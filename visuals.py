import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta
import cufflinks as cf
import json
from copy import deepcopy

from data_handling import *

FULL_MAP_W = 844
FULL_MAP_STYLE = 'outdoors'

def covid_map(fd, counties_geo, states_df):
    # https://en.wikipedia.org/wiki/List_of_geographic_centers_of_the_United_States
    # https://developers.google.com/public-data/docs/canonical/states_csv
    fd.refresh_if_needed()
    df = fd.map_df
    state = 'USA'

    fig = go.Figure(
        go.Choroplethmapbox(
            colorbar=dict(title=dict(text='Average<br>Daily<br>Cases<br>per 100k',
                                     font=dict(size=14, color='#A10C0C')),
                          x=1
                          ),
            geojson=counties_geo,
            locations=df['FIPS'],
            z=df['ave_rate'],
            customdata=df['week_ave'],
            text=df['text'],
            colorscale='Reds', zmin=0, zmax=50,
            hovertemplate='%{text} <extra></extra>',
            meta=state
        ),
    )

    fig.update_layout(
        mapbox_accesstoken=open(".mapbox_token").read(),  # you will need your own token,
        mapbox_style=FULL_MAP_STYLE,
        width=FULL_MAP_W,
        margin=dict(l=3, r=3, b=3, t=13, pad=10),
        mapbox_zoom=states_df.loc[state, 'zoom'],
        mapbox_center=dict(lat=states_df.loc[state, 'lat'],
                           lon=states_df.loc[state, 'lon']),
    )
    return fig


def update_map(fig, fd, states_df, selected_fips=None):
    current_state = fig.data[0].meta
    df = fd.map_df
    if selected_fips is None:
        state = 'USA'
        width = FULL_MAP_W
        style = FULL_MAP_STYLE
    else:
        state = df[df['FIPS'] == selected_fips]['State'].values[0]
        df = df[df['State'] == state]
        width = 600
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
    fig.update_layout(mapbox_zoom=states_df.loc[state, 'zoom'],
                      mapbox_center={'lat': states_df.loc[state, 'lat'],
                                     'lon': states_df.loc[state, 'lon']},
                      width=width,
                      mapbox_style=style
                      )
    return fig

def county_fig(df, county_name):
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
             xref="x", yref="y", text='7 Day <br>Average', ax=0, ay=-30),
        dict(x=df.index[x_loc50], y=50,
             xref="x", yref="y", text='50 Cases<br>per 100k', ax=0, ay=-30),
    ]
    cases_annotations = [dict(x=df.index[x_loc], y=df['cases_ave'].iloc[x_loc],
                             xref="x", yref="y", text='7 Day <br>Average',
                             ax=0, ay=-30)]
    fig.update_layout(annotations=cases_rate_annotations)

    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                showactive=True,
                x=0.505,
                y=1.2,
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

    fig.update_layout(title=county_name,
                      autosize=False,
                      width=500,
                      height=350,
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
    # fd = FreshData()
    # fips = '53047'
    # county_name = fd.fips_county_dict[fips]
    # county_pop = fd.fips_pop_dict[fips]
    # county_df = county_data(fd.cases_df[fips], county_pop)
    # f = county_fig(county_df, county_name)
    # f.show()

    with open('data/geojson-counties-fips.json') as f:
        counties = json.load(f)
    fd = FreshData()
    states_df = load_states_csv()
    fips = '53047'
    fips2 = '02290'
    f = covid_map(fd, counties)
    f.show()
    # f = update_map(f, fd, states_df, fips)
    # f = update_map(f, fd, states_df, fips2)
    #
    print()