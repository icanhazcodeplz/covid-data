import pandas as pd
import re


def preprocess_raw_df(df):
    df = df.dropna()
    df = df[~(df['Admin2'] == 'Unassigned')]
    df = df[~(df['Admin2'].str.contains('Out of'))]
    df['Combined_Key'] = df['Combined_Key'].apply(lambda x: x.replace(', US', ''))

    # Convert fips to string and front fill zeros to get to 5 characters
    df['FIPS'] = df['FIPS'].apply(lambda n: str.zfill(str(int(n)), 5))
    return df


def county_series(df, county_key):
    county_s = df[df['Combined_Key'] == county_key]
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in
                      county_s.columns]
    county_s = county_s.iloc[:, date_cols_bool]
    county_s = county_s.T
    county_s.index = pd.to_datetime(county_s.index)
    county_s.columns = ['cases']
    return county_s['cases']


def county_data(cases_df, county_key):
    county_cases = county_series(cases_df, county_key).diff()[1:]

    if county_cases.sum() > 0:
        while county_cases[0] == 0.0:
            county_cases = county_cases[1:]
        #FIXME: Remove positive tests from previous day instead?
        county_cases = county_cases.clip(lower=0)
        return county_cases
    else:
        return None


def county_summary(county_s):

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

    summary_df = pd.DataFrame(data=[cases],
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
