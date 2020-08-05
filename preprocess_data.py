import pandas as pd
import re
from __init__ import *


def read_pkl(name):
    file = '{}/{}.pkl'.format(DATA_DIR, name)
    print('reading "{}"'.format(file)) if LOG_LEVEL > 1 else None
    return pd.read_pickle('{}/{}.pkl'.format(DATA_DIR, name))


def save_pkl(thing, name):
    file = '{}/{}.pkl'.format(DATA_DIR, name)
    pd.to_pickle(thing, file)
    print('saved "{}"'.format(file)) if LOG_LEVEL > 0 else None


def preprocess_raw_df(df):
    df = df.dropna()
    df = df[~(df['Admin2'] == 'Unassigned')]
    df = df[~(df['Admin2'].str.contains('Out of'))]
    df['Combined_Key'] = df['Combined_Key'].apply(lambda x: x.replace(', US', ''))

    # Convert fips to string and front fill zeros to get to 5 characters
    df['FIPS'] = df['FIPS'].apply(lambda n: str.zfill(str(int(n)), 5))
    return df


def get_and_save_data():
    print('Loading "{}"'.format(CASES_FILE)) if LOG_LEVEL > 0 else None
    cases_df = pd.read_csv(CASES_FILE)
    cases_df = preprocess_raw_df(cases_df)
    print('Loading "{}"'.format(DEATHS_FILE)) if LOG_LEVEL > 0 else None
    deaths_df = pd.read_csv(DEATHS_FILE)
    deaths_df = preprocess_raw_df(deaths_df)

    new_cases_df = new_cases(cases_df)

    pop_df = deaths_df[['FIPS', 'Population', 'Combined_Key']].set_index('FIPS')
    fips_pop_dict = pop_df['Population'].to_dict()
    fips_county_dict = pop_df['Combined_Key'].to_dict()

    def per_100k(s):
        return s / fips_pop_dict[s.name] * 100000

    new_cases_rate_df = new_cases_df.apply(per_100k)

    case_ave_df = new_cases_df.rolling(7, ).mean().dropna()
    case_ave_rate_df = case_ave_df.apply(per_100k)

    map_df = pop_df[['Combined_Key']]
    map_df['week_ave'] = case_ave_df.iloc[-1]
    map_df['ave_rate'] = case_ave_rate_df.iloc[-1]
    map_df = map_df.reset_index()

    save_pkl(map_df, 'map_df')
    save_pkl(new_cases_df, 'new_cases_df')
    save_pkl(new_cases_rate_df, 'new_cases_rate_df')
    save_pkl(fips_county_dict, 'fips_county_dict')
    save_pkl(case_ave_df, 'case_ave_df')
    save_pkl(case_ave_rate_df, 'case_ave_rate_df')


def county_series(df, county_key):
    county_s = df[df['Combined_Key'] == county_key]
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in
                      county_s.columns]
    county_s = county_s.iloc[:, date_cols_bool]
    county_s = county_s.T
    county_s.index = pd.to_datetime(county_s.index)
    county_s.columns = ['cases']
    return county_s['cases']


def new_cases(cases_df):
    df = cases_df.set_index('FIPS')
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in
                      df.columns]
    df = df.iloc[:, date_cols_bool].T
    df = df.diff()[1:]
    df = df.clip(lower=0) #FIXME: Remove positive tests from previous day instead?
    df.index = pd.to_datetime(df.index)
    return df


def clean_county_s(county_s):
    if county_s.sum() > 0:
        while county_s[0] == 0.0:
            county_s = county_s[1:]
        #FIXME: Remove positive tests from previous day instead?
        county_s = county_s.clip(lower=0)
        return county_s
    else:
        return None


def county_summary(county_s, county_rate_s):

    def data_for_table(name, ser):
        yest = ser.iloc[-1]
        week = ser.tail(7).sum()
        two_week_ago = ser.tail(14).head(7).sum()
        if two_week_ago > 0:
            week_change = (week / two_week_ago - 1) * 100
        elif (two_week_ago == 0) and (week == 0):
            week_change = 0
        else:
            week_change = 100
        week_change = int(round(week_change))
        if week_change >= 0:
            week_change = '+{}%'.format(week_change)
        else:
            week_change = '{}%'.format(week_change)
        return name, yest, week, two_week_ago, week_change

    cases = data_for_table('Positive Tests', county_s)
    case_rate = data_for_table('Per 100k', county_rate_s)

    summary_df = pd.DataFrame(data=[cases, case_rate],
                              columns=['', 'Yesterday', 'Past Week',
                                       'Two Weeks Ago', 'Weekly Change'])
    return summary_df


if __name__ == '__main__':
    print()


## Ideas
# https://www.larimer.org/health/communicable-disease/coronavirus-covid-19/larimer-county-positive-covid-19-numbers
# https://www.digitalocean.com/community/pages/hub-for-good
# https://covid19-dash.herokuapp.com/
# https://covid19mtl.ca/en
# https://covid19-dashboard-online.herokuapp.com/
# https://experience.arcgis.com/experience/a6f23959a8b14bfa989e3cda29297ded
# https://www.esri.com/en-us/covid-19/overview#image3
# https://graphics.reuters.com/HEALTH-CORONAVIRUS/USA-TRENDS/dgkvlgkrkpb/index.html
# https://covidtracking.com/data#chart-annotations

## Cloud
# https://console.cloud.google.com/freetrial/signup/tos?_ga=2.216095126.1215990170.1594321151-1114669994.1594321151&pli=1
