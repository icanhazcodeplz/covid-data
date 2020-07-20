import pandas as pd
import re

#FIXME: Update file locations
CASES_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
DEATHS_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'

# CASES_FILE = 'time_series_covid19_confirmed_US.csv'
# DEATHS_FILE = 'time_series_covid19_deaths_US.csv'


def county_list():
    cases = pd.read_csv(CASES_FILE)
    county_keys = cases['Combined_Key'].unique()
    return [dict(label=k, value=k) for k in county_keys]


def county_series(df, county_key):
    county_s = df[df['Combined_Key'] == county_key].set_index('Admin2')
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in
                      county_s.columns]
    county_s = county_s.iloc[:, date_cols_bool]
    county_s = county_s.T
    county_s.index = pd.to_datetime(county_s.index)
    return county_s


def county_data(county_key):
    print('Reading CSV')
    cases = pd.read_csv(CASES_FILE)
    deaths = pd.read_csv(DEATHS_FILE)

    county_cases = county_series(cases, county_key).diff()[1:]
    county_deaths = county_series(deaths, county_key).diff()[1:]

    df = pd.concat([county_cases, county_deaths], axis=1)
    df.columns = ['cases', 'deaths']

    while (df['cases'][0] == 0.0) and (df['deaths'][0] == 0.0):
        df = df[1:]

    #TODO: Handle case where there are no positive values anywhere
    df = df.clip(lower=0) #FIXME: Remove positive tests from previous day instead?
    return df


def county_summary(county_df):

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

    cases = data_for_table('Positive Tests', county_df['cases'])
    deaths = data_for_table('Deaths', county_df['deaths'])

    summary_df = pd.DataFrame(data=[cases, deaths],
                              columns=['', 'Yesterday', 'Past Week',
                                       'Two Weeks Ago', 'Weekly Change'])

    return summary_df


def all_county_data(county_key):
    county_df = county_data(county_key)
    summary_df = county_summary(county_df)
    return county_df, summary_df

if __name__ == '__main__':
    county_data('Bibb, Alabama, US')


## Ideas
# https://www.larimer.org/health/communicable-disease/coronavirus-covid-19/larimer-county-positive-covid-19-numbers
# https://www.digitalocean.com/community/pages/hub-for-good
# https://covid19-dash.herokuapp.com/
# https://covid19mtl.ca/en
# https://covid19-dashboard-online.herokuapp.com/

## Cloud
# https://console.cloud.google.com/freetrial/signup/tos?_ga=2.216095126.1215990170.1594321151-1114669994.1594321151&pli=1
