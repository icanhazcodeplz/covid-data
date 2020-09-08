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
          'doubleClick': False}


#### LAYOUT ###################################################################
def table_and_graph_card(title, table, graph):
    """Return a dbc Card object that shows a table and graph.

    Args:
        title (str): Title of card displayed as H4
        table (dash_html_components.Th): html table components
        graph (plotly.graph_objects.Figure): Plotly graph

    Returns:
        dash_bootstrap_components.Card: Bootstrap card

    """
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
                             interval=1*1000 * 60 * 60, # One hour in milliseconds
                             n_intervals=0),
                dbc.Row([
                    html.Div(id='usa-card'),
                    dbc.Card([
                        dcc.Graph(id='states-map',
                                  config=config),
                        html.H5('Click on a state or select from the dropdown to see state-view',
                                style={'textAlign': 'center'}),
                    ], color='light', inverse=False, body=True),
                ], justify='center'),
            ], color='secondary', body=True)
        ], width='auto'),
    ], justify='center',),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.Row([  # Row just for the state-dropdown
                    dbc.Col([
                        dcc.Dropdown(id='state-dropdown',
                                     options=[dict(value=s, label=s) for s in fd.states_meta_df.index],
                                     placeholder='Select a state',
                                     clearable=False,
                                     style={"width": "180px",
                                            "font-size": "large",}),
                    ], width=3),
                ], justify='center'),
                dbc.Row([  # Row for the counties map and data card
                    dcc.Loading([
                        dbc.Card([
                            dcc.Graph(id='counties-map',
                                      config={'displayModeBar': False,
                                              'doubleClick': False}), # TODO: DashBug report, doubleClick = False does nothing
                        ], color='light', body=True),
                    ], type='default'),
                    dcc.Loading([html.Div(id='state-or-county-card')], type='default'),
                ], justify='center'),
            ], color='secondary', body=True),
        ], width='auto'),
    ], id='county-row', justify='center'),

    dbc.Row([
        dcc.Markdown("""
            Built with [Plotly Dash](https://plotly.com/dash/). Data from 
            [Johns Hopkins University](https://github.com/CSSEGISandData/COVID-19). 
            Source code at [Github](https://github.com/icanhazcodeplz/covid-data). 
            Inspiration from 
            [The New York Times](https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html).
            """),
    ], justify='center',)
], fluid=True)


#### CALLBACKS ################################################################

@app.callback(
    [Output('usa-card', 'children'),
     Output('states-map', 'figure')],
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=False)
def update_usa_data(_):
    # Using the interval-component trigger on initial load ensures that the
    # data is fresh. This is a bit hacky, but I couldn't find a better solution
    return (table_and_graph_card('USA',
                                 trend_table(fd.states_df['USA']),
                                 CasesGraph.usa_graph(fd.states_df['USA'])),
            states_map(fd.states_map_df, fd.states_df.index[-1]))


@app.callback(
    Output('state-dropdown', 'value'),
    [Input('states-map', 'clickData')],
    prevent_initial_call=False)
def set_state_dropdown_from_map_click(clickData):
    # Update the selected state in the dropdown if the user clicks on a state
    # on the states-map
    trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'states-map':
        state = clickData['points'][0]['customdata']
    else:
        # The full map of the US will be the first shown
        state = 'USA'
    return state


@app.callback(
    Output('counties-map', 'figure'),
    [Input('state-dropdown', 'value')],
    prevent_initial_call=False)
def update_counties_map_from_dropdown(value):
    # If a user selects a state, only show the counties for that state
    if value is None:
        value = 'USA'
    return counties_map(fd.counties_map_df, fd.counties_geo, fd.states_meta_df, value)


@app.callback(
    Output('state-or-county-card', 'children'),
    [Input('state-dropdown', 'value'),
     Input('counties-map', 'clickData')],
    prevent_initial_call=True)
def make_state_or_county_card(value, clickData):

    trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'state-dropdown':
        # for that state
        if value == 'USA':
            return None
        title = value
        table = trend_table(fd.states_df[value])
        ser = fd.states_df[value]
        pop = fd.state_pop_dict[value]
        graph = CasesGraph.state_or_county_graph(ser, pop)

    if trigger == 'counties-map':
        # If a county is clicked from the counties-map,
        # the state-or-county-card will display data from that county
        fips = clickData['points'][0]['location']
        title = fd.fips_county_dict[fips]
        if fd.counties_df[fips].sum() == 0:
            return html.H4('No cases have been reported in {}'.format(title))

        table = trend_table(fd.counties_df[fips])
        ser = fd.counties_df[fips]
        pop = fd.fips_pop_dict[fips]
        graph = CasesGraph.state_or_county_graph(ser, pop)

    return table_and_graph_card(title, table, graph)


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)

"""
TODO:
- Add documentation
- Add tests
- Update to python 3.8

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

