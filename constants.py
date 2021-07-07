LOG_LEVEL = 1  # There is currently only 1 logging level, could add more later though
ACCEPTABLE_STALE_HOURS = 1  # How frequently the site will refresh it's own data

# Download the John Hopkins data directly from github
CASES_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
DEATHS_FILE = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'

BUCKET = 'covid-283120.appspot.com'  # Only used when deployed to google cloud
LOCAL_DATA = True  # Set to "False" before deploying
