import pandas as pd

from dataprep import load_csv
# from EnergyML import create_features
from get_weather import get_hist_weather


def calc_consumption(latitude, longitude):

    # -------INPUT---------
    consumption_df = load_csv('data', edistribuzione_format=True)

    
    # ensure datetime column is parsed and used as index for resampling
    consumption_df['datetime'] = pd.to_datetime(consumption_df['datetime'])
    consumption_df = consumption_df.set_index('datetime').resample('h').sum().reset_index()

    # make datetimes timezone-aware (UTC) so they match weather timestamps
    consumption_df['datetime'] = consumption_df['datetime'].dt.tz_localize('UTC')

    start_date = consumption_df['datetime'].min().strftime('%Y-%m-%d')
    end_date = consumption_df['datetime'].max().strftime('%Y-%m-%d')

    weather_data = get_hist_weather(latitude, longitude, start_date, end_date)

    weather_data['date'] = pd.to_datetime(weather_data['date'])

    weather_data['date'] = pd.to_datetime(weather_data['date'])

    df = weather_data.set_index('date').join(
        consumption_df.set_index('datetime'),
        how='inner'
    ).reset_index()

    return df

    """
    # Merge consumption and weather data
    df = weather_data.set_index('date').join(
        consumption_df.set_index('datetime'),
        how='inner'
    ).reset_index() """
    


def main():    

    # Input
    latitude = 41.89
    longitude = 12.51

    df =calc_consumption(latitude, longitude)

    print(df.head)
    print(df.tail)





if __name__ == "__main__":
    main()
