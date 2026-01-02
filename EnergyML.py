import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score



# THIS IS A MOCKUP CODE GENERATED FROM CLAUDE, NEEDS TO BE FIXED!!!! Fare anche gli add
""" Additional Weather Data to Consider
Since you can get more weather data, I'd recommend adding:
High Priority:

Solar Radiation (GHI) - Major impact on cooling loads
Humidity - Affects HVAC efficiency and comfort
Wind Speed - Impacts infiltration and heat loss

Medium Priority:
4. Cloud Cover - Affects lighting and solar gains
5. Dew Point - Better than humidity for some applications
These will likely improve your model by 5-15% in accuracy. """


# Feature engineering
def create_features(df):
    df = df.copy()
    
    # Time features
    df['hour'] = df.index.hour
    df['day_of_week'] = df.index.dayofweek
    df['month'] = df.index.month
    
    # Lag features
    df['consumption_lag_1h'] = df['consumption'].shift(1)
    df['consumption_lag_24h'] = df['consumption'].shift(24)
    df['consumption_lag_168h'] = df['consumption'].shift(168)  # 1 week
    
    # Rolling features
    df['temp_rolling_mean_3h'] = df['temperature'].rolling(3).mean()
    df['temp_rolling_mean_24h'] = df['temperature'].rolling(24).mean()
    
    # Temperature derivatives
    df['temp_change_1h'] = df['temperature'].diff(1)
    
    return df.dropna()  # Remove NaN from lag/rolling features

df_features = create_features(df)  # Assuming 'df' is your original dataframe
y = df_features['consumption']
X = df_features.drop('consumption', axis=1)

# Model setup
model = LGBMRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=6,
    num_leaves=31,
    min_child_samples=20,
    random_state=42,
    verbose=-1
)

# Time-based cross-validation (IMPORTANT!)
tscv = TimeSeriesSplit(n_splits=5)

# Train and evaluate
for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
    
    model.fit(X_train, y_train)
    y_pred = model.predict(X_val)
    
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    print(f"Fold {fold+1} - MAE: {mae:.2f}, R²: {r2:.3f}")