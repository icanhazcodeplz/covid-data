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
        """Uploads a file blob to the bucket."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_file(file)
        print("String uploaded to {}".format(destination_blob_name)) if LOG_LEVEL > 0 else None

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
        print('saved "{}"'.format(file)) if LOG_LEVEL > 0 else None

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


def process_for_county_level(df):
    df = df.dropna()
    df = df[~(df['Admin2'] == 'Unassigned')]
    df = df[~(df['Admin2'].str.contains('Out of'))]

    # Convert fips to string and front fill zeros to get to 5 characters
    df['FIPS'] = df['FIPS'].apply(lambda n: str.zfill(str(int(n)), 5))
    df = df.set_index('FIPS')
    return df


def new_cases(df):
    date_cols_bool = [bool(re.match('\d*/\d*/\d\d', c)) for c in df.columns]
    df = df.iloc[:, date_cols_bool].T
    df = df.diff()[1:]
    df = df.clip(lower=0) #FIXME: Remove positive tests from previous day instead?
    df.index = pd.to_datetime(df.index)

    # Only show data from March 1st on
    df = df.iloc[38:]
    return df


def get_and_save_data(_):
    print('Loading "{}"'.format(CASES_FILE)) if LOG_LEVEL > 0 else None
    tot_cases_df = pd.read_csv(CASES_FILE)
    print('Loading "{}"'.format(DEATHS_FILE)) if LOG_LEVEL > 0 else None
    tot_deaths_df = pd.read_csv(DEATHS_FILE)

    # FIXME: This is some ugly code. Clean it up!!!
    uid_pop = tot_deaths_df[['UID', 'Population']].set_index('UID',drop=True)
    state_cases_df = tot_cases_df.join(uid_pop, on='UID')
    state_cases_df = state_cases_df.drop(['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Admin2', 'Country_Region', 'Lat', 'Long_', 'Combined_Key'], axis='columns')
    state_cases_df = state_cases_df.rename({'Province_State': 'state'}, axis='columns')
    state_cases_df = state_cases_df.groupby(['state']).sum()
    state_cases_df = state_cases_df.drop(
        ['Diamond Princess', 'Guam', 'American Samoa', 'Grand Princess',
         'Northern Mariana Islands', 'Virgin Islands'], axis='rows')
    state_cases_df.loc['USA'] = state_cases_df.sum()
    state_map_df = state_cases_df['Population'].to_frame('pop')
    state_pop_dict = state_cases_df['Population'].to_dict()
    state_cases_df = state_cases_df.drop('Population', axis='columns')
    state_df = new_cases(state_cases_df)

    tot_cases_df = process_for_county_level(tot_cases_df)
    tot_deaths_df = process_for_county_level(tot_deaths_df)

    county_df = new_cases(tot_cases_df)

    county_meta_df = tot_deaths_df[['Population', 'Admin2', 'Province_State']]
    county_meta_df = county_meta_df.rename({'Admin2': 'county', 'Province_State': 'state',
                            'Population': 'pop'}, axis='columns')

    fips_pop_dict = county_meta_df['pop'].to_dict()
    # def per_100k(s):
    #     return s / fips_pop_dict[s.name] * 100000

    def make_map_df(df, map_df, loc_pop_dict):
        ave_df = df.rolling(7, ).mean().dropna()
        ave_rate_df = ave_df.apply(lambda s: s / loc_pop_dict[s.name] * 100000)
        map_df['week_ave'] = ave_df.iloc[-1]
        map_df['ave_rate'] = ave_rate_df.iloc[-1]
        return map_df.reset_index()

    county_map_df = county_meta_df[['county', 'state']]
    county_map_df = make_map_df(county_df, county_map_df, fips_pop_dict)

    state_map_df = make_map_df(state_df, state_map_df, state_pop_dict)

    county_map_df['text'] = [
        '<b>{} County, {}</b><br>Avg. Daily Cases: {:.1f}<br>             Per 100k: {:.1f}'.format(
        tup.county, tup.state, tup.week_ave, tup.ave_rate) for tup in county_map_df.itertuples()]

    state_map_df['text'] = [
        '<b>{}</b><br>Avg. Daily Cases: {:.1f}<br>             Per 100k: {:.1f}'.format(
        tup.state, tup.week_ave, tup.ave_rate) for tup in state_map_df.itertuples()]

    DataHandler().save_pkl_file(county_map_df, 'county_map_df')
    DataHandler().save_pkl_file(county_df, 'county_df')
    DataHandler().save_pkl_file(county_meta_df, 'county_meta_df')

    DataHandler().save_pkl_file(state_pop_dict, 'state_pop_dict')
    DataHandler().save_pkl_file(state_df, 'state_df')
    DataHandler().save_pkl_file(state_map_df, 'state_map_df')
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


def cases_data_for_graph(cases, pop):
    if cases.sum() == 0:
        return None

    df = cases.to_frame('cases')
    df['cases_rate'] = df['cases'] / pop * 100000

    df['cases_ave'] = df['cases'].rolling(7, ).mean()
    df['cases_ave_rate'] = df['cases_ave'] / pop * 100000
    return df.dropna()


def load_states_csv():
    return pd.read_csv('{}/states.csv'.format(DATA_DIR),
                       index_col=0,
                       dtype=dict(fips=str))


class FreshData:

    def __init__(self):
        self.county_map_df = DataHandler().load_pkl_file('county_map_df')
        self.county_df = DataHandler().load_pkl_file('county_df')
        self.county_meta_df = DataHandler().load_pkl_file('county_meta_df')

        self.state_pop_dict = DataHandler().load_pkl_file('state_pop_dict')
        self.state_df = DataHandler().load_pkl_file('state_df')
        self.state_map_df = DataHandler().load_pkl_file('state_map_df')

        tmp = self.county_meta_df.county + ' County, ' + self.county_meta_df.state
        self.fips_county_dict = tmp.to_dict()
        self.fips_pop_dict = self.county_meta_df['pop'].to_dict()

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
    df = load_states_csv()
    d = FreshData().fips_county_dict
    new = {}
    for k, v in d.items():
        new[v.split(', ')[1]] = k[:2]
        print()
    print()
    # get_and_save_data('')

    print()
    print()


# def clean_county_s(county_s):
#     if county_s.sum() > 0:
#         while county_s[0] == 0.0:
#             county_s = county_s[1:]
#         #FIXME: Remove positive tests from previous day instead?
#         county_s = county_s.clip(lower=0)
#         return county_s
#     else:
#         return None

#
# def county_summary(county_s, county_rate_s):
#
#     yest = county_s.iloc[-1]
#     week = county_s.tail(7).sum()
#     two_week_ago = county_s.tail(14).head(7).sum()
#     if two_week_ago > 0:
#         week_change = (week / two_week_ago - 1) * 100
#     elif (two_week_ago == 0) and (week == 0):
#         week_change = 0
#     else:
#         week_change = 100
#
#
#     # week_change = int(round(week_change))
#     # if week_change >= 0:
#     #     week_change = '+{}%'.format(week_change)
#     # else:
#     #     week_change = '{}%'.format(week_change)
#
#     if week < 10:
#         trend = 'N/A'
#     elif week_change < -20:
#         trend = 'Falling Quickly'
#     elif week_change < -2:
#         trend = 'Falling Slowly'
#     elif week_change > 20:
#         trend = 'Rising Quickly'
#     elif week_change > 2:
#         trend = 'Rising Slowly'
#     else:
#         trend = 'No Change'
#
#     # summary_df = pd.DataFrame(data=[cases, case_rate],
#     #                           columns=['', 'Yesterday', 'Past Week'])
#     # return summary_df, trend
#
