import pandas as pd
import re

state = 'Washington'
county = 'Whatcom'


def counts_by_county(df, state):
    df_state = df[df['Province_State'] == state].set_index('Admin2')
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in
                      df_state.columns]
    df_state = df_state.iloc[:, date_cols_bool]
    df_state = df_state.T
    df_state.index = pd.to_datetime(df_state.index)
    return df_state


cases = pd.read_csv('time_series_covid19_confirmed_US.csv')
deaths = pd.read_csv('time_series_covid19_deaths_US.csv')

state_cases_diff = counts_by_county(cases, state).diff()
state_deaths_diff = counts_by_county(deaths, state).diff()


def data_for_table(name, ser):
    yest = ser.iloc[-1]
    week = ser.tail(7).sum()
    two_week_ago = ser.tail(14).head(7).sum()
    if two_week_ago > 0:
        week_change = (week / two_week_ago - 1) * 100
    else:
        week_change = 100
    week_change = int(round(week_change))
    return name, yest, week, two_week_ago, str(week_change) + '%'


cases = data_for_table('Positive Tests', state_cases_diff[county])
deaths = data_for_table('Deaths', state_deaths_diff[county])
df = pd.DataFrame(data=[cases, deaths],
                  columns=['', 'Yesterday', 'Past Week', 'Two Weeks Ago',
                           'Weekly Change'])

df.to_pickle('table_df.pkl')


## Ideas
# https://www.larimer.org/health/communicable-disease/coronavirus-covid-19/larimer-county-positive-covid-19-numbers
# https://www.digitalocean.com/community/pages/hub-for-good
# https://covid19-dash.herokuapp.com/
# https://covid19mtl.ca/en

## Cloud
# https://console.cloud.google.com/freetrial/signup/tos?_ga=2.216095126.1215990170.1594321151-1114669994.1594321151&pli=1