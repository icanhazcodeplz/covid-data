import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import cufflinks as cf
from urllib.request import urlopen
import json
from preprocess_data import *

#FIXME: Update file locations
CASES_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
DEATHS_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'

# CASES_FILE = 'time_series_covid19_confirmed_US.csv'
# DEATHS_FILE = 'time_series_covid19_deaths_US.csv'

print('Loading {}'.format(CASES_FILE))
cases_df = pd.read_csv(CASES_FILE).dropna()

print('Loading {}'.format(DEATHS_FILE))
deaths_df = pd.read_csv(DEATHS_FILE).dropna()

# Convert fips to string and front fill zeros to get to 5 characters
cases_df['FIPS'] = cases_df['FIPS'].apply(lambda n: str.zfill(str(int(n)), 5))
deaths_df['FIPS'] = deaths_df['FIPS'].apply(lambda n: str.zfill(str(int(n)), 5))

case_ave_df = cases_df.set_index('FIPS')
case_ave_df = case_ave_df.iloc[:, -15:].T
case_ave_df = case_ave_df.diff()[1:]
case_ave_df = case_ave_df.clip(lower=0) #FIXME: Remove positive tests from previous day instead?
case_ave_df = case_ave_df.rolling(7, ).mean().dropna()
case_ave = case_ave_df.iloc[-1,:]
case_ave.name = '7day_ave'

fips_pop_df = deaths_df[['FIPS', 'Population', 'Combined_Key']].set_index('FIPS')
fips_pop_df = pd.concat([fips_pop_df, case_ave], axis=1)
fips_pop_df = fips_pop_df[fips_pop_df['Population'] > 0]

fips_pop_df['ave_rate'] = fips_pop_df['7day_ave'] / fips_pop_df['Population'] * 100000
fips_pop_df['ave_rate'] = round(fips_pop_df['ave_rate'], 1)

case_rate_df = fips_pop_df[['Combined_Key', 'ave_rate']].reset_index()


with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)


fig_map = px.choropleth_mapbox(case_rate_df, geojson=counties, locations='FIPS', color='ave_rate',
                               color_continuous_scale='Reds', #"YlOrRd",
                               range_color=(0, 40),
                               mapbox_style="carto-positron",
                               zoom=3, center={"lat": 37.0902, "lon": -95.7129},
                               opacity=0.5,
                               hover_data=['Combined_Key'],
                               labels=dict(Combined_Key='County', ave_rate='Average Daily Cases Per 100k', FIPS='id')
                               )
fig_map.update_layout(margin={"r":0, "t":0, "l":0, "b":0})
# fig_map.show()


county_keys = cases_df['Combined_Key'].unique()
county_keys = [dict(label=k, value=k) for k in county_keys]

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server


def county_fig(county_df, county_key):
    fig = county_df.iplot(asFigure=True, kind='bar', barmode='group',
                          title='New Cases and Deaths in {}'.format(county_key))
    fig.update_layout(autosize=False, width=650, height=350,
                      margin=dict(l=5, r=5, b=5, t=70, pad=1),
                      paper_bgcolor="LightSteelBlue",
                      xaxis=dict(tickformat='%b %d', tickmode='linear',
                                 tick0=county_df.index[0], dtick=14 * 86400000.0,
                                 showgrid=True, ticks="outside",
                                 tickson="boundaries", ticklen=3, tickangle=45)
                      )
    return fig


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
    html.H2(children='Covid-19 Hot Spots'),
    # html.H6('Search for a County'),
    # dcc.Dropdown(
    #     id='county-dropdown',
    #     options=county_keys,
    #     value=''
    # ),
    # html.Div(id='dd-output'),
    dcc.Graph(figure=fig_map)
])


# @app.callback(
#     dash.dependencies.Output('dd-output', 'children'),
#     [dash.dependencies.Input('county-dropdown', 'value')])
def update_output(county_selection):
    if county_selection:
        county_df = county_data(cases_df, deaths_df, county_selection)
        summary_df = county_summary(county_df)
        fig = county_fig(county_df, county_selection)
        return html.Div(children=[generate_table(summary_df),
            dcc.Graph(figure=fig)])

    return ''


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)

#
# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
#
# app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
#
# colors = {
#     'background': '#111111',
#     'text': '#7FDBFF'
# }
#
# # assumes you have a "wide-form" data frame with no index
# # see https://plotly.com/python/wide-form/ for more options
# df = pd.DataFrame({"x": [1, 2, 3], "SF": [4, 1, 2], "Montreal": [2, 4, 5]})
#
# fig = px.bar(df, x="x", y=["SF", "Montreal"], barmode="group")
#
# fig.update_layout(plot_bgcolor=colors['background'], paper_bgcolor=colors['background'], font_color=colors['text'])
#
# app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
#     html.H1(
#         children='Hello Dash',
#         style={
#             'textAlign': 'center',
#             'color': colors['text']
#         }
#     ),
#
#     html.Div(children='Dash: A web application framework for Python.', style={
#         'textAlign': 'center',
#         'color': colors['text']
#     }),
#
#     dcc.Graph(
#         id='example-graph-2',
#         figure=fig
#     )
# ])
#
# if __name__ == '__main__':
#     app.run_server(debug=True)
