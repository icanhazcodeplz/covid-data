import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from constants import *
from data_handling import *
from visuals import *


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = 'COVID-19 Dashboard'

#### GLOBAL VARS ##############################################################
with open('{}/geojson-counties-fips.json'.format(DATA_DIR)) as f:
    counties = json.load(f)
fd = FreshData()
county_keys = [dict(value=k, label=v) for k, v in fd.fips_county_dict.items()]
states_df = load_states_csv()
#### END GLOBAL VARS ##########################################################


def generate_table(dataframe, max_rows=10):
    return html.Table([
        html.Thead(html.Tr([html.Th(col) for col in dataframe.columns])),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])

#FIXME: Not all of these are actually removed! Might be plotly bug
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

app.layout = html.Div(children=[
    dcc.Markdown("""
    # COVID-19 Hot Spots
    Welcome! This dashboard is, to say the least, a work in progress.
    It is built using [Plotly Dash](https://plotly.com/dash/) with data from 
    [Johns Hopkins University](https://github.com/CSSEGISandData/COVID-19). 
    The source code is available on 
    [Github](https://github.com/icanhazcodeplz/covid-data). The inspiration for 
    the map is from the [NYTimes](https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html).
    """),
    html.Div([
        html.Div([
            html.Button('Reset Map', id='reset-button'),
        ], className="three columns"),
        html.Div([
            dcc.Markdown('Click on a county or select from the dropdown'),
        ], className="three columns"),
        # FIXME: reset dropdown when county is clicked
        # https://community.plotly.com/t/how-to-clear-the-value-in-dropdown-via-callback/28777
        html.Div([
            dcc.Dropdown(
            id='county-dropdown',
            options=county_keys,
            placeholder='Select a county'),
        ], className="three columns"),#, style=dict(width='50%')),
    ], className="row"),
    dcc.Graph(figure=covid_map(fd, counties, states_df), id='cases-map', config={'modeBarButtonsToRemove': modebar_buttons_to_remove}),
    html.Div(id='county-display'),
    ])


def county_display(fips):
    refreshed = fd.refresh_if_needed()
    county_name = fd.fips_county_dict[fips]
    county_pop = fd.fips_pop_dict[fips]
    county_df = county_data(fd.cases_df[fips], county_pop)
    debug_str = dcc.Markdown('''Debug Info: Refreshed {}. Last refresh {}. Fips = {}. Pop = {}
            '''.format(refreshed, fd.last_refresh_time, fips, county_pop))
    if county_df is None:
        return html.Div([html.H4('No recorded positive cases in {}'.format(county_name)),
                        debug_str])
    # summary_df, trend = county_summary(county_s, county_rate_s, )
    fig = county_fig(county_df)
    return html.Div(children=[
        html.H4('Data for {}'.format(county_name)),
        # generate_table(summary_df),
        dcc.Graph(figure=fig, config={'modeBarButtonsToRemove': modebar_buttons_to_remove}),
        html.H1(''),
        html.H1(''),
        debug_str
    ])


@app.callback(
    [Output('cases-map', 'figure'),
    Output('county-display', 'children')],
    [Input('cases-map', 'clickData'),
     Input('county-dropdown', 'value'),
     Input('reset-button', 'n_clicks')])
def map_click_or_county_selection(clickData, value, _reset_btn):
    ctx = dash.callback_context
    if not ctx.triggered:  # Initial loading
        return covid_map(fd, counties, states_df), ''

    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'cases-map':
        fips = clickData['points'][0]['location']
    elif trigger == 'county-dropdown':
        fips = value
        if fips is None:
            return ''
    elif trigger == 'reset-button':
        return covid_map(fd, counties, states_df), ''

    return covid_map(fd, counties, states_df, fips), county_display(fips)


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
"""

