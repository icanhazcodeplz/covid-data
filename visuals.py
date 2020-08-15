import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta
import cufflinks as cf
import json

from data_handling import *


def covid_map(fd, counties):
    fd.refresh_if_needed()
    df = fd.map_df
    t = ["""<b>{}</b><br>Avg. Daily Cases: {:.1f}<br>             Per 100k: {:.1f}""".format(
        tup.Combined_Key, tup.week_ave, tup.ave_rate) for tup in df.drop(
        'FIPS', axis=1).itertuples()]
    fig = go.Figure(
        go.Choroplethmapbox(
            geojson=counties, locations=df['FIPS'], z=df['ave_rate'],
            customdata=df['week_ave'],
            colorscale='Reds', zmin=0, zmax=50,
            hovertemplate='%{text} <extra></extra>',
            text=t,
        )
    )

    fig.update_layout(mapbox_style="outdoors",
                      mapbox_accesstoken=open(".mapbox_token").read(), # you will need your own token,
                      mapbox_zoom=3,
                      mapbox_center={"lat": 37.0902, "lon": -95.7129},
                      margin={"r":0,"t":0,"l":0,"b":0})

    return fig


def county_fig(df):
    df = df.round(1)
    ### find first tick spot
    total_days = len(df)
    days_back_to_start = int(total_days / 14) * 14 + 2
    # Hacky fix to add extra day at end so that the tick-mark will show
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

    x_loc = 17
    cases_rate_annotations = [dict(x=df.index[x_loc], y=df['cases_ave_rate'].iloc[x_loc],
                             xref="x", yref="y", text='7 Day <br>Average',
                             ax=0, ay=-30)]
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
                x=0.44,
                y=1.18,
                buttons=list([
                    dict(label='New Cases per 100k',
                         method="update",
                         args=[{"visible": [True, True, False, False]},
                               {"annotations": cases_rate_annotations}]),
                    dict(label='New Cases',
                         method="update",
                         args=[{"visible": [False, False, True, True]},
                               {"annotations": cases_annotations}]),
                ]),
            )
        ])

    fig.update_layout(autosize=False, width=650, height=350,
                      showlegend=False,
        # title_text='New Cases in {}'.format(county_name),
                    margin=dict(l=5, r=5, b=5, t=70, pad=1),
                    # paper_bgcolor="LightSteelBlue",
                    hovermode='x unified',
                    yaxis=dict(title=None),
                    xaxis=dict(title=None,tickformat='%b %d', tickmode='linear',
                               tick0=df.index[-days_back_to_start],
                               dtick=14 * 86400000.0,
                               showgrid=True, ticks="outside",
                               tickson="boundaries", ticklen=3, tickangle=45)

                    )
    return fig


if __name__ == '__main__':
    with open('geojson-counties-fips.json') as f:
        counties = json.load(f)
    fd = FreshData()
    f = covid_map(fd, counties)
    f.show()
    print()

    fd = FreshData()
    fips = '53047'
    county_name = fd.fips_county_dict[fips]
    county_pop = fd.fips_pop_dict[fips]
    county_df = county_data(fd.cases_df[fips], county_pop)
    f = county_fig(county_df)
    f.show()
    print()