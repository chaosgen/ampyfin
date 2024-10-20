from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import API_KEY, API_SECRET, BASE_URL

# Function to fetch historical bar data using Alpaca StockHistoricalDataClient
def get_historical_data(ticker, client, days=100):
    """
    Fetch historical bar data for a given stock ticker.
    
    :param ticker: The stock ticker symbol.
    :param client: An instance of StockHistoricalDataClient.
    :param days: Number of days of historical data to fetch.
    :return: DataFrame with historical stock bar data.
    """
    start_time = datetime.now() - timedelta(days=days)  # Get data for the past 'days' days
    request_params = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TimeFrame.Day,
        start=start_time
    )
    
    bars = client.get_stock_bars(request_params)
    data = bars.df  # Returns a pandas DataFrame
    return data

# Machine Learning-based trading strategy
def random_forest_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Predict stock price movement using ML and decide trading action.

    :param ticker: The stock ticker symbol.
    :param current_price: The current price of the stock.
    :param historical_data: Historical stock data for the ticker.
    :param account_cash: Available cash in the account.
    :param portfolio_qty: Quantity of stock held in the portfolio.
    :param total_portfolio_value: Total value of the portfolio.
    :return: Tuple (action, quantity, ticker).
    """
    
    # Preprocessing: Add features such as moving averages
    window_short = 10
    window_long = 50
    historical_data['MA10'] = historical_data['close'].rolling(window=window_short).mean()
    historical_data['MA50'] = historical_data['close'].rolling(window=window_long).mean()
    
    # Drop NaN values after creating moving averages
    historical_data.dropna(inplace=True)
    
    # Create target variable: 1 if stock price goes up, 0 if it goes down
    historical_data['Target'] = np.where(historical_data['close'].shift(-1) > historical_data['close'], 1, 0)
    
    # Features (you can add more indicators as features)
    features = ['close', 'volume', 'MA10', 'MA50']
    X = historical_data[features]
    y = historical_data['Target']
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # Scale the features (important for ML models)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Initialize the Random Forest Classifier
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    # Predict the stock movement on the test set and evaluate accuracy
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy * 100:.2f}%")
    
    # Predict future movement (use the latest data point)
    X_latest = scaler.transform([X.iloc[-1]])  # Use the most recent data
    prediction = model.predict(X_latest)[0]  # 1 = up, 0 = down
    
    # Define max investment (10% of total portfolio value)
    max_investment = total_portfolio_value * 0.10
    
    # Trading logic based on prediction and available cash
    if prediction == 1 and account_cash > 0:  # If prediction is "up" (buy)
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif prediction == 0 and portfolio_qty > 0:  # If prediction is "down" (sell)
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))  # Sell 50% of portfolio, or at least 1
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def momentum_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Momentum strategy logic to determine buy or sell signals based on short and long moving averages.
    Limits the amount to invest to less than 10% of the total portfolio.
    """
    # Maximum percentage of portfolio to invest per trade
    max_investment_percentage = 0.10  # 10% of total portfolio value
    max_investment = total_portfolio_value * max_investment_percentage

    # Momentum Logic
    short_window = 10
    long_window = 50
    
    short_ma = historical_data['close'].rolling(short_window).mean().iloc[-1]
    long_ma = historical_data['close'].rolling(long_window).mean().iloc[-1]

    # Buy signal (short MA crosses above long MA)
    if short_ma > long_ma and account_cash > 0:
        # Calculate amount to invest based on available cash and max investment
        amount_to_invest = min(account_cash, max_investment)
        quantity_to_buy = int(amount_to_invest // current_price)  # Calculate quantity to buy

        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)

    # Sell signal (short MA crosses below long MA)
    elif short_ma < long_ma and portfolio_qty > 0:
        # Sell 50% of the current holding, at least 1 share
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)

    # No action triggered
    return ('hold', portfolio_qty, ticker)

def mean_reversion_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Mean reversion strategy: Buy if the stock price is below the moving average, sell if above.

    :param ticker: The stock ticker symbol.
    :param current_price: The current price of the stock.
    :param historical_data: Historical stock data for the ticker.
    :param account_cash: Available cash in the account.
    :param portfolio_qty: Quantity of stock held in the portfolio.
    :param total_portfolio_value: Total value of the portfolio.
    :return: Tuple (action, quantity, ticker).
    """
    
    # Calculate moving average
    window = 20  # Use a 20-day moving average
    historical_data['MA20'] = historical_data['close'].rolling(window=window).mean()
    
    # Drop NaN values after creating the moving average
    historical_data.dropna(inplace=True)
    
    # Define max investment (10% of total portfolio value)
    max_investment = total_portfolio_value * 0.10

    # Buy signal: if current price is below the moving average by more than 2%
    if current_price < historical_data['MA20'].iloc[-1] * 0.98 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    # Sell signal: if current price is above the moving average by more than 2%
    elif current_price > historical_data['MA20'].iloc[-1] * 1.02 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))  # Sell 50% of portfolio, or at least 1
        return ('sell', quantity_to_sell, ticker)
    
    # No action triggered
    return ('hold', portfolio_qty, ticker)

def neural_network_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Predict stock price movement using a neural network and decide trading action.

    :param ticker: The stock ticker symbol.
    :param current_price: The current price of the stock.
    :param historical_data: Historical stock data for the ticker.
    :param account_cash: Available cash in the account.
    :param portfolio_qty: Quantity of stock held in the portfolio.
    :param total_portfolio_value: Total value of the portfolio.
    :return: Tuple (action, quantity, ticker).
    """
    # Preprocessing: Add features such as moving averages
    window_short = 10
    window_long = 50
    historical_data['MA10'] = historical_data['close'].rolling(window=window_short).mean()
    historical_data['MA50'] = historical_data['close'].rolling(window=window_long).mean()

    # Drop NaN values
    historical_data.dropna(inplace=True)

    # Create target variable: 1 if stock price goes up, 0 if it goes down
    historical_data['Target'] = np.where(historical_data['close'].shift(-1) > historical_data['close'], 1, 0)

    # Features (you can add more indicators as features)
    features = ['close', 'volume', 'MA10', 'MA50']
    X = historical_data[features]
    y = historical_data['Target']

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Scale the features
    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Define the neural network model
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=(X_train_scaled.shape[1],)),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    
    # Train the model
    model.fit(X_train_scaled, y_train, epochs=10, batch_size=32, verbose=0)

    # Evaluate the model
    loss, accuracy = model.evaluate(X_test_scaled, y_test, verbose=0)
    print(f"Neural Network Accuracy: {accuracy * 100:.2f}%")

    # Predict the next movement
    X_latest = scaler.transform([X.iloc[-1]])  # Use the most recent data
    prediction = model.predict(X_latest)[0][0]  # 1 = up, 0 = down
    
    # Define max investment (10% of total portfolio value)
    max_investment = total_portfolio_value * 0.10
    
    # Trading logic
    if prediction > 0.5 and account_cash > 0:  # Buy signal
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)

    elif prediction <= 0.5 and portfolio_qty > 0:  # Sell signal
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))  # Sell 50% of portfolio
        return ('sell', quantity_to_sell, ticker)

    return ('hold', portfolio_qty, ticker)

def rsi_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value, rsi_period=14):
    """
    RSI-based trading strategy to determine buy or sell signals based on RSI levels.

    :param ticker: The stock ticker symbol.
    :param current_price: The current price of the stock.
    :param historical_data: Historical stock data for the ticker.
    :param account_cash: Available cash in the account.
    :param portfolio_qty: Quantity of stock held in the portfolio.
    :param total_portfolio_value: Total value of the portfolio.
    :param rsi_period: Period for calculating the RSI (default is 14).
    :return: Tuple (action, quantity, ticker).
    """
    # Calculate daily price change
    delta = historical_data['close'].diff()

    # Calculate gains and losses
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    # Calculate average gain and loss
    avg_gain = pd.Series(gain).rolling(window=rsi_period).mean()
    avg_loss = pd.Series(loss).rolling(window=rsi_period).mean()

    # Calculate RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]

    # Maximum percentage of portfolio to invest per trade
    max_investment_percentage = 0.10  # 10% of total portfolio value
    max_investment = total_portfolio_value * max_investment_percentage

    # Buy signal (RSI below 30 indicates oversold conditions)
    if current_rsi < 30 and account_cash > 0:
        amount_to_invest = min(account_cash, max_investment)
        quantity_to_buy = int(amount_to_invest // current_price)
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)

    # Sell signal (RSI above 70 indicates overbought conditions)
    elif current_rsi > 70 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))  # Sell 50% of portfolio
        return ('sell', quantity_to_sell, ticker)

    # No action triggered
    return ('hold', portfolio_qty, ticker)

