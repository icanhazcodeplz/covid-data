import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
from preprocess_data import preprocess_data

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server


def generate_table(dataframe, max_rows=10):
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in dataframe.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])


df = preprocess_data()
app.layout = html.Div(children=[
    html.H2(children='Whatcom County Covid-19 Tracker'),

    generate_table(df),

    html.Br(),
    # html.Div(children='Last update: {}'.format(date_yest)),
    # dcc.Graph(
    #     id='example-graph',
    #     figure=fig
    # )
])
# app.layout = dash_table.DataTable(
#     id='table',
#     columns=[{"name": i, "id": i} for i in df.columns],
#     data=df.to_dict('records'),
# )

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
