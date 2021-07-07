from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timedelta
import dash_html_components as html
from module.data_handling import *

X_LOC7d = 38  # X location for the '7 Day Average' annotation


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
        # TODO: Improve this logic so it handles 2022 and onward
        last_month = df.index[-1].month
        first_of_months20 = [datetime(year=2020, month=m, day=1) for m in
                             range(1, 13)]
        first_of_months21 = [datetime(year=2021, month=m, day=1) for m in
                             range(1, last_month + 1)]

        fig.update_xaxes(
            tickformat='%b %Y',
            tickmode='array',
            tickvals=first_of_months20 + first_of_months21,
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
