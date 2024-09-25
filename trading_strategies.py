from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import pandas as pd
from config import API_KEY, API_SECRET, BASE_URL

# Function to fetch historical bar data using Alpaca StockHistoricalDataClientfrom datetime import datetime, timedelta
import pandas as pd
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

def combined_trading_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    # Check if total_portfolio_value is a numeric type and convert if necessary
    if isinstance(total_portfolio_value, str):
        try:
            total_portfolio_value = float(total_portfolio_value)
        except ValueError:
            raise ValueError("total_portfolio_value must be convertible to a float.")
    
    # Ensure total_portfolio_value is a numeric type
    if not isinstance(total_portfolio_value, (int, float)):
        raise TypeError("total_portfolio_value must be an int or float.")

    # Define a maximum investment percentage per trade
    max_investment_percentage = 0.075  # Limit to 10% of total portfolio value

    # Calculate the maximum amount you can invest based on the percentage
    max_investment = total_portfolio_value * max_investment_percentage
    
    # Mean Reversion Logic
    window = 20
    moving_average = historical_data['close'].rolling(window).mean().iloc[-1]
    
    lower_threshold = 0.95 * moving_average  # Buy when price is 5% below the MA
    upper_threshold = 1.05 * moving_average  # Sell when price is 5% above the MA
    
    mean_reversion_signal = None
    if current_price < lower_threshold and account_cash > 0:
        # Limit quantity to buy based on max_investment
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        mean_reversion_signal = ('buy', quantity_to_buy, ticker)
    elif current_price > upper_threshold and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))  # Sell 50% of portfolio, or at least 1
        mean_reversion_signal = ('sell', quantity_to_sell, ticker)
    
    # Momentum Logic
    short_window = 10
    long_window = 50
    
    short_ma = historical_data['close'].rolling(short_window).mean().iloc[-1]
    long_ma = historical_data['close'].rolling(long_window).mean().iloc[-1]
    
    momentum_signal = None
    if short_ma > long_ma and account_cash > 0:
        # Limit quantity to buy based on max_investment
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        momentum_signal = ('buy', quantity_to_buy, ticker)
    elif short_ma < long_ma and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))  # Sell 50% of portfolio, or at least 1
        momentum_signal = ('sell', quantity_to_sell, ticker)
    
    # Determine final action
    if mean_reversion_signal and momentum_signal:
        # If both strategies suggest buying
        if mean_reversion_signal[0] == 'buy' and momentum_signal[0] == 'buy':
            return ('buy', min(mean_reversion_signal[1], momentum_signal[1]), ticker)
        # If mean reversion suggests buying and momentum suggests selling
        elif mean_reversion_signal[0] == 'buy' and momentum_signal[0] == 'sell':
            return ('hold', portfolio_qty, ticker)
        # If mean reversion suggests selling and momentum suggests buying
        elif mean_reversion_signal[0] == 'sell' and momentum_signal[0] == 'buy':
            return ('hold', portfolio_qty, ticker)
        # If both suggest selling
        elif mean_reversion_signal[0] == 'sell' and momentum_signal[0] == 'sell':
            return ('sell', min(mean_reversion_signal[1], momentum_signal[1]), ticker)
    
    # If one strategy suggests action while the other does not
    if mean_reversion_signal:
        return mean_reversion_signal
    if momentum_signal:
        return momentum_signal
    
    return ('hold', portfolio_qty, ticker)
