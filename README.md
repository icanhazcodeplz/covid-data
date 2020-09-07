# covid-data

COVID-19 Hot-Spot Dashboard that shows the areas in the US that have the highest 
per capita cases. This project is built using [Plotly Dash](https://plotly.com/dash/) with data from 
[Johns Hopkins University](https://github.com/CSSEGISandData/COVID-19). 
The inspiration for the map is from the [NYTimes](https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html).

The dashboard is currently hosted on Google Cloud Platform, and is available at [www.covid19dashboard.app]().

## Running Locally
#### Setup
1. Clone this repo locally.
1. Create a free [mapbox](https://www.mapbox.com/) account.
1. Copy your *"Default public token"* from your [mapbox account](https://account.mapbox.com/) and save it as a text file called *".mapbox_token"* in this project's directory.
1. Create a local python3.7 environment and install all packages in *"requirements_local_only.txt"*.

#### Running
1. Make sure that the variable `LOCAL_DATA` is set to `True` in the file *"constants.py"*.
1. From this directory, run `python3 data_handling.py`
1. Run `python3 main.py`


## Contributing
Contributions are welcome, especially bug reports! Please feel free to submit a pull request or bug report :).  