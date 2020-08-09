import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import numpy as np
import pandas as pd
import cufflinks as cf
import json

from __init__ import *
from preprocess_data import *


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

#### GLOBAL VARS ##############################################################
fd = FreshData()
county_keys_old = [dict(label=k, value=k) for k in fd.pop_df['Combined_Key'].unique()]
county_keys = [dict(value=k, label=v) for k, v in fd.fips_county_dict.items()]
with open('geojson-counties-fips.json') as f:
    counties = json.load(f)
#### END GLOBAL VARS ##########################################################


def covid_map():
    fd.refresh_if_needed()
    f = px.choropleth_mapbox(fd.map_df, geojson=counties, locations='FIPS', color='ave_rate',
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

    df = df.round(1)
    ### find first tick spot
    total_days = len(df)
    days_back_to_start = int(total_days / 14) * 14 + 2
    # Hacky fix to add extra day at end so that the tick-mark will show
    new_i = df.index[-1] + timedelta(days=1)
    df.loc[new_i] = [np.nan] * len(df.columns)

    f = px.line(df['cases_ave'], title='New Cases in {}'.format(county_name))
    # f.update_xaxes()
    f.update_traces(name='7 Day Average', hovertemplate=None)
    f.add_bar(y=df['cases'], x=df.index, name='New Cases')
    f.update_layout(autosize=False, width=650, height=350,
                    margin=dict(l=5, r=5, b=5, t=70, pad=1),
                    paper_bgcolor="LightSteelBlue",
                    hovermode='x unified',
                    yaxis=dict(title=None),
                    xaxis=dict(title=None,tickformat='%b %d', tickmode='linear',
                                tick0=df.index[-days_back_to_start],
                                dtick=14 * 86400000.0,
                                showgrid=True, ticks="outside",
                                tickson="boundaries", ticklen=3, tickangle=45)

                      )
    # f.show()
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


app.layout = html.Div(children=[
    html.H1('Covid-19 Hot Spots'),
    dcc.Graph(figure=covid_map(), id='cases-map'),
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
    fig = county_fig(county_df, county_name)
    return html.Div(children=[
        # html.H4('Data for {}'.format(county_name)),
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

