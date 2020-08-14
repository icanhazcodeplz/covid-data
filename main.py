import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from __init__ import *
from data_handling.main import *
from preprocess_data import *
from visuals import *


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = 'COVID-19 Dashboard'

#### GLOBAL VARS ##############################################################
fd = FreshData()
county_keys_old = [dict(label=k, value=k) for k in fd.pop_df['Combined_Key'].unique()]
county_keys = [dict(value=k, label=v) for k, v in fd.fips_county_dict.items()]
with open('geojson-counties-fips.json') as f:
    counties = json.load(f)
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


app.layout = html.Div(children=[
    dcc.Markdown('''
    # COVID-19 Hot Spots
    Welcome! This dashboard is, to say the least, a work in progress.
    It is built using [Plotly Dash](https://plotly.com/dash/) with data from 
    [Johns Hopkins University](https://github.com/CSSEGISandData/COVID-19). 
    The source code is available on 
    [Github](https://github.com/icanhazcodeplz/covid-data). The inspiration for 
    the map is from the [NYTimes](https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html).
    '''),
    dcc.Graph(figure=covid_map(fd, counties), id='cases-map'),
    html.Div([
        html.Div([
            html.Div([
                html.H5('For more data, click on a county or select from the dropdown'),
            ], className="six columns"),

            html.Div([
                dcc.Dropdown(
                id='county-dropdown',
                options=county_keys,
                placeholder='Select a county'),
            ], className="six columns"),#, style=dict(width='50%')),
        ], className="row")
    ], className="row"),
    html.Div(id='county-display'),
    ])


def county_display(fips):
    refreshed = fd.refresh_if_needed()
    county_name = fd.fips_county_dict[fips]
    county_pop = fd.fips_pop_dict[fips]
    county_df = county_data(fd.cases_df[fips], county_pop)
    if county_df is None:
        return html.H4('No recorded positive cases in {}'.format(county_name))
    # summary_df, trend = county_summary(county_s, county_rate_s, )
    fig = county_fig(county_df)
    return html.Div(children=[
        html.H4('Data for {}'.format(county_name)),
        # generate_table(summary_df),
        dcc.Graph(figure=fig),
        html.H1(''),
        html.H1(''),
        dcc.Markdown('''
            Debug Info
            Refreshed {}. Last refresh {}
            Fips = {}. Pop = {}
            '''.format(refreshed, fd.last_refresh_time, fips, county_pop))
    ])


@app.callback(
    Output('county-display', 'children'),
    [Input('cases-map', 'clickData'),
     Input('county-dropdown', 'value')])
def map_click_or_county_selection(clickData, value):
    ctx = dash.callback_context
    if not ctx.triggered:
        return ''
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'cases-map':
        fips = clickData['points'][0]['location']
    elif trigger == 'county-dropdown':
        fips = value
    return county_display(fips)


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)

