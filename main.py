import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from constants import *
from data_handling import *
from visuals import *


app = dash.Dash(external_stylesheets=[dbc.themes.UNITED],
                prevent_initial_callbacks=True)

app.title = 'COVID-19 Hot Spots'
server = app.server

#### GLOBAL VARS ##############################################################
with open('{}/geojson-counties-fips.json'.format(DATA_DIR)) as f:
    counties_geo = json.load(f)
fd = FreshData()
states_meta_df = load_states_csv()
state_keys = [dict(value=s, label=s) for s in states_meta_df.index]

# FIXME: will fig_map update when the data refreshes???

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

#### LAYOUT ###################################################################

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("COVID-19 Hot Spots", style={'textAlign': 'center'}),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Interval(id='interval-component',
                                 interval=1*1000 * 60 * 60, # in milliseconds
                                 n_intervals=0),
                    dcc.Graph(figure=make_states_map(fd, states_meta_df),
                              id='usa-map',
                              config={'scrollZoom': False,
                                      'displayModeBar': False,
                                      'doubleClick': False}), # TODO: Bug report, doubleClick = False does nothing
                    html.H6('Click on a state or select from the dropdown to see county-level data',
                            style={'textAlign': 'center'}),
                    dbc.Row([
                        dbc.Col([
                            dcc.Dropdown(id='state-dropdown',
                                         options=state_keys,
                                         placeholder='Select a state',
                                         clearable=False),
                        ], width=4),
                    ], justify='center'),
                ])
            ], color='secondary')
        ], width='auto'),
    ], justify='center',),

    dbc.Row([
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    html.H2(id='state-card-header')
                ], justify='center'),
                dbc.Row([
                    dbc.Col([
                        dcc.Loading([
                            dcc.Graph(id='state-map',
                                      figure=make_counties_map(fd,
                                                  counties_geo,
                                                  states_meta_df, state='USA'),
                                      config={'displayModeBar': False}),
                                ], type='default')
                            ], width='auto'),
                            dbc.Col([
                                dcc.Loading([html.Div(id='county-graph')], type='default'),
                            ], width='auto'),
                        ], justify='center'),
                    ]),
        ], color='light'),
    ], id='county-row', justify='center'),

    dbc.Row([
        dcc.Markdown("""
            Built with [Plotly Dash](https://plotly.com/dash/). Data from 
            [Johns Hopkins University](https://github.com/CSSEGISandData/COVID-19). 
            Source code at
            [Github](https://github.com/icanhazcodeplz/covid-data). Inspiration from 
             the [New York Times](https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html).
            """),
    ], justify='center',)
], fluid=True)


def make_state_graph_dcc(state):
    if state is None:
        return ''
    fd.refresh_if_needed()
    state_pop = fd.state_pop_dict[state]
    state_df = cases_data_for_graph(fd.state_df[state], state_pop)
    fig = make_cases_graph(state_df, state)
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


@app.callback(Output('usa-map', 'figure'),
              [Input('interval-component', 'n_intervals')])
def update_usa_graph(n):
    return make_states_map(fd, states_meta_df)


@app.callback(
    Output('state-dropdown', 'value'),
    [Input('usa-map', 'clickData')], #, Input('reset-button', 'n_clicks')],
    prevent_initial_call=False)
def map_click_or_county_selection(clickData): #, _n_clicks):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'usa-map':
        state = clickData['points'][0]['customdata']
    else:
        state = 'USA'
    return state


@app.callback(
    Output('state-card-header', 'children'),
    [Input('state-dropdown', 'value')])
def update_state_card_header(value):
    if value is None:
        value = 'USA'
    return value


@app.callback(
    Output('state-map', 'figure'),
    [Input('state-dropdown', 'value')])
def update_state_map(value):
    if value is None:
        value = 'USA'
    return make_counties_map(fd, counties_geo, states_meta_df, state=value)


@app.callback(
    Output('county-graph', 'children'),
    [Input('state-dropdown', 'value'),
     Input('state-map', 'clickData')])
def make_county_display(value, clickData):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'state-dropdown':
        fig = make_cases_subplots(fd, value)
    if trigger == 'state-map':
        state = clickData['points'][0]['customdata']
        fips = clickData['points'][0]['location']
        fig = make_cases_subplots(fd, state, fips)

    return dcc.Graph(figure=fig, config={'displayModeBar': False})


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)



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

def generate_table(dataframe, max_rows=10):
    return html.Table([
        html.Thead(html.Tr([html.Th(col) for col in dataframe.columns])),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])

"""

