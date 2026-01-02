import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score
import joblib


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
def create_consumption_features(df):
    df = df.copy()

    df = check_datetime(df)
    
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


def train_consumption_model(df, feature_function=None, model_params=None, n_splits=5, save_path=None):
    """
    Train a LightGBM model for consumption prediction with time-series cross-validation.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Original dataframe with consumption data
    feature_function : callable, optional
        Function to create features from df (e.g., create_consumption_features)
        If None, assumes df already has features prepared
    model_params : dict, optional
        Custom LightGBM parameters. If None, uses defaults
    n_splits : int, default=5
        Number of time-series cross-validation splits
    save_path : str, optional
        Path to save the trained model (e.g., 'model.pkl')
    
    Returns:
    --------
    dict : Contains 'model', 'feature_names', 'cv_scores', and 'final_metrics'
    """
    # Prepare features
    if feature_function is not None:
        df_features = feature_function(df)
    else:
        df_features = df.copy()
    
    # Split features and target
    y = df_features['consumption']
    X = df_features.drop('consumption', axis=1)
    
    # Default model parameters
    if model_params is None:
        model_params = {
            'n_estimators': 500,
            'learning_rate': 0.05,
            'max_depth': 6,
            'num_leaves': 31,
            'min_child_samples': 20,
            'random_state': 42,
            'verbose': -1
        }
    
    # Initialize model
    model = LGBMRegressor(**model_params)
    
    # Time-based cross-validation
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    
    print(f"Training with {n_splits}-fold Time Series Cross-Validation...")
    print("-" * 60)
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        
        mae = mean_absolute_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        
        cv_scores.append({'fold': fold + 1, 'mae': mae, 'r2': r2})
        print(f"Fold {fold + 1} - MAE: {mae:.2f}, R²: {r2:.3f}")
    
    # Train final model on all data
    print("-" * 60)
    print("Training final model on full dataset...")
    model.fit(X, y)
    
    # Final predictions and metrics
    y_pred_final = model.predict(X)
    final_mae = mean_absolute_error(y, y_pred_final)
    final_r2 = r2_score(y, y_pred_final)
    
    print(f"Final Model - MAE: {final_mae:.2f}, R²: {final_r2:.3f}")
    
    # Save model if path provided
    if save_path:
        model_artifacts = {
            'model': model,
            'feature_names': X.columns.tolist(),
            'model_params': model_params
        }
        joblib.dump(model_artifacts, save_path)
        print(f"\nModel saved to: {save_path}")
    
    return {
        'model': model,
        'feature_names': X.columns.tolist(),
        'cv_scores': pd.DataFrame(cv_scores),
        'final_metrics': {'mae': final_mae, 'r2': final_r2}
    }


def predict_consumption(model_or_path, df_future, feature_function=None):
    """
    Make consumption predictions on future data.
    
    Parameters:
    -----------
    model_or_path : LGBMRegressor or str
        Trained model object or path to saved model
    df_future : pd.DataFrame
        Future dataframe with necessary columns for feature creation
    feature_function : callable, optional
        Function to create features from df_future
        If None, assumes df_future already has features prepared
    
    Returns:
    --------
    pd.DataFrame : Original dataframe with 'predicted_consumption' column added
    """
    # Load model if path provided
    if isinstance(model_or_path, str):
        model_artifacts = joblib.load(model_or_path)
        model = model_artifacts['model']
        expected_features = model_artifacts['feature_names']
    else:
        model = model_or_path
        expected_features = None
    
    # Prepare features
    if feature_function is not None:
        df_features = feature_function(df_future)
    else:
        df_features = df_future.copy()
    
    # Remove target if it exists
    if 'consumption' in df_features.columns:
        X_future = df_features.drop('consumption', axis=1)
    else:
        X_future = df_features
    
    # Verify features match
    if expected_features is not None:
        missing_features = set(expected_features) - set(X_future.columns)
        if missing_features:
            raise ValueError(f"Missing features: {missing_features}")
        X_future = X_future[expected_features]
    
    # Make predictions
    predictions = model.predict(X_future)
    
    # Add predictions to original dataframe
    result = df_future.copy()
    result['predicted_consumption'] = predictions
    
    return result

def check_datetime(df):
        # Ensure we have a DatetimeIndex (try common column names or coerce index)
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        else:
            coerced = pd.to_datetime(df.index, errors='coerce')
            if coerced.isna().any():
                raise ValueError("DataFrame must have a DatetimeIndex or a parsable 'datetime'/'date' column")
            df.index = coerced
    return df


    
"""     # 1. Train the model
    results = train_consumption_model(
        df=df,
        feature_function=create_consumption_features,
        n_splits=5,
        save_path='consumption_model.pkl'
    )
    
    # Access trained model and metrics
    trained_model = results['model']
    print("\nCross-validation scores:")
    print(results['cv_scores']) """
    
"""     # 2. Make predictions on future data
    # df_future should have the same structure as your training data
    predictions_df = predict_consumption(
        model_or_path='consumption_model.pkl',  # or use trained_model directly
        df_future=df_future,
        feature_function=create_consumption_features
    )
    
    print("\nPredictions:")
    print(predictions_df[['predicted_consumption']].head()) """