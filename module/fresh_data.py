from datetime import datetime

from constants import *
from module.data_handling import DataHandler


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

