import pandas as pd
import os
import re


def load_csv(folder, edistribuzione_format=False):
    """
    Load all the CSVs in the specified folder and concatenate them into a single DataFrame.

    Point of attention: if edistribuzione_format is False, the standard format is everything but standardized.

    """
    try:
        filepaths = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
        df = pd.concat(map(lambda f: pd.read_csv(f, sep=';', index_col=False, decimal=','), filepaths), ignore_index=True)
    except FileNotFoundError:
        print(f"File non trovato: {folder}")
        return None
    
    if edistribuzione_format:
        df = reprocess_csv_edistribuzione(df)

    return df

def reprocess_csv_edistribuzione(df):
    """
    Reprocess the CSV from E-Distribuzione to have a DataFrame with hourly profile.

    Args:
        df (pandas.DataFrame): DataFrame obtained from edistribuzione CSV, with the following structure (unit measure is kWh):
        
            | timestamp  | 00:00-06:00 | 06:00-12:00 | 12:00-18:00 | 18:00-24:00 |
            |------------|-------------|-------------|-------------|-------------|
            | 2023-01-01 | 1,23        | 4,56        | 7,89        | 0,12        | 
            | 2023-01-02 | 2,34        | 5,67        | 8,90        | 1,23        | 
            | ...        | ...         | ...         | ...         | ...         | 

    Returns:
        pandas.DataFrame: Dataframe with everything in one column.
    """

# Identify time interval columns (all columns except the first one)
    time_cols = df.columns[1:].tolist()
    
    # Melt the dataframe to long format
    df_long = df.melt(
        id_vars=df.columns[0],
        value_vars=time_cols,
        var_name='time_interval',
        value_name='consumption'
    )
        
    # Extract start time from interval (e.g., "00:00-00:15" -> "00:00")
    df_long['time'] = df_long['time_interval'].apply(extract_start_time)

    # Combine date and time into a single timestamp
    df_long['datetime'] = pd.to_datetime(
        df_long[df.columns[0]].astype(str) + ' ' + df_long['time'],
    format='%d/%m/%Y %H:%M'
    )

    # Select and sort final columns
    result = df_long[['datetime', 'consumption']].sort_values('datetime').reset_index(drop=True)


    return result

def extract_start_time(interval_str):
    """
    Extract the start time from various interval formats.
    Examples: "00:00-06:00" -> "00:00", "14:00" -> "14:00"
    """
    # Try to match time range format (e.g., "00:00-06:00")
    match = re.match(r'(\d{1,2}:\d{2})', str(interval_str))
    if match:
        return match.group(1)
    return interval_str

def create_output_file(input_directory='input', output_directory='data'):

    consumption_df = load_csv(input_directory)

    consumption_df.to_csv(output_directory+'/output.csv', index=False)

    return None