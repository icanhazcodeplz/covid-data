import pandas as pd
from datetime import datetime, timedelta
import re
import os

from google.cloud import storage
import pickle
from io import BytesIO
from io import StringIO
import sys

from __init__ import *
from data_handling.main import *


def county_series(df, county_key):
    county_s = df[df['Combined_Key'] == county_key]
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in
                      county_s.columns]
    county_s = county_s.iloc[:, date_cols_bool]
    county_s = county_s.T
    county_s.index = pd.to_datetime(county_s.index)
    county_s.columns = ['cases']
    return county_s['cases']


def clean_county_s(county_s):
    if county_s.sum() > 0:
        while county_s[0] == 0.0:
            county_s = county_s[1:]
        #FIXME: Remove positive tests from previous day instead?
        county_s = county_s.clip(lower=0)
        return county_s
    else:
        return None


def county_data(cases, pop):
    if cases.sum() == 0:
        return None

    df = cases.to_frame('cases')
    df['cases_rate'] = df['cases'] / pop * 100000

    df['cases_ave'] = df['cases'].rolling(7, ).mean()
    df['cases_ave_rate'] = df['cases_ave'] / pop * 100000
    return df.dropna()


def county_summary(county_s, county_rate_s):

    yest = county_s.iloc[-1]
    week = county_s.tail(7).sum()
    two_week_ago = county_s.tail(14).head(7).sum()
    if two_week_ago > 0:
        week_change = (week / two_week_ago - 1) * 100
    elif (two_week_ago == 0) and (week == 0):
        week_change = 0
    else:
        week_change = 100


    # week_change = int(round(week_change))
    # if week_change >= 0:
    #     week_change = '+{}%'.format(week_change)
    # else:
    #     week_change = '{}%'.format(week_change)

    if week < 10:
        trend = 'N/A'
    elif week_change < -20:
        trend = 'Falling Quickly'
    elif week_change < -2:
        trend = 'Falling Slowly'
    elif week_change > 20:
        trend = 'Rising Quickly'
    elif week_change > 2:
        trend = 'Rising Slowly'
    else:
        trend = 'No Change'

    # summary_df = pd.DataFrame(data=[cases, case_rate],
    #                           columns=['', 'Yesterday', 'Past Week'])
    # return summary_df, trend


class FreshData:

    def __init__(self):
        self.map_df = DataHandler().load_pkl_file('map_df')
        self.cases_df = DataHandler().load_pkl_file('cases_df')
        self.pop_df = DataHandler().load_pkl_file('pop_df')
        self.fips_pop_dict = self.pop_df['Population'].to_dict()
        self.fips_county_dict = self.pop_df['Combined_Key'].to_dict()

        self.last_refresh_time = datetime.now()

    def refresh_if_needed(self):
        stale_secs = (datetime.now() - self.last_refresh_time).total_seconds()
        stale_hours = stale_secs / 3600
        if stale_hours > ACCEPTABLE_STALE_HOURS:
            print('Refreshing data at {}'.format(datetime.now()))
            self.__init__()
            return True
        else:
            return False



if __name__ == '__main__':
    fd = FreshData()
    # get_and_save_data(upload_pkl_to_gcloud=True)

    # cases_df = download_csv_blob_as_df('cases_df')
    # cases_df = read_pkl('cases_df')
    # upload_df_as_pkl_blob(cases_df, 'cases_df')
    # df = download_csv_blob_as_df('cases_df.csv')
    print('done')
    # df2 = read_pkl('cases_df')
    # buff = BytesIO()

    # get_and_save_data()
    # last_update()
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
