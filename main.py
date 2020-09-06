import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from constants import *
from data_handling import *
from visuals import *


app = dash.Dash(external_stylesheets=[dbc.themes.UNITED])
app.title = 'COVID-19 Hot Spots'
server = app.server

#### GLOBAL VARS ##############################################################
fd = FreshData()
config = {'scrollZoom': False,
          'displayModeBar': False,
          'doubleClick': False} # TODO: Bug report, doubleClick = False does nothing


#### LAYOUT ###################################################################
def table_and_graph_card(title, table, graph):
    return dbc.Card([
        html.H4(title, style={'textAlign': 'center'}),
        dbc.Row([
            dbc.Table(table,
                      bordered=True,
                      dark=False,
                      striped=True,
                      className='table-primary',
                      size='sm',
                      style=dict(width='8.1cm')),
        ], justify='center'),
        dcc.Graph(figure=graph,
                  config=config),
    ], color='light', body=True)


def usa_table_and_graph_card():
    return table_and_graph_card('USA',
                                make_trend_table(fd.states_df['USA']),
                                make_usa_graph(fd.states_df['USA']))


app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("COVID-19 Hot Spots", style={'textAlign': 'center'}),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dcc.Interval(id='interval-component',
                             interval=1*1000 * 60 * 60,  # in milliseconds
                             n_intervals=0),
                dbc.Row([
                    html.Div(usa_table_and_graph_card(), id='usa-card'),
                    dbc.Card([
                        dcc.Graph(figure=make_states_map(fd.states_map_df, fd.states_df.index[-1]),
                                  id='usa-map',
                                  config=config),
                        html.H6('Click on a state or select from the dropdown to see state-view',
                                style={'textAlign': 'center'}),
                    ], color='light', inverse=False, body=True),
                ], justify='center'),
            ], color='secondary', body=True)
        ], width='auto'),
    ], justify='center',),

    dbc.Row([
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(id='state-dropdown',
                                     options=[dict(value=s, label=s) for s in fd.states_meta_df.index],
                                     placeholder='Select a state',
                                     clearable=False,
                                     style={"width": "180px",
                                            "font-size": "large",}),
                    ], width=3),
                ], justify='center'),
                dbc.Row([
                    dbc.Card([
                        dcc.Loading([
                            dcc.Graph(id='state-map',
                                      config={'displayModeBar': False}),
                                ], type='default')
                    ], color='light', body=True),
                    dcc.Loading([html.Div(id='county-graph')], type='default'),
                ], justify='center'),
            ]),
        ], color='secondary'),
    ], id='county-row', justify='center'),

    dbc.Row([
        dcc.Markdown("""
            Built with [Plotly Dash](https://plotly.com/dash/). Data from 
            [Johns Hopkins University](https://github.com/CSSEGISandData/COVID-19). 
            Source code at [Github](https://github.com/icanhazcodeplz/covid-data). 
            Inspiration from the
            [New York Times](https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html).
            """),
    ], justify='center',)
], fluid=True)


#### CALLBACKS ################################################################

@app.callback(
    Output('usa-card', 'children'),
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=False)
def update_usa_data(_):
    return usa_table_and_graph_card()


@app.callback(
    Output('state-dropdown', 'value'),
    [Input('usa-map', 'clickData')],
    prevent_initial_call=False)
def map_click_or_county_selection(clickData):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'usa-map':
        state = clickData['points'][0]['customdata']
    else:
        state = 'USA'
    return state


@app.callback(
    Output('state-map', 'figure'),
    [Input('state-dropdown', 'value')],
    prevent_initial_call=False)
def update_state_map(value):
    if value is None:
        value = 'USA'
    return make_counties_map(fd.counties_map_df, fd.counties_geo, fd.states_meta_df, state=value)


@app.callback(
    Output('county-graph', 'children'),
    [Input('state-dropdown', 'value'),
     Input('state-map', 'clickData')],
    prevent_initial_call=True)
def make_state_or_county_card(value, clickData):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'state-dropdown':
        state = value
        title = state
        table = make_trend_table(fd.states_df[state])
        graph = make_state_or_county_graph(fd, state=state)

    if trigger == 'state-map':
        fips = clickData['points'][0]['location']
        title = fd.fips_county_dict[fips]
        if fd.counties_df[fips].sum() == 0:
            return html.H4('No cases have been reported in {}'.format(title))

        table = make_trend_table(fd.counties_df[fips])
        graph = make_state_or_county_graph(fd, fips=fips)

    return table_and_graph_card(title, table, graph)


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)

"""
TODO:
- Add tests
- Add documentation
- Update README

# FIXME: Not all of these are actually removed! Might be plotly bug
modebar_buttons_to_remove = ['autoScale2d',
                             'hoverCompareCartesian',
                             'toggleSpikelines',
                             'lassoSelect',
                             'zoomInGeo',
                             'zoomOutGeo',
                             'resetGeo',
                             'hoverClosestGeo'
                             'hoverClosestGl2d',
                             'hoverClosestPie',
                             'toggleHover',
                             'resetViews',
                             'sendDataToCloud',
                             'resetViewMapbox'
                             'lasso2d',
                             'zoom2d',
                             'resetScale2d'
                             'select2d',
                             'zoomIn2d',
                             'zoomOut2d',
                             'toImage',
                             'pan2d',
                             'hoverClosestGeo'
                             'hoverClosestCartesian']
"""


"""" Ideas
https://www.larimer.org/health/communicable-disease/coronavirus-covid-19/larimer-county-positive-covid-19-numbers
https://www.digitalocean.com/community/pages/hub-for-good
https://covid19-dash.herokuapp.com/
https://covid19mtl.ca/en
https://covid19-dashboard-online.herokuapp.com/
https://experience.arcgis.com/experience/a6f23959a8b14bfa989e3cda29297ded
https://www.esri.com/en-us/covid-19/overview#image3
https://graphics.reuters.com/HEALTH-CORONAVIRUS/USA-TRENDS/dgkvlgkrkpb/index.html
https://covidtracking.com/data#chart-annotations

https://en.wikipedia.org/wiki/List_of_geographic_centers_of_the_United_States
https://developers.google.com/public-data/docs/canonical/states_csv
"""

