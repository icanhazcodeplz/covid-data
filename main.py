import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import cufflinks as cf
from urllib.request import urlopen
import json
from __init__ import *
from preprocess_data import *

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server


with open('geojson-counties-fips.json') as f:
    counties = json.load(f)


def covid_map():
    map_df = read_pkl('map_df')
    f = px.choropleth_mapbox(map_df, geojson=counties, locations='FIPS', color='ave_rate',
                                   color_continuous_scale='Reds', #"YlOrRd",
                                   range_color=(0, 40),
                                   mapbox_style="carto-positron",
                                   zoom=3, center={"lat": 37.0902, "lon": -95.7129},
                                   opacity=0.5,
                                   hover_data=dict(FIPS=False, Combined_Key=True, ave_rate=':.1f', week_ave=':.1f'),
                                   labels=dict(Combined_Key='County',
                                               ave_rate='Average Daily Cases Per 100k',
                                               week_ave='Average Daily Cases')
                                   )
    f.update_layout(margin={"r":0, "t":0, "l":0, "b":0})
    return f

get_and_save_data()
fig_map = covid_map()

def county_fig(county_s, county_ave_s, county_key):
    #TODO: Update Colors
    f = px.line(county_ave_s, title='New Cases in {}'.format(county_key))
    f.update_traces(name='7 Day Average')
    f.add_bar(y=county_s, x=county_s.index, name='New Cases')
    f.update_layout(autosize=False, width=650, height=350,
                      margin=dict(l=5, r=5, b=5, t=70, pad=1),
                      paper_bgcolor="LightSteelBlue",
                      xaxis=dict(tickformat='%b %d', tickmode='linear',
                                 tick0=county_s.index[0], dtick=14 * 86400000.0,
                                 showgrid=True, ticks="outside",
                                 tickson="boundaries", ticklen=3, tickangle=45)
                      )
    return f
#
# fips = '56039'
# county_s = clean_county_s(new_cases_df[fips])
# county_ave_s = clean_county_s(case_ave_df[fips])
# county_fig(county_s, county_ave_s, 'HAHA')


def generate_table(dataframe, max_rows=10):
    return html.Table([
        html.Thead(html.Tr([html.Th(col) for col in dataframe.columns])),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])

# county_keys = [dict(label=k, value=k) for k in pop_df['Combined_Key'].unique()]

app.layout = html.Div(children=[
    dcc.Markdown(
        '''
        # Covid-19 Hot Spots
        ##### Click on a County for more information
        '''),
    dcc.Graph(figure=fig_map, id='cases-map'),
    # html.Div(className='row', children=[
    #     html.Div([
    #         dcc.Markdown("""
    #                 **Click Data**
    #
    #                 Click on points in the graph.
    #             """),
    #         html.Pre(id='click-data', style=styles['pre']),
    #         ], className='three columns'),
    #     ]),
    # html.H6('Search for a County'),
    # dcc.Dropdown(
    #     id='county-dropdown',
    #     options=county_keys,
    #     value=''
    # ),
    html.Div(id='click-data'),
    ])


fips_county_dict = read_pkl('fips_county_dict')

@app.callback(
    Output('click-data', 'children'),
    [Input('cases-map', 'clickData')])
def county_display(clickData):
    if clickData:
        fips = clickData['points'][0]['location']
        case_ave_df = read_pkl('case_ave_df')
        new_cases_df = read_pkl('new_cases_df')
        new_cases_rate_df = read_pkl('new_cases_rate_df')

        county_selection = fips_county_dict[fips]
        county_s = clean_county_s(new_cases_df[fips])
        county_ave_s = clean_county_s(case_ave_df[fips])
        if county_s is None:
            return html.H4('No recorded positive cases in {}'.format(county_selection))

        county_rate_s = clean_county_s(new_cases_rate_df[fips])
        summary_df = county_summary(county_s, county_rate_s)

        fig = county_fig(county_s, county_ave_s, county_selection)
        return html.Div(children=[
            html.H4('Data for {}'.format(county_selection)),
            generate_table(summary_df),
            dcc.Graph(figure=fig)])

    return ''


# @app.callback(
#     Output('dd-output', 'children'),
#     [Input('county-dropdown', 'value')])


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)

