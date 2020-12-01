import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import dash_html_components as html
import dash_core_components as dcc
from copy import deepcopy

from data_handling import *

Z_MAX = 100
MAP_WIDTH = 625
X_LOC7d = 38  # X location for the '7 Day Average' annotation
COLORBAR = dict(x=1, title=dict(text='Average<br>Daily<br>Cases<br>per 100k',
                                font=dict(size=14, color='#A10C0C')))


def _add_ave_and_rate_cols(cases_s, pop=None):
    """Add 7-day average and rate per 100k population.

    Args:
        cases_s (pandas.Series): Index are dates, values are number of new cases that day
        pop (int): Population of the area. If `None`, do not add two extra columns for the cases_rate and average cases_rate

    Returns:
        pandas.DataFrame: Add column for the rolling 7 day average. If `pop` is provided, add two extra columns fro the cases per 100k population, and 7-day average of that

    """
    if cases_s.sum() == 0:
        return None

    df = cases_s.to_frame('cases')
    df['cases_ave'] = df['cases'].rolling(7, ).mean()

    if pop:
        df['cases_rate'] = df['cases'] / pop * 100000
        df['cases_rate_ave'] = df['cases_ave'] / pop * 100000

    return df.dropna()


def trend_table(ser):
    """Create an html table with summary statistics

    Args:
        ser (pandas.Series): Index are dates, values new cases on that day

    Returns:
        dash_html_components: Table that shows new cases yesterday, 7-day trend, and 14-day trend
    """
    df = _add_ave_and_rate_cols(ser)
    yest = int(df['cases'][-1])  # Cases yesterday
    yest_date_str = df.index[-1].strftime('%b %-d')
    ave = df['cases_ave'][-1]  # Average cases as of yesterday
    ave_week_ago = df['cases_ave'][-8]
    ave_two_week_ago = df['cases_ave'][-15]

    def percent_change_str(old, new):
        if old == 0 and new > 0:
            change = 100
        elif old == 0 and new == 0:
            change = 0
        else:
            change = int(round(((new - old) / old * 100), 0))

        if change > 0:
            return '+{}%'.format(change)
        else:
            return '{}%'.format(change)

    week_change = percent_change_str(ave_week_ago, ave)
    two_week_change = percent_change_str(ave_two_week_ago, ave)

    style = {'textAlign': 'center'}
    table_header = [
        html.Thead(html.Tr([
            html.Th('New Cases {}'.format(yest_date_str), style=style),
            html.Th('7-Day Trend', style=style),
            html.Th('14-Day Trend', style=style),
        ]))]

    table_body = [
        html.Tbody(html.Tr([
            html.Td('{:,.0f}'.format(yest), style=style),
            html.Td(week_change, style=style),
            html.Td(two_week_change, style=style),
        ]))]

    return table_header + table_body


def states_map(states_map_df, date):
    """Create a Choropleth plot of the US states

    Args:
        states_map_df (pandas.DataFrame): Index are names of states, columns must include 'abbr', 'ave_rate', and 'text'
        date (datetime): Date that states_map_df was created

    Returns:
        plotly.graph_objects.Figure:

    """
    fig = go.Figure(data=go.Choropleth(
        locationmode='USA-states',
        locations=states_map_df['abbr'],
        z=states_map_df['ave_rate'].astype(float),
        customdata=states_map_df.index.to_list(),
        text=states_map_df['text'],
        zmin=0,
        zmax=Z_MAX,
        colorscale='Reds',
        hovertemplate='%{text} <extra></extra>',
        colorbar=COLORBAR,
    ))

    fig.update_layout(
        margin=dict(l=3, r=3, b=3, t=0, pad=0),
        geo_scope='usa',
        width=MAP_WIDTH,
        height=310,
        annotations=[dict(
            x=0.0,
            y=0.0,
            xref='paper',
            yref='paper',
            text='As of {}'.format(date.strftime('%b %-d')),
            showarrow=False
        )]
    )
    return fig


def counties_map(counties_map_df, counties_geo, states_meta_df, state):
    """County-level map that shows the average cases per day rate

    Args:
        counties_map_df (pandas.DataFrame): from FreshData
        counties_geo (dict): from FreshData
        states_meta_df (pandas.DataFrame): from FreshData
        state (str): US state to show a map of

    Returns:
        plotly.graph_objects.Figure:

    """
    df = counties_map_df

    geo = deepcopy(counties_geo)
    if state != 'USA':
        df = df[df['state'] == state]
        state_num = states_meta_df.loc[state, 'fips']
        l = [f for f in counties_geo['features'] if
             f['properties']['STATE'] == state_num]
        geo['features'] = l

    fig = go.Figure(
        go.Choroplethmapbox(
            colorbar=COLORBAR,
            geojson=geo,
            locations=df['fips'],
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
        # you will need your own mapbox token,
        mapbox_accesstoken=open(".mapbox_token").read(),
        mapbox_style='light',
        width=MAP_WIDTH,
        height=414,
        margin=dict(l=3, r=3, b=3, t=3, pad=10),
        mapbox_zoom=states_meta_df.loc[state, 'zoom'],
        mapbox_center=dict(lat=states_meta_df.loc[state, 'lat'],
                           lon=states_meta_df.loc[state, 'lon']),
    )

    return fig


class CasesGraph:
    """Generate plotly graphs to show number of new cases

    I put this into a class purely for organizational purposes
    """

    @staticmethod
    def _add_cases_graph(fig, df, row=1, col=1, only_total_cases=False):
        """Add cases graph to a plotly figure

        Args:
            fig (plotly.graph_objects.Figure):
            df (pandas.DataFrame): index are dates, columns include 'cases', 'cases_ave', and (optionally) 'cases_rate' and 'cases_rate_ave'
            row (int, optional): Which row to put the graph if using subplots
            col (int, optional): Which column to put the graph if using subplots
            only_total_cases (bool, optional): If True, do not add traces for 'cases_rate' and 'cases_rate_ave'

        Returns:
            plotly.graph_objects.Figure:

        """
        df = df.round(1)

        # Hacky fix to add extra day at end so that the last tick-mark will show
        new_i = df.index[-1] + timedelta(days=1)
        df.loc[new_i] = [np.nan] * len(df.columns)

        if not only_total_cases:
            # Traces for total cases
            fig.add_trace(
                go.Bar(
                    x=list(df.index), y=list(df['cases_rate']),
                    name='Cases Per 100k',
                    marker=dict(color='red'), opacity=0.5
                ),
                row=row, col=col
            )
            fig.add_trace(
                go.Scatter(
                    x=list(df.index), y=list(df['cases_rate_ave']),
                    name='7 Day Average.', line=dict(color='red'),
                    hoverinfo='skip'
                ),
                row=row, col=col,
            )
            fig.add_trace(
                go.Scatter(
                    x=list(df.index), y=[50] * len(df),
                    line=dict(color='rgba(0, 0, 0, 0.5)', dash='dash'),
                    hoverinfo='skip'
                ),
                row=row, col=col
            )

        # Traces for cases per 100k
        fig.add_trace(
            go.Bar(
                x=list(df.index), y=list(df['cases']), name='Cases',
                marker=dict(color='red'), opacity=0.5,
                visible=only_total_cases
            ),
            row=row, col=col
        )
        fig.add_trace(
            go.Scatter(
                x=list(df.index), y=list(df['cases_ave']),
                name='7 Day Average',
                line=dict(color='red'),
                visible=only_total_cases, hoverinfo='skip'
            ),
            row=row, col=col
        )

        # Set xticks
        first_month = df.index[1].month
        last_month = df.index[-1].month
        first_of_months = [datetime(year=2020, month=m, day=1) for m in
                           range(first_month, last_month + 1)]

        fig.update_xaxes(
            tickformat='%b %-d',
            tickmode='array',
            tickvals=first_of_months,
            showgrid=True,
            ticks='outside',
            tickson='boundaries',
            ticklen=3,
            tickangle=45,
            row=row, col=col)
        return fig

    @staticmethod
    def _add_buttons_and_annotations(fig, df):
        """Add buttons for 'New Cases per 100k' and 'New Cases'

        Args:
            fig (plotly.graph_objects.Figure):
            df (pandas.DataFrame): DataFrame used to create graph

        Returns:
            :plotly.graph_objects.Figure

        """

        ### Create annotations ######
        x_loc50 = 24  # x location for the '50 Cases per 100k' annotation

        if df['cases_rate'].max() < 45:
            #  If max cases_rate is low, put annotation below line
            ay = 25
        else:
            #  If max cases_rate is high, put annotation above the line
            ay = -25

        cases_rate_anns = tuple([
            dict(x=df.index[x_loc50], y=50,
                 xref='x1', yref='y1', text='50 Cases<br>per 100k', ax=0,
                 ay=ay),
            dict(x=df.index[X_LOC7d], y=df['cases_rate_ave'].iloc[X_LOC7d],
                 xref='x1', yref='y1', text='7 Day Average', ax=0, ay=-20,
                 ),
        ])
        cases_anns = tuple([
            dict(x=df.index[X_LOC7d], y=df['cases_ave'].iloc[X_LOC7d],
                 xref="x", yref="y", text='7 Day Average',
                 ax=0, ay=-20)
        ])


        ### Add buttons and annotations ######
        existing_anns = fig.layout.annotations
        fig.layout.annotations = existing_anns + cases_rate_anns

        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    active=0,
                    showactive=True,
                    x=0.5,
                    y=1.2,
                    xanchor='center',
                    yanchor='top',
                    buttons=list([
                        dict(label='New Cases per 100k',
                             method="update",
                             args=[
                                 {"visible": [True, True, True, False, False]},
                                 {"annotations": existing_anns + cases_rate_anns}]),
                        dict(label='New Cases',
                             method="update",
                             args=[{"visible": [False, False, False, True,
                                                True]},
                                   {"annotations": existing_anns + cases_anns}]),
                    ]),
                )
            ])
        return fig

    @staticmethod
    def usa_graph(usa_cases_ser):
        """Create a graph showing the new cases for all of the US

        Args:
            usa_cases_ser (pandas.Series): Index are dates. Values are new cases that day

        Returns:
            plotly.graph_objects.Figure

        """
        fig = make_subplots()
        df = _add_ave_and_rate_cols(usa_cases_ser)
        fig = CasesGraph()._add_cases_graph(fig, df, only_total_cases=True)

        cases_annotations = [
            dict(x=df.index[X_LOC7d], y=df['cases_ave'].iloc[X_LOC7d],
                 xref="x", yref="y", text='7 Day Average',
                 ax=0, ay=-25),
        ]

        fig.update_layout(width=360,
                          height=200,
                          showlegend=False,
                          margin=dict(l=5, r=5, b=5, t=5, pad=1),
                          hovermode='x unified',
                          annotations=cases_annotations)
        return fig

    @staticmethod
    def state_or_county_graph(ser, pop):
        """Create a graph showing the new cases for all of the US

        Args:
            ser (pandas.Series): Index are dates, values are new cases on that day
            pop (int): population of the area in question

        Returns:
            :plotly.graph_objects.Figure

        """
        df = _add_ave_and_rate_cols(ser, pop)
        fig = make_subplots()
        fig = CasesGraph._add_cases_graph(fig, df, row=1, col=1)
        fig = CasesGraph._add_buttons_and_annotations(fig, df)
        fig.update_layout(width=360,
                          height=270,
                          showlegend=False,
                          margin=dict(l=5, r=5, b=5, t=5, pad=1),
                          hovermode='x unified')
        return fig


