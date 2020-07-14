import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import cufflinks as cf
from preprocess_data import preprocess_data

STATE = 'Washington'
COUNTY = 'Whatcom'

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

df, table_df = preprocess_data(STATE, COUNTY)

fig = df.iplot(asFigure=True, kind='bar', barmode='group',
               title='New Cases and Deaths in {} County, {} '.format(COUNTY,
                                                                     STATE))
fig.update_layout(autosize=False, width=650, height=350,
                  margin=dict(l=5, r=5, b=5, t=70, pad=1),
                  paper_bgcolor="LightSteelBlue",
                  xaxis=dict(tickformat='%b %d', tickmode='linear',
                             tick0=df.index[0], dtick=14 * 86400000.0,
                             showgrid=True, ticks="outside",
                             tickson="boundaries", ticklen=3, tickangle=45)
                  )
# fig.show()
print()


def generate_table(dataframe, max_rows=10):
    print('in gen_table')
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


app.layout = html.Div(children=[
    html.H2(children='Whatcom County Covid-19 Tracker'),
    generate_table(table_df),

    html.Br(),
    # html.Div(children='Last update: {}'.format(date_yest)),
    dcc.Graph(
        id='example-graph',
        figure=fig
    )
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
