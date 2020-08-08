import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import cufflinks as cf
from urllib.request import urlopen
import json
from apscheduler.schedulers.background import BackgroundScheduler

from __init__ import *
from preprocess_data import *

get_and_save_data()

sched = BackgroundScheduler()

@sched.scheduled_job('cron', day_of_week='mon-sun', hour=0)
def scheduled_job():
    print('Getting data, processing, and saving to pickles')
    get_and_save_data()

sched.start()


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

with open('geojson-counties-fips.json') as f:
    counties = json.load(f)


def covid_map():
    map_df = DataHandler().load_pkl_file('map_df')
    f = px.choropleth_mapbox(map_df, geojson=counties, locations='FIPS', color='ave_rate',
                                   color_continuous_scale='Reds', #"YlOrRd",
                                   range_color=(0, 40),
                                   mapbox_style="carto-positron",
                                   zoom=3, center={"lat": 37.0902, "lon": -95.7129},
                                   opacity=0.5,
                                   hover_data=dict(FIPS=False, Combined_Key=True, week_ave=':.1f', ave_rate=':.1f'),
                                   labels=dict(Combined_Key='County',
                                               week_ave='Average Daily Cases',
                                               ave_rate='Average Daily Cases Per 100k')
                                   )
    f.update_layout(margin={"r":0, "t":0, "l":0, "b":0})
    return f


def county_fig(df, county_name):
    #TODO: Update Colors
    #TODO: Get x-ticks backwards from end
    f = px.line(df['cases_ave'], title='New Cases in {}'.format(county_name))
    f.update_traces(name='7 Day Average')
    f.add_bar(y=df['cases'], x=df.index, name='New Cases')
    f.update_layout(autosize=False, width=650, height=350,
                      margin=dict(l=5, r=5, b=5, t=70, pad=1),
                      paper_bgcolor="LightSteelBlue",
                      xaxis=dict(tickformat='%b %d', tickmode='linear',
                                 tick0=df.index[0], dtick=14 * 86400000.0,
                                 showgrid=True, ticks="outside",
                                 tickson="boundaries", ticklen=3, tickangle=45)
                      )
    return f


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
    dcc.Graph(figure=covid_map(), id='cases-map'),
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


# fips_county_dict = read_pkl('fips_county_dict')
# fips_pop_dict = read_pkl('fips_pop_dict')
pop_df = DataHandler().load_pkl_file('pop_df')
fips_pop_dict = pop_df['Population'].to_dict()
fips_county_dict = pop_df['Combined_Key'].to_dict()

@app.callback(
    Output('click-data', 'children'),
    [Input('cases-map', 'clickData')])
def county_display(clickData):
    if clickData:
        fips = clickData['points'][0]['location']
        county_name = fips_county_dict[fips]
        county_pop = fips_pop_dict[fips]

        cases_df = DataHandler().load_pkl_file('cases_df')
        county_df = county_data(cases_df[fips], county_pop)
        if county_df is None:
            return html.H4('No recorded positive cases in {}'.format(county_name))

        # summary_df, trend = county_summary(county_s, county_rate_s, )

        fig = county_fig(county_df, county_name)
        return html.Div(children=[
            html.H4('Data for {}'.format(county_name)),
            # generate_table(summary_df),
            dcc.Graph(figure=fig)])

    return ''


# @app.callback(
#     Output('dd-output', 'children'),
#     [Input('county-dropdown', 'value')])


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)

