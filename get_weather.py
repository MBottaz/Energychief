import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

def get_hist_weather (latitude, longitude, start_date, end_date) -> pd.DataFrame:
    # Function to get historical weather data from Open-Meteo API for given coordinates and date range
    # Parameters:
    #   latitude (float): Latitude of the location
    #   longitude (float): Longitude of the location
    #   start_date (str): Start date in 'YYYY-MM-DD' format
    #   end_date (str): End date in 'YYYY-MM-DD' format, for historical, the end date should be 5 days before today at max
    # Returns: pd.DataFrame containing hourly weather data

    # The following code is copy-pasted from the Open-Meteo Requests documentation
    # https://open-meteo.com/en/docs

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "global_tilted_irradiance"],
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_global_tilted_irradiance = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}

    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["global_tilted_irradiance"] = hourly_global_tilted_irradiance

    hourly_dataframe = pd.DataFrame(data = hourly_data)

    return hourly_dataframe