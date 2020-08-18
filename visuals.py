import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta
import cufflinks as cf
import json
from copy import deepcopy

from data_handling import *

FULL_MAP_W = 700
FULL_MAP_STYLE = 'outdoors'
Z_MAX = 50
COLORBAR = dict(x=1, #outlinecolor='#A10C0C', bordercolor='#A10C0C',
                title=dict(text='Average<br>Daily<br>Cases<br>per 100k',
                           font=dict(size=14, color='#A10C0C')),
                )

def make_counties_map(fd, counties_geo, states_meta_df):
    fd.refresh_if_needed()
    df = fd.county_map_df
    state = 'USA'

    fig = go.Figure(
        go.Choroplethmapbox(
            colorbar=COLORBAR,
            geojson=counties_geo,
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
        mapbox_style=FULL_MAP_STYLE,
        width=FULL_MAP_W,
        margin=dict(l=3, r=3, b=3, t=3, pad=10),
        mapbox_zoom=states_meta_df.loc[state, 'zoom'],
        mapbox_center=dict(lat=states_meta_df.loc[state, 'lat'],
                           lon=states_meta_df.loc[state, 'lon']),
    )
    return fig


def make_state_map(fd, states_meta_df):
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

    fig.update_layout(
        # title_text='2011 US Agriculture Exports by State',
        margin=dict(l=3, r=3, b=3, t=0, pad=0),
        geo_scope='usa',
        width=650,
        height=320
    )

    return fig


def update_counties_map(fig, fd, states_meta_df, fips=None, state=None):
    if not fips and not state:
        raise Exception('Must provide one of "state" or "fips"')
    current_state = fig.data[0].meta
    df = fd.county_map_df
    if fips:
        state = df[df['FIPS'] == fips]['state'].values[0]
    df = df[df['state'] == state]
    width = 650
    style = 'light'

    if current_state == state:
        return fig

    # TODO: File bug report about plotly_restyle not changing type to numpy automatically
    fig.plotly_restyle(dict(locations=df['FIPS'].to_numpy(),
                            z=df['ave_rate'].to_numpy(),
                            customdata=df['week_ave'].to_numpy(),
                            text=df['text'].to_numpy(),
                            meta=state
                            )
                       )
    fig.update_layout(mapbox_zoom=states_meta_df.loc[state, 'zoom'],
                      mapbox_center={'lat': states_meta_df.loc[state, 'lat'],
                                     'lon': states_meta_df.loc[state, 'lon']},
                      width=width,
                      mapbox_style=style
                      )
    return fig


def make_cases_graph(df, title):
    df = df.round(1)
    ### find first tick spot
    total_days = len(df)
    days_back_to_start = int(total_days / 14) * 14 + 2
    # Hacky fix to add extra day at end so that the last tick-mark will show
    new_i = df.index[-1] + timedelta(days=1)
    df.loc[new_i] = [np.nan] * len(df.columns)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=list(df.index), y=list(df['cases_rate']), name='Cases Per 100k',
        marker=dict(color='red'), opacity=0.5)
    )
    fig.add_trace(go.Scatter(
        x=list(df.index), y=list(df['cases_ave_rate']), name='7 Day Average.', line=dict(color='red'))
    )
    fig.add_trace(go.Scatter(
        x=list(df.index), y=[50]*len(df), line=dict(color='rgba(0, 0, 0, 0.5)', dash='dash'),
        hoverinfo='skip')
    )

    fig.add_trace(go.Bar(
        x=list(df.index), y=list(df['cases']), name='Cases',
        marker=dict(color='red'), opacity=0.5,
        visible=False)
    )
    fig.add_trace(go.Scatter(
        x=list(df.index), y=list(df['cases_ave']), name='7 Day Average',
        line=dict(color='red'),
        visible=False)
    )

    x_loc = 20
    x_loc50 = 11
    #TODO: Add logic to put annotation below line if max is below 50
    cases_rate_annotations = [
        dict(x=df.index[x_loc], y=df['cases_ave_rate'].iloc[x_loc],
             xref="x", yref="y", text='7 Day Average', ax=0, ay=-20),
        dict(x=df.index[x_loc50], y=50,
             xref="x", yref="y", text='50 Cases<br>per 100k', ax=0, ay=-30),
    ]
    cases_annotations = [dict(x=df.index[x_loc], y=df['cases_ave'].iloc[x_loc],
                             xref="x", yref="y", text='7 Day Average',
                             ax=0, ay=-20)]
    fig.update_layout(annotations=cases_rate_annotations)

    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                showactive=True,
                x=0.65,
                y=1.25,
                buttons=list([
                    dict(label='New Cases per 100k',
                         method="update",
                         args=[{"visible": [True, True, True, False, False]},
                               {"annotations": cases_rate_annotations}]),
                    dict(label='New Cases',
                         method="update",
                         args=[{"visible": [False, False, False, True, True]},
                               {"annotations": cases_annotations}]),
                ]),
            )
        ])

    fig.update_layout(title=title,
                      autosize=False,
                      width=400,
                      height=300,
                      showlegend=False,
                      margin=dict(l=5, r=5, b=5, t=100, pad=1),
                      hovermode='x unified',
                      xaxis=dict(title=None,
                                 tickformat='%b %d',
                                 tickmode='linear',
                                 tick0=df.index[-days_back_to_start],
                                 dtick=14 * 86400000.0,
                                 showgrid=True,
                                 ticks="outside",
                                 tickson="boundaries",
                                 ticklen=3,
                                 tickangle=45)
                      )
    return fig


if __name__ == '__main__':
    fd = FreshData()
    states_meta = load_states_csv()
    # make_state_map(fd, states_meta)


    fips = '53047'
    state='Washington'
    state_pop = fd.state_pop_dict[state]
    state_df = cases_data_for_graph(fd.state_df[state], state_pop)
    f = make_cases_graph(state_df, state)
    f.show()
    print()

    with open('data/geojson-counties-fips.json') as f:
        counties = json.load(f)
    fd = FreshData()
    states_df = load_states_csv()
    fips = '53047'
    fips2 = '02290'
    f = make_counties_map(fd, counties, states_df)
    f.show()
    # f = update_map(f, fd, states_df, fips)
    # f = update_map(f, fd, states_df, fips2)
    #
    print()