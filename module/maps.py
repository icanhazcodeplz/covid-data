import plotly.graph_objects as go
from copy import deepcopy

MAP_WIDTH = 625
Z_MAX = 50
COLORBAR = dict(x=1, title=dict(text='Average<br>Daily<br>Cases<br>per 100k',
                                font=dict(size=14, color='#A10C0C')))


def states_map(states_map_df, date):
    """Create a Choropleth plot of the US states

    Args:
        states_map_df (pandas.DataFrame): Index are names of states, columns must include 'abbr', 'ave_rate', and 'text'
        date (datetime): Date that states_map_df was created

    Returns:
        plotly.graph_objects.Figure:

    """
    fig = go.Figure(data=go.Choropleth(
        locationmode='USA-states',
        locations=states_map_df['abbr'],
        z=states_map_df['ave_rate'].astype(float),
        customdata=states_map_df.index.to_list(),
        text=states_map_df['text'],
        zmin=0,
        zmax=Z_MAX,
        colorscale='Reds',
        hovertemplate='%{text} <extra></extra>',
        colorbar=COLORBAR,
    ))

    fig.update_layout(
        margin=dict(l=3, r=3, b=3, t=0, pad=0),
        geo_scope='usa',
        width=MAP_WIDTH,
        height=310,
        annotations=[dict(
            x=0.0,
            y=0.0,
            xref='paper',
            yref='paper',
            text='As of {}'.format(date.strftime('%b %-d')),
            showarrow=False
        )]
    )
    return fig


def counties_map(counties_map_df, counties_geo, states_meta_df, state):
    """County-level map that shows the average cases per day rate

    Args:
        counties_map_df (pandas.DataFrame): from FreshData
        counties_geo (dict): from FreshData
        states_meta_df (pandas.DataFrame): from FreshData
        state (str): US state to show a map of

    Returns:
        plotly.graph_objects.Figure:

    """
    df = counties_map_df

    geo = deepcopy(counties_geo)
    if state != 'USA':
        df = df[df['state'] == state]
        state_num = states_meta_df.loc[state, 'fips']
        l = [f for f in counties_geo['features'] if
             f['properties']['STATE'] == state_num]
        geo['features'] = l

    fig = go.Figure(
        go.Choroplethmapbox(
            colorbar=COLORBAR,
            geojson=geo,
            locations=df['fips'],
            z=df['ave_rate'],
            customdata=df['state'],
            text=df['text'],
            zmin=0,
            zmax=Z_MAX,
            hovertemplate='%{text} <extra></extra>',
            colorscale='Reds',
            meta=state
        ),
    )

    fig.update_layout(
        # you will need your own mapbox token,
        mapbox_accesstoken=open("./.mapbox_token").read(),
        mapbox_style='light',
        width=MAP_WIDTH,
        height=414,
        margin=dict(l=3, r=3, b=3, t=3, pad=10),
        mapbox_zoom=states_meta_df.loc[state, 'zoom'],
        mapbox_center=dict(lat=states_meta_df.loc[state, 'lat'],
                           lon=states_meta_df.loc[state, 'lon']),
    )

    return fig