if __name__ == '__main__':
    print()

# def make_cases_subplots(fd, state, county_fips=None):
#     if county_fips is None:
#         county_title = '(Click on a county to see county graph)'
#     else:
#         county_title = fd.fips_county_dict[county_fips]
#
#     fig = make_subplots(rows=2, shared_xaxes=False, vertical_spacing=0.2)
#
#     state_pop = fd.state_pop_dict[state]
#     states_df = cases_data_for_graph(fd.states_df[state], state_pop)
#     fig = make_cases_graph(fig, states_df, row=1, col=1)
#
#     if county_fips:
#         county_pop = fd.fips_pop_dict[county_fips]
#         counties_df = cases_data_for_graph(fd.counties_df[county_fips], county_pop)
#         if counties_df is None:
#             county_title = 'No recorded positive cases in {}'.format(county_title)
#         else:
#             fig = make_cases_graph(fig, counties_df, row=2, col=1)
#
#     title_annotations = [
#         dict(x=0.5, y=1.08, showarrow=False, xref='paper', yref='paper',
#              yanchor='top', xanchor='center',
#              text='<b>{}</b>'.format(state), font={'size': 18}
#              ),
#         dict(x=0.5, y=0.44, showarrow=False, xref='paper', yref='paper',
#              yanchor='middle', xanchor='center',
#              text='<b>{}</b>'.format(county_title), font={'size': 16}
#              )
#     ]
#
#     fig.update_layout(annotations=title_annotations)
#
#     fig = _add_buttons_and_annotations(fig, states_df)
#     return fig
