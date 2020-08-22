import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import json
from copy import deepcopy

from data_handling import *

Z_MAX = 50
COLORBAR = dict(x=1,
                title=dict(text='Average<br>Daily<br>Cases<br>per 100k',
                           font=dict(size=14, color='#A10C0C')),
                )

def make_states_map(fd, states_meta_df):
    fd.refresh_if_needed()
    # FIXME: This logic should be done somewhere else!
    df = fd.state_map_df
    df = df.set_index('state', drop=True)
    df = df.join(states_meta_df['abbr'])

    fig = go.Figure(data=go.Choropleth(
        locationmode='USA-states',  # set of locations match entries in `locations`
        locations=df['abbr'],
        z=df['ave_rate'].astype(float),  # Data to be color-coded
        customdata=df.index.to_list(),
        text=df['text'],
        zmin=0,
        zmax=Z_MAX,
        colorscale='Reds',
        hovertemplate='%{text} <extra></extra>',
        colorbar=COLORBAR,
    ))

    now = datetime.now() - timedelta(hours=7)
    now = now.strftime('%m/%d/%y at %H:%M:%S')
    fig.update_layout(
        margin=dict(l=3, r=3, b=3, t=0, pad=0),
        geo_scope='usa',
        width=650,
        height=320,
        annotations=[dict(
            x=0.0,
            y=0.0,
            xref='paper',
            yref='paper',
            text='Refreshed {}'.format(now),
            showarrow=False
        )]

    )
    return fig


def make_counties_map(fd, counties_geo, states_meta_df, fips=None, state=None):
    fd.refresh_if_needed()
    df = fd.county_map_df

    if not fips and not state:
        state = 'USA'
    elif fips:
        state = df[df['FIPS'] == fips]['state'].values[0]

    geo = deepcopy(counties_geo)
    if state != 'USA':
        df = df[df['state'] == state]
        state_num = states_meta_df.loc[state, 'fips']
        l = [f for f in counties_geo['features'] if f['properties']['STATE'] == state_num]
        geo['features'] = l

    fig = go.Figure(
        go.Choroplethmapbox(
            colorbar=COLORBAR,
            geojson=geo,
            locations=df['FIPS'],
            z=df['ave_rate'],
            customdata=df['state'],
            text=df['text'],
            zmin=0,
            zmax=Z_MAX,
            hovertemplate='%{text} <extra></extra>',
            colorscale='Reds',
            meta=state
        ),
    )

    fig.update_layout(
        mapbox_accesstoken=open(".mapbox_token").read(),  # you will need your own token,
        mapbox_style='light',
        width=650,
        height=500,
        margin=dict(l=3, r=3, b=3, t=3, pad=10),
        mapbox_zoom=states_meta_df.loc[state, 'zoom'],
        mapbox_center=dict(lat=states_meta_df.loc[state, 'lat'],
                           lon=states_meta_df.loc[state, 'lon']),
    )

    return fig


def make_cases_graph(fig, df, row=1, col=1):
    df = df.round(1)
    ### find first tick spot
    total_days = len(df)
    days_back_to_start = int(total_days / 14) * 14 + 2
    # Hacky fix to add extra day at end so that the last tick-mark will show
    new_i = df.index[-1] + timedelta(days=1)
    df.loc[new_i] = [np.nan] * len(df.columns)

    # Once every fortnight we have this problem
    if days_back_to_start > len(df):
        days_back_to_start -= 14

    fig.add_trace(go.Bar(
        x=list(df.index), y=list(df['cases_rate']), name='Cases Per 100k',
        marker=dict(color='red'), opacity=0.5),
        row=row, col=col
    )
    fig.add_trace(go.Scatter(
        x=list(df.index), y=list(df['cases_ave_rate']), name='7 Day Average.', line=dict(color='red')),
        row=row, col=col
    )
    fig.add_trace(go.Scatter(
        x=list(df.index), y=[50]*len(df), line=dict(color='rgba(0, 0, 0, 0.5)', dash='dash'),
        hoverinfo='skip'),
        row=row, col=col
    )

    fig.add_trace(go.Bar(
        x=list(df.index), y=list(df['cases']), name='Cases',
        marker=dict(color='red'), opacity=0.5,
        visible=False),
        row=row, col=col
    )
    fig.add_trace(go.Scatter(
        x=list(df.index), y=list(df['cases_ave']), name='7 Day Average',
        line=dict(color='red'),
        visible=False),
        row=row, col=col
    )

    fig.update_xaxes(
                     tickformat='%b %d',tickmode='linear',
                     tick0=df.index[-days_back_to_start],
                     dtick=14 * 86400000.0,showgrid=True, ticks="outside",
                     tickson="boundaries", ticklen=3, tickangle=45,
                     row=row, col=col)
    return fig


