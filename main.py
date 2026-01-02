import pandas as pd

from dataprep import load_csv
from EnergyML import train_consumption_model, create_consumption_features
from get_weather import get_hist_weather


def get_consumption(latitude, longitude):
    """
    get_consumption(latitude, longitude) -> pandas.DataFrame

    Inputs:
    - latitude (float): latitude in decimal degrees
    - longitude (float): longitude in decimal degrees

    Output:
    - pandas.DataFrame: hourly, timezone-aware (UTC) DataFrame joining
        historical weather data with electricity consumption.

    Description:
    Loads consumption CSVs, resamples to hourly sums, fetches historical
    weather for the date range, and returns a joined DataFrame.
    """

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

    df['date'] = pd.to_datetime(df['date'])

    return df





def main():    

    # Input
    latitude = 41.89
    longitude = 12.51

    df =get_consumption(latitude, longitude)

    results = train_consumption_model(
        df=df,
        feature_function=create_consumption_features,
        n_splits=5,
        save_path='consumption_model.pkl'
    )
    
    # Access trained model and metrics
    trained_model = results['model']
    print("\nCross-validation scores:")
    print(results['cv_scores'])





if __name__ == "__main__":
    main()
