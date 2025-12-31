from get_weather import get_hist_weather


def calc_consumption():
    # Example coordinates for Rome, Italy
    latitude = 41.89
    longitude = 12.51
    start_date = "2025-12-01"
    end_date = "2025-12-15"

    weather_data = get_hist_weather(latitude, longitude, start_date, end_date)
    
    return weather_data

def main():    
    print(calc_consumption().head())
    print(calc_consumption().tail())

if __name__ == "__main__":
    main()
