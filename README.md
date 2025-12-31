#Energy Chief

Energy chief is a companion for understanding energy consumption and help everybody handling it.

## Feature 0: Calculate the thermical disperision from historical data
Estimate the consumption of a building

### Input
- Location --> Outside temperature (through [https://open-meteo.com/](Open-meteo))
- Historical consumption data

## Feature 1: Calculate convience of Natural Gas (NG) vs electricity for heating

### Input
- Electricity Price [€/kWh];
- NG Price [€/Sm3];
- Location (for accessing weather data);
- Heat Pump COP at different temperatures (interpolate);
- Average thermical dispersion [kW/h C°]

### Output
Heat pump/Boiler based on which is more convinient

## Feature 1.2: Add the PV