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
    """Load and save data from either google cloud bucket or .../covid-data/data

    If `LOCAL_DATA` in the file "constants.py" is set to `True`, save and load
    data to .../covid-data/data

    If `LOCAL_DATA` is set to `False`, save and load data to google cloud
    storage in the bucket `BUCKET`, which is defined in "constants.py"

    This is in a class purely for orginizational purposes
    """

    @staticmethod
    def _upload_string_blob(string, destination_blob_name):
        """Uploads a string to the bucket."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_string(string)
        print("String uploaded to {}.".format(destination_blob_name))

    @staticmethod
    def _upload_file_blob(file, destination_blob_name):
        """Uploads a file blob to the bucket."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_file(file)
        print("{} uploaded to {}".format(destination_blob_name, BUCKET)) if LOG_LEVEL > 0 else None

    @staticmethod
    def _upload_df_as_csv_blob(df, name_prefix):
        csv = StringIO()
        df.to_csv(csv)
        DataHandler._upload_string_blob(csv.getvalue(), '{}.csv'.format(name_prefix))

    @staticmethod
    def _download_csv_blob_as_df(name_prefix):
        """Downloads a blob from the bucket."""
        storage_client = storage.Client()

        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob('{}.csv'.format(name_prefix))
        txt = blob.download_as_string()
        return pd.read_csv(BytesIO(txt), index_col=0)

    @staticmethod
    def _upload_df_as_pkl_blob(df, name_prefix):
        DataHandler._upload_file_blob(BytesIO(pickle.dumps(df)), '{}.pkl'.format(name_prefix))

    @staticmethod
    def _download_pkl_blob_as_df(name_prefix):
        """Downloads a blob from the bucket."""
        storage_client = storage.Client()

        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob('{}.pkl'.format(name_prefix))
        txt = blob.download_as_string()
        return pd.read_pickle(BytesIO(txt))

    @staticmethod
    def _local_pkl_path(name):
        return 'data/{}.pkl'.format(name)

    @staticmethod
    def _read_local_pkl(name):
        file = DataHandler._local_pkl_path(name)
        print('reading "{}"'.format(file)) if LOG_LEVEL > 0 else None
        return pd.read_pickle(file)

    @staticmethod
    def _save_local_pkl(thing, name):
        file = DataHandler._local_pkl_path(name)
        pd.to_pickle(thing, file)
        print('saved "{}" locally'.format(file)) if LOG_LEVEL > 0 else None

    @staticmethod
    def load_pkl_file(file_prefix):
        if LOCAL_DATA:
            return DataHandler()._read_local_pkl(file_prefix)
        else:
            return DataHandler()._download_pkl_blob_as_df(file_prefix)

    @staticmethod
    def save_pkl_file(obj, file_prefix):
        if LOCAL_DATA:
            return DataHandler()._save_local_pkl(obj, file_prefix)
        else:
            return DataHandler()._upload_df_as_pkl_blob(obj, file_prefix)

    @staticmethod
    def load_states_csv():
        return pd.read_csv('data/states.csv',
                           index_col=0,
                           dtype=dict(fips=str))

    @staticmethod
    def load_counties_geo():
        with open('data/geojson-counties-fips.json') as f:
            counties_geo = json.load(f)
        return counties_geo


def load_raw_covid_file(file):
    """Read the John Hopkins csv files, do some preprocessing, and return a df

    Args:
        file (str): URL of the file

    Returns:
        :pandas.DataFrame

    """
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


def get_and_save_data(_=None):
    """Download data from John Hopkins, do some processing, and save as pickles

    Args:
        _: Empty variable. Was needed for the Google Cloud Function to work

    """
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

        # Only keep data from Feb 24 on
        slice_i = datetime(year=2020, month=2, day=24)
        return df[slice_i:]

    states_map_df = state_cases_df['pop'].to_frame('pop')
    state_cases_df = state_cases_df.drop('pop', axis='columns')
    states_df = new_cases(state_cases_df)

    counties_df = tot_cases_df.dropna().set_index('fips', drop=True)
    counties_df = counties_df[~(counties_df['county'] == 'Unassigned')]
    counties_df = counties_df[~(counties_df['county'].str.contains('Out of'))]
    counties_df = new_cases(counties_df)

    def make_map_df(df, map_df):
        loc_pop_dict = map_df['pop'].to_dict()
        ave_df = df.rolling(7, ).mean().dropna()
        ave_rate_df = ave_df.apply(lambda s: s / loc_pop_dict[s.name] * 100000)
        map_df['week_ave'] = ave_df.iloc[-1]
        map_df['ave_rate'] = ave_rate_df.iloc[-1]
        return map_df.reset_index()

    counties_map_df = tot_deaths_df[['pop', 'county', 'state', 'fips']]
    counties_map_df = counties_map_df.set_index('fips', drop=True)

    counties_map_df = make_map_df(counties_df, counties_map_df)
    states_map_df = make_map_df(states_df, states_map_df)

    def custom_number_str(num, max_val_for_decimals=10):
        if num > max_val_for_decimals:
            return str(int(round(num, 0)))
        else:
            return str(round(num, 1))

    counties_map_df['text'] = [
        '<b>{} County, {}</b><br>Avg. Daily Cases: {}<br>             Per 100k: {}'.format(
            tup.county,
            tup.state,
            custom_number_str(tup.week_ave),
            custom_number_str(tup.ave_rate)
        ) for tup in counties_map_df.itertuples()]

    states_map_df['text'] = [
        '<b>{}</b><br>Avg. Daily Cases: {}<br>             Per 100k: {}'.format(
            tup.state,
            custom_number_str(tup.week_ave),
            custom_number_str(tup.ave_rate)
        ) for tup in states_map_df.itertuples()]

    DataHandler.save_pkl_file(counties_df, 'counties_df')
    DataHandler.save_pkl_file(counties_map_df, 'counties_map_df')

    DataHandler.save_pkl_file(states_df, 'states_df')
    DataHandler.save_pkl_file(states_map_df, 'states_map_df')
    return f'Completed'


class FreshData:
    """Single class to access all the data needed in this app.

    John Hopkins updates their data once a day. I am using a Google Cloud
    Function to pull the data and create four files (see the function
    `get_and_save_data`) that are then saved to a bucket in Google Cloud
    Storage. This app is hosted using Google App Engine. It is served using
    Gunicorn. Because Gunicorn keeps global variables in memory, I needed a way
     to force some variables to update when there is fresh data avaible in
    Cloud Storage. This class does that by checking the `last_refresh_date`
    before returning the attributes, and pulls fresh data from the bucket if needed.

    """

    def __init__(self):
        self.states_meta_df = DataHandler.load_states_csv()
        self.counties_geo = DataHandler.load_counties_geo()

        self._load_dynamic_data()

    def _load_dynamic_data(self):
        self._counties_map_df = DataHandler.load_pkl_file('counties_map_df')
        self._counties_df = DataHandler.load_pkl_file('counties_df')

        tmp_df = self._counties_map_df.set_index('fips', drop=True)
        self.fips_pop_dict = tmp_df['pop'].to_dict()
        self.fips_county_dict = (
                tmp_df.county + ' County, ' + tmp_df.state).to_dict()

        self._states_df = DataHandler.load_pkl_file('states_df')
        self._states_map_df = DataHandler.load_pkl_file('states_map_df')
        self._states_map_df = self._states_map_df.set_index('state', drop=True)
        self._states_map_df = self._states_map_df.join(self.states_meta_df['abbr'])

        self.state_pop_dict = self._states_map_df['pop'].to_dict()
        self.last_load_time = datetime.now()

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
    def counties_map_df(self):
        """DataFrame used to generate a county level map

        Returns:
            :pandas.DataFrame

        """
        self._refresh_if_needed()
        return self._counties_map_df

    @property
    def counties_df(self):
        """DataFrame used to create timeseries graphs of cases

        Returns:
            :pandas.DataFrame

        """
        self._refresh_if_needed()
        return self._counties_df

    @property
    def states_df(self):
        """DataFrame used to create timeseries graphs for states

        Returns:
            :pandas.DataFrame

        """
        self._refresh_if_needed()
        return self._states_df

    @property
    def states_map_df(self):
        """DataFrame used to create a map of states

        Returns:
            :pandas.DataFrame

        """
        self._refresh_if_needed()
        return self._states_map_df


if __name__ == '__main__':
    get_and_save_data()

