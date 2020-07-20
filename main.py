import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import cufflinks as cf
from preprocess_data import county_list, all_county_data

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
    # fig.show()
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
    html.H2(children='Covid-19 Tracker'),
    html.H6('Search for a County'),
    dcc.Dropdown(
        id='county-dropdown',
        options=county_list(),
        value=''
    ),
    html.Div(id='dd-output'),
])


@app.callback(
    dash.dependencies.Output('dd-output', 'children'),
    [dash.dependencies.Input('county-dropdown', 'value')])
def update_output(value):
    if value:
        county_df, summary_df = all_county_data(value)
        fig = county_fig(county_df, value)
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
