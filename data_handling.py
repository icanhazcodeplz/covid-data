import pandas as pd
import re
from google.cloud import storage
import pickle
from io import BytesIO, StringIO
from datetime import datetime

from constants import *


class DataHandler:

    def _upload_string_blob(self, string, destination_blob_name):
        """Uploads a string to the bucket."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_string(string)
        print("String uploaded to {}.".format(destination_blob_name))

    def _upload_file_blob(self, file, destination_blob_name):
        """Uploads a string to the bucket."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_file(file)
        print("String uploaded to {}.".format(destination_blob_name))

    def _upload_df_as_csv_blob(self, df, name_prefix):
        csv = StringIO()
        df.to_csv(csv)
        self._upload_string_blob(csv.getvalue(), '{}.csv'.format(name_prefix))

    def _download_csv_blob_as_df(self, name_prefix):
        """Downloads a blob from the bucket."""
        storage_client = storage.Client()

        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob('{}.csv'.format(name_prefix))
        txt = blob.download_as_string()
        return pd.read_csv(BytesIO(txt), index_col=0)

    def _upload_df_as_pkl_blob(self, df, name_prefix):
        self._upload_file_blob(BytesIO(pickle.dumps(df)), '{}.pkl'.format(name_prefix))

    def _download_pkl_blob_as_df(self, name_prefix):
        """Downloads a blob from the bucket."""
        storage_client = storage.Client()

        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob('{}.pkl'.format(name_prefix))
        txt = blob.download_as_string()
        return pd.read_pickle(BytesIO(txt))

    def _local_pkl_path(self, name):
        return '{}/{}.pkl'.format(DATA_DIR, name)

    def _read_local_pkl(self, name):
        file = self._local_pkl_path(name)
        print('reading "{}"'.format(file))
        return pd.read_pickle(file)

    def _save_local_pkl(self, thing, name):
        file = self._local_pkl_path(name)
        pd.to_pickle(thing, file)
        print('saved "{}"'.format(file))

    def load_pkl_file(self, file_prefix):
        #TODO: Make this class or static method?
        if USE_LOCAL_DIR:
            return self._read_local_pkl(file_prefix)
        else:
            return self._download_pkl_blob_as_df(file_prefix)

    def save_pkl_file(self, obj, file_prefix):
        if USE_LOCAL_DIR:
            return self._save_local_pkl(obj, file_prefix)
        else:
            return self._upload_df_as_pkl_blob(obj, file_prefix)


def preprocess_raw_df(df):
    df = df.dropna()
    df = df[~(df['Admin2'] == 'Unassigned')]
    df = df[~(df['Admin2'].str.contains('Out of'))]
    df['Combined_Key'] = df['Combined_Key'].apply(lambda x: x.replace(', US', ''))

    # Convert fips to string and front fill zeros to get to 5 characters
    df['FIPS'] = df['FIPS'].apply(lambda n: str.zfill(str(int(n)), 5))
    return df


def new_cases(cases_df):
    df = cases_df.set_index('FIPS')
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in df.columns]
    df = df.iloc[:, date_cols_bool].T
    df = df.diff()[1:]
    df = df.clip(lower=0) #FIXME: Remove positive tests from previous day instead?
    df.index = pd.to_datetime(df.index)
    return df


def get_and_save_data(_):
    print('Loading "{}"'.format(CASES_FILE))
    tot_cases_df = pd.read_csv(CASES_FILE)
    tot_cases_df = preprocess_raw_df(tot_cases_df)
    print('Loading "{}"'.format(DEATHS_FILE))
    tot_deaths_df = pd.read_csv(DEATHS_FILE)
    tot_deaths_df = preprocess_raw_df(tot_deaths_df)

    cases_df = new_cases(tot_cases_df)

    pop_df = tot_deaths_df[['FIPS', 'Population', 'Admin2', 'Province_State']].set_index('FIPS')
    pop_df = pop_df.rename({'Admin2': 'County', 'Province_State': 'State'}, axis='columns')
    fips_pop_dict = pop_df['Population'].to_dict()

    def per_100k(s):
        return s / fips_pop_dict[s.name] * 100000

    cases_ave_df = cases_df.rolling(7, ).mean().dropna()
    cases_ave_rate_df = cases_ave_df.apply(per_100k)

    map_df = pop_df[['County', 'State']]
    map_df['week_ave'] = cases_ave_df.iloc[-1]
    map_df['ave_rate'] = cases_ave_rate_df.iloc[-1]
    map_df = map_df.reset_index()

    DataHandler().save_pkl_file(map_df, 'map_df')
    DataHandler().save_pkl_file(cases_df, 'cases_df')
    DataHandler().save_pkl_file(pop_df, 'pop_df')
    return f'Completed'


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


def load_states_csv():
    return pd.read_csv('{}/states.csv'.format(DATA_DIR), index_col=0)


class FreshData:

    def __init__(self):
        self.map_df = DataHandler().load_pkl_file('map_df')
        self.cases_df = DataHandler().load_pkl_file('cases_df')
        self.pop_df = DataHandler().load_pkl_file('pop_df')
        self.fips_pop_dict = self.pop_df['Population'].to_dict()

        tmp = self.pop_df
        tmp = tmp.County + ' County, ' + tmp.State
        self.fips_county_dict = tmp.to_dict()

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
    # load_states_csv()
    # get_and_save_data('')
    # fd = FreshData()
    # fips = '36047'
    print()