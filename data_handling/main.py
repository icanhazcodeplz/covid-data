import pandas as pd
import re
from google.cloud import storage
import pickle
from io import BytesIO, StringIO


CASES_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
DEATHS_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'
BUCKET = 'covid-283120.appspot.com'
USE_LOCAL_DIR = False
DATA_DIR = 'processed_data'



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

    pop_df = tot_deaths_df[['FIPS', 'Population', 'Combined_Key']].set_index('FIPS')
    fips_pop_dict = pop_df['Population'].to_dict()

    def per_100k(s):
        return s / fips_pop_dict[s.name] * 100000

    cases_ave_df = cases_df.rolling(7, ).mean().dropna()
    cases_ave_rate_df = cases_ave_df.apply(per_100k)

    map_df = pop_df[['Combined_Key']]
    map_df['week_ave'] = cases_ave_df.iloc[-1]
    map_df['ave_rate'] = cases_ave_rate_df.iloc[-1]
    map_df = map_df.reset_index()

    DataHandler().save_pkl_file(map_df, 'map_df')
    DataHandler().save_pkl_file(cases_df, 'cases_df')
    DataHandler().save_pkl_file(pop_df, 'pop_df')
    return f'Completed'