def make_cases_subplots(fd, state, county_fips=None):
    fd.refresh_if_needed()
    if county_fips is None:
        county_title = '(Click on a county to see county graph)'
    else:
        county_title = fd.fips_county_dict[county_fips]

    fig = make_subplots(rows=2, shared_xaxes=False, vertical_spacing=0.2)

    state_pop = fd.state_pop_dict[state]
    state_df = cases_data_for_graph(fd.state_df[state], state_pop)
    fig = make_cases_graph(fig, state_df, row=1, col=1)

    if county_fips:
        county_pop = fd.fips_pop_dict[county_fips]
        county_df = cases_data_for_graph(fd.county_df[county_fips], county_pop)
        if county_df is None:
            county_title = 'No recorded positive cases in {}'.format(county_title)
        else:
            fig = make_cases_graph(fig, county_df, row=2, col=1)

    title_annotations = [
        dict(x=0.5, y=1.08, showarrow=False, xref='paper', yref='paper', yanchor='top', xanchor='center',
             text='<b>{}</b>'.format(state), font={'size': 18}
             ),
        dict(x=0.5, y=0.44, showarrow=False, xref='paper', yref='paper', yanchor='middle', xanchor='center',
             text='<b>{}</b>'.format(county_title), font={'size': 16}
             )
    ]

    x_loc = 20
    x_loc50 = 11
    if state_df['cases_ave_rate'].max() < 45:
        ay = 25
    else:
        ay = -25
    cases_rate_annotations = [
        dict(x=state_df.index[x_loc50], y=50,
             xref='x1', yref='y1', text='50 Cases<br>per 100k', ax=0, ay=ay),
        dict(x=state_df.index[x_loc], y=state_df['cases_ave_rate'].iloc[x_loc],
             xref='x1', yref='y1', text='7 Day Average', ax=0, ay=-25,
             ),
    ]
    cases_annotations = [dict(x=state_df.index[x_loc], y=state_df['cases_ave'].iloc[x_loc],
                             xref="x", yref="y", text='7 Day Average',
                             ax=0, ay=-25)]

    fig.update_layout(annotations=title_annotations + cases_rate_annotations)

    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                showactive=True,
                x=0.5,
                y=1.17,
                xanchor='center',
                yanchor='top',
                buttons=list([
                    dict(label='New Cases per 100k',
                         method="update",
                         args=[{"visible": [True, True, True, False, False]},
                               {"annotations": title_annotations + cases_rate_annotations}]),
                    dict(label='New Cases',
                         method="update",
                         args=[{"visible": [False, False, False, True, True]},
                               {"annotations": title_annotations + cases_annotations}]),
                ]),
            )
        ])

    fig.update_layout(width=500,
                      height=500,
                      showlegend=False,
                      margin=dict(l=5, r=5, b=5, t=5, pad=1),
                      hovermode='x unified',)
    return fig


if __name__ == '__main__':
    fd = FreshData()
    states_meta = load_states_csv()

    fig = make_cases_subplots(fd, 'USA')
    fig.show()

    # with open('data/geojson-counties-fips.json') as f:
    #     counties_geo = json.load(f)
    # fig = make_counties_map(fd, counties_geo, states_meta, fips=None, state='Alabama')
    # fig.show()


    # fig = make_state_map(fd, states_meta)
    # fig.show()
    # state='New York'
    # fips = '53047'
    # # fips = None
    # f = make_cases_subplots(fd, state, county_fips=fips)
    # f.show()
    print()

    # states_df = load_states_csv()
    # fips = '53047'
    # fips2 = '02290'
    # f = make_counties_map(fd, counties, states_df)
    # f.show()
    # f = update_map(f, fd, states_df, fips)
    # f = update_map(f, fd, states_df, fips2)
    #
