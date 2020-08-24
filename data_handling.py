import pandas as pd
import numpy as np
import re
from google.cloud import storage
import pickle
from io import BytesIO, StringIO
from datetime import datetime
import json

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
        """Uploads a file blob to the bucket."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_file(file)
        print("{} uploaded to {}".format(destination_blob_name, BUCKET)) if LOG_LEVEL > 0 else None

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
        print('reading "{}"'.format(file)) if LOG_LEVEL > 0 else None
        return pd.read_pickle(file)

    def _save_local_pkl(self, thing, name):
        file = self._local_pkl_path(name)
        pd.to_pickle(thing, file)
        print('saved "{}" locally'.format(file)) if LOG_LEVEL > 0 else None

    @staticmethod
    def load_pkl_file(file_prefix):
        if USE_LOCAL_DIR:
            return DataHandler()._read_local_pkl(file_prefix)
        else:
            return DataHandler()._download_pkl_blob_as_df(file_prefix)

    @staticmethod
    def save_pkl_file(obj, file_prefix):
        if USE_LOCAL_DIR:
            return DataHandler()._save_local_pkl(obj, file_prefix)
        else:
            return DataHandler()._upload_df_as_pkl_blob(obj, file_prefix)

    @staticmethod
    def load_states_csv():
        return pd.read_csv('{}/states.csv'.format(DATA_DIR),
                           index_col=0,
                           dtype=dict(fips=str))

    @staticmethod
    def load_counties_geo():
        with open('{}/geojson-counties-fips.json'.format(DATA_DIR)) as f:
            counties_geo = json.load(f)
        return counties_geo


def load_raw_covid_file(file):
    print('Loading "{}"'.format(file)) if LOG_LEVEL > 0 else None
    df = pd.read_csv(file)
    df = df.drop(
        ['iso2', 'iso3', 'code3', 'Country_Region',
         'Lat', 'Long_', 'Combined_Key'], axis='columns')
    df = df.rename(
        {'Admin2': 'county', 'Province_State': 'state', 'Population': 'pop',
         'FIPS': 'fips', 'UID': 'uid'},
        axis='columns')

    def convert_fips_to_str(f):
        # Convert fips to string and front fill zeros to get to 5 characters
        try:
            return str.zfill(str(int(f)), 5)
        except ValueError:
            return np.nan

    df['fips'] = df['fips'].apply(convert_fips_to_str)
    return df


def get_and_save_data(_):
    tot_deaths_df = load_raw_covid_file(DEATHS_FILE)
    tot_cases_df = load_raw_covid_file(CASES_FILE)
    uid_pop = tot_deaths_df[['uid', 'pop']].set_index('uid', drop=True)
    tot_cases_df = tot_cases_df.join(uid_pop, on='uid')

    state_cases_df = tot_cases_df.drop(
        ['uid', 'fips', 'county'], axis='columns')
    state_cases_df = state_cases_df.groupby(['state']).sum()
    state_cases_df = state_cases_df.drop(
        ['Diamond Princess', 'Guam', 'American Samoa', 'Grand Princess',
         'Northern Mariana Islands', 'Virgin Islands'], axis='rows')
    state_cases_df.loc['USA'] = state_cases_df.sum()

    def new_cases(df):
        date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in df.columns]
        df = df.iloc[:, date_cols_bool].T
        df = df.diff()[1:]
        df = df.clip(lower=0) #FIXME: Remove positive tests from previous day instead?
        df.index = pd.to_datetime(df.index)

        # Only show data from March 1st on
        return df.iloc[38:]

    state_map_df = state_cases_df['pop'].to_frame('pop')
    state_cases_df = state_cases_df.drop('pop', axis='columns')
    state_df = new_cases(state_cases_df)

    county_df = tot_cases_df.dropna().set_index('fips', drop=True)
    county_df = county_df[~(county_df['county'] == 'Unassigned')]
    county_df = county_df[~(county_df['county'].str.contains('Out of'))]
    county_df = new_cases(county_df)

    def make_map_df(df, map_df):
        loc_pop_dict = map_df['pop'].to_dict()
        ave_df = df.rolling(7, ).mean().dropna()
        ave_rate_df = ave_df.apply(lambda s: s / loc_pop_dict[s.name] * 100000)
        map_df['week_ave'] = ave_df.iloc[-1]
        map_df['ave_rate'] = ave_rate_df.iloc[-1]
        return map_df.reset_index()

    county_map_df = tot_deaths_df[['pop', 'county', 'state', 'fips']]
    county_map_df = county_map_df.set_index('fips', drop=True)

    county_map_df = make_map_df(county_df, county_map_df)
    state_map_df = make_map_df(state_df, state_map_df)

    def custom_number_str(num, max_val_for_decimals=10):
        if num > max_val_for_decimals:
            return str(int(round(num, 0)))
        else:
            return str(round(num, 1))

    county_map_df['text'] = [
        '<b>{} County, {}</b><br>Avg. Daily Cases: {}<br>             Per 100k: {}'.format(
            tup.county,
            tup.state,
            custom_number_str(tup.week_ave),
            custom_number_str(tup.ave_rate)
        ) for tup in county_map_df.itertuples()]

    state_map_df['text'] = [
        '<b>{}</b><br>Avg. Daily Cases: {}<br>             Per 100k: {}'.format(
            tup.state,
            custom_number_str(tup.week_ave),
            custom_number_str(tup.ave_rate)
        ) for tup in state_map_df.itertuples()]

    DataHandler.save_pkl_file(county_df, 'county_df')
    DataHandler.save_pkl_file(county_map_df, 'county_map_df')

    DataHandler.save_pkl_file(state_df, 'state_df')
    DataHandler.save_pkl_file(state_map_df, 'state_map_df')
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


def cases_data_for_graph(cases_s, pop):
    if cases_s.sum() == 0:
        return None

    df = cases_s.to_frame('cases')
    df['cases_rate'] = df['cases'] / pop * 100000

    df['cases_ave'] = df['cases'].rolling(7, ).mean()
    df['cases_ave_rate'] = df['cases_ave'] / pop * 100000
    return df.dropna()


class FreshData:

    def __init__(self):
        self._load_static_data()
        self._load_dynamic_data()

    def _load_dynamic_data(self):
        self._county_map_df = DataHandler.load_pkl_file('county_map_df')
        self._county_df = DataHandler.load_pkl_file('county_df')

        tmp_df = self._county_map_df.set_index('fips', drop=True)
        self.fips_pop_dict = tmp_df['pop'].to_dict()
        self.fips_county_dict = (
                tmp_df.county + ' County, ' + tmp_df.state).to_dict()

        self._state_df = DataHandler.load_pkl_file('state_df')
        self._state_map_df = DataHandler.load_pkl_file('state_map_df')

        self.state_pop_dict = self._state_map_df.set_index('state')['pop'].to_dict()

        self.last_load_time = datetime.now()

    def _load_static_data(self):
        self.states_meta_df = DataHandler.load_states_csv()
        self.state_keys = [dict(value=s, label=s) for s in self.states_meta_df.index]
        self.counties_geo = DataHandler.load_counties_geo()

    def _refresh_if_needed(self):
        stale_secs = (datetime.now() - self.last_load_time).total_seconds()
        stale_hours = stale_secs / 3600
        if stale_hours > ACCEPTABLE_STALE_HOURS:
            print('Refreshing data at {}'.format(datetime.now()))
            self._load_dynamic_data()
            return True
        else:
            return False

    @property
    def county_map_df(self):
        self._refresh_if_needed()
        return self._county_map_df

    @property
    def county_df(self):
        self._refresh_if_needed()
        return self._county_df

    # @property
    # def county_meta_df(self):
    #     self.refresh_if_needed()
    #     return self._county_meta_df

    @property
    def state_df(self):
        self._refresh_if_needed()
        return self._state_df

    @property
    def state_map_df(self):
        self._refresh_if_needed()
        return self._state_map_df


if __name__ == '__main__':
    get_and_save_data('')
    # fd = FreshData()
    #
    # t = fd.county_map_df

    print()

