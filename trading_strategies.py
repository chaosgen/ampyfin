from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import API_KEY, API_SECRET, BASE_URL

import numpy as np
import pandas as pd

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


# ... (existing code remains unchanged)

def rsi_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    RSI strategy: Buy when RSI is oversold, sell when overbought.
    """
    window = 14
    max_investment = total_portfolio_value * 0.10

    # Calculate RSI
    delta = historical_data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    current_rsi = rsi.iloc[-1]

    # Buy signal: RSI below 30 (oversold)
    if current_rsi < 30 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)

    # Sell signal: RSI above 70 (overbought)
    elif current_rsi > 70 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)

    # No action triggered
    return ('hold', portfolio_qty, ticker)

def bollinger_bands_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Bollinger Bands strategy: Buy when price touches lower band, sell when it touches upper band.
    """
    window = 20
    num_std = 2
    max_investment = total_portfolio_value * 0.10

    historical_data['MA'] = historical_data['close'].rolling(window=window).mean()
    historical_data['STD'] = historical_data['close'].rolling(window=window).std()
    historical_data['Upper'] = historical_data['MA'] + (num_std * historical_data['STD'])
    historical_data['Lower'] = historical_data['MA'] - (num_std * historical_data['STD'])

    upper_band = historical_data['Upper'].iloc[-1]
    lower_band = historical_data['Lower'].iloc[-1]

    # Buy signal: Price at or below lower band
    if current_price <= lower_band and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)

    # Sell signal: Price at or above upper band
    elif current_price >= upper_band and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)

    # No action triggered
    return ('hold', portfolio_qty, ticker)

def macd_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    MACD strategy: Buy when MACD line crosses above signal line, sell when it crosses below.
    """
    max_investment = total_portfolio_value * 0.10

    # Calculate MACD
    exp1 = historical_data['close'].ewm(span=12, adjust=False).mean()
    exp2 = historical_data['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()

    # Get the last two MACD and signal values
    macd_current, macd_prev = macd.iloc[-1], macd.iloc[-2]
    signal_current, signal_prev = signal.iloc[-1], signal.iloc[-2]

    # Buy signal: MACD line crosses above signal line
    if macd_prev <= signal_prev and macd_current > signal_current and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)

    # Sell signal: MACD line crosses below signal line
    elif macd_prev >= signal_prev and macd_current < signal_current and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)

    # No action triggered
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

def triple_moving_average_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Triple Moving Average Crossover Strategy: Uses 3 moving averages to generate stronger signals
    """
    max_investment = total_portfolio_value * 0.10
    
    # Calculate three moving averages
    short_ma = historical_data['close'].rolling(window=5).mean()
    medium_ma = historical_data['close'].rolling(window=20).mean()
    long_ma = historical_data['close'].rolling(window=50).mean()
    
    # Get current and previous values
    current_short = short_ma.iloc[-1]
    current_medium = medium_ma.iloc[-1]
    current_long = long_ma.iloc[-1]
    
    prev_short = short_ma.iloc[-2]
    prev_medium = medium_ma.iloc[-2]
    
    # Buy when short MA crosses above both medium and long MA
    if (prev_short <= prev_medium and current_short > current_medium and 
        current_short > current_long and account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    # Sell when short MA crosses below medium MA
    elif prev_short >= prev_medium and current_short < current_medium and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def volume_price_trend_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Volume Price Trend (VPT) Strategy: Combines price and volume for stronger signals
    """
    max_investment = total_portfolio_value * 0.10
    
    # Calculate VPT
    price_change = historical_data['close'].pct_change()
    vpt = (price_change * historical_data['volume']).cumsum()
    
    # Calculate VPT moving average
    vpt_ma = vpt.rolling(window=15).mean()
    
    current_vpt = vpt.iloc[-1]
    prev_vpt = vpt.iloc[-2]
    current_vpt_ma = vpt_ma.iloc[-1]
    prev_vpt_ma = vpt_ma.iloc[-2]
    
    # Buy signal: VPT crosses above its MA
    if prev_vpt <= prev_vpt_ma and current_vpt > current_vpt_ma and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    # Sell signal: VPT crosses below its MA
    elif prev_vpt >= prev_vpt_ma and current_vpt < current_vpt_ma and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def keltner_channel_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Keltner Channel Strategy: Similar to Bollinger Bands but uses ATR for volatility
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    multiplier = 2
    
    # Calculate ATR
    high_low = historical_data['high'] - historical_data['low']
    high_close = abs(historical_data['high'] - historical_data['close'].shift())
    low_close = abs(historical_data['low'] - historical_data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=window).mean()
    
    # Calculate Keltner Channels
    middle_line = historical_data['close'].rolling(window=window).mean()
    upper_channel = middle_line + (multiplier * atr)
    lower_channel = middle_line - (multiplier * atr)
    
    # Buy signal: Price crosses below lower channel
    if current_price <= lower_channel.iloc[-1] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    # Sell signal: Price crosses above upper channel
    elif current_price >= upper_channel.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def adaptive_momentum_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Adaptive Momentum Strategy: Adjusts momentum calculation based on volatility
    """
    max_investment = total_portfolio_value * 0.10
    
    # Calculate volatility
    returns = historical_data['close'].pct_change()
    volatility = returns.rolling(window=21).std()
    
    # Adjust lookback period based on volatility
    base_period = 20
    vol_adjust = (volatility.iloc[-1] / volatility.mean()) * base_period
    lookback = int(max(10, min(40, vol_adjust)))
    
    # Calculate momentum
    momentum = historical_data['close'].diff(lookback)
    mom_ma = momentum.rolling(window=10).mean()
    
    # Buy signal: Positive momentum and increasing
    if momentum.iloc[-1] > 0 and momentum.iloc[-1] > mom_ma.iloc[-1] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    # Sell signal: Negative momentum and decreasing
    elif momentum.iloc[-1] < 0 and momentum.iloc[-1] < mom_ma.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def dual_thrust_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Dual Thrust Strategy: Range breakout strategy with dynamic thresholds
    """
    max_investment = total_portfolio_value * 0.10
    lookback = 4
    k1 = 0.7  # Upper threshold multiplier
    k2 = 0.7  # Lower threshold multiplier
    
    # Calculate range
    hh = historical_data['high'].rolling(window=lookback).max()
    lc = historical_data['close'].rolling(window=lookback).min()
    hc = historical_data['close'].rolling(window=lookback).max()
    ll = historical_data['low'].rolling(window=lookback).min()
    
    range_val = max(hh - lc, hc - ll)
    
    # Calculate upper and lower bounds
    upper_bound = historical_data['open'].iloc[-1] + k1 * range_val.iloc[-1]
    lower_bound = historical_data['open'].iloc[-1] - k2 * range_val.iloc[-1]
    
    # Buy signal: Price breaks above upper bound
    if current_price > upper_bound and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    # Sell signal: Price breaks below lower bound
    elif current_price < lower_bound and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def hull_moving_average_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Hull Moving Average Strategy: Reduces lag in moving averages
    """
    max_investment = total_portfolio_value * 0.10
    n = 20  # Base period
    
    # Calculate Hull MA: HMA = WMA(2*WMA(n/2) - WMA(n))
    wma_n = historical_data['close'].rolling(window=n).apply(
        lambda x: np.sum(x * np.arange(1, n + 1)) / np.sum(np.arange(1, n + 1)))
    wma_n_half = historical_data['close'].rolling(window=n//2).apply(
        lambda x: np.sum(x * np.arange(1, n//2 + 1)) / np.sum(np.arange(1, n//2 + 1)))
    
    hull = 2 * wma_n_half - wma_n
    hma = hull.rolling(window=int(np.sqrt(n))).apply(
        lambda x: np.sum(x * np.arange(1, int(np.sqrt(n)) + 1)) / np.sum(np.arange(1, int(np.sqrt(n)) + 1)))
    
    if current_price > hma.iloc[-1] and hma.iloc[-1] > hma.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif current_price < hma.iloc[-1] and hma.iloc[-1] < hma.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def elder_ray_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Elder Ray Strategy: Uses Bull and Bear Power indicators
    """
    max_investment = total_portfolio_value * 0.10
    period = 13
    
    # Calculate EMA
    ema = historical_data['close'].ewm(span=period, adjust=False).mean()
    
    # Calculate Bull and Bear Power
    bull_power = historical_data['high'] - ema
    bear_power = historical_data['low'] - ema
    
    if bull_power.iloc[-1] > 0 and bear_power.iloc[-1] < 0 and \
       bull_power.iloc[-1] > bull_power.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif bull_power.iloc[-1] < 0 and bear_power.iloc[-1] < bear_power.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def chande_momentum_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Chande Momentum Oscillator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    # Calculate price changes
    price_changes = historical_data['close'].diff()
    
    # Calculate sum of up and down moves
    up_sum = price_changes.rolling(window=period).apply(lambda x: x[x > 0].sum())
    down_sum = price_changes.rolling(window=period).apply(lambda x: abs(x[x < 0].sum()))
    
    # Calculate CMO
    cmo = 100 * ((up_sum - down_sum) / (up_sum + down_sum))
    
    if cmo.iloc[-1] < -50 and cmo.iloc[-1] > cmo.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif cmo.iloc[-1] > 50 and cmo.iloc[-1] < cmo.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def dema_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Double Exponential Moving Average Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    # Calculate DEMA
    ema = historical_data['close'].ewm(span=period, adjust=False).mean()
    ema_of_ema = ema.ewm(span=period, adjust=False).mean()
    dema = 2 * ema - ema_of_ema
    
    if current_price > dema.iloc[-1] and dema.iloc[-1] > dema.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif current_price < dema.iloc[-1] and dema.iloc[-1] < dema.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def price_channel_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Price Channel Breakout Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    upper_channel = historical_data['high'].rolling(window=period).max()
    lower_channel = historical_data['low'].rolling(window=period).min()
    
    if current_price > upper_channel.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif current_price < lower_channel.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def mass_index_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Mass Index Strategy for reversal detection
    """
    max_investment = total_portfolio_value * 0.10
    period = 25
    ema_period = 9
    
    # Calculate the Mass Index
    high_low = historical_data['high'] - historical_data['low']
    ema1 = high_low.ewm(span=ema_period).mean()
    ema2 = ema1.ewm(span=ema_period).mean()
    ratio = ema1 / ema2
    mass_index = ratio.rolling(window=period).sum()
    
    if mass_index.iloc[-1] > 27 and mass_index.iloc[-2] < 27 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif mass_index.iloc[-1] < 26.5 and mass_index.iloc[-2] > 26.5 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def vortex_indicator_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Vortex Indicator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 14
    
    # Calculate True Range
    high_low = historical_data['high'] - historical_data['low']
    high_close = abs(historical_data['high'] - historical_data['close'].shift())
    low_close = abs(historical_data['low'] - historical_data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate VM+ and VM-
    vm_plus = abs(historical_data['high'] - historical_data['low'].shift())
    vm_minus = abs(historical_data['low'] - historical_data['high'].shift())
    
    # Calculate VI+ and VI-
    vi_plus = vm_plus.rolling(period).sum() / tr.rolling(period).sum()
    vi_minus = vm_minus.rolling(period).sum() / tr.rolling(period).sum()
    
    if vi_plus.iloc[-1] > vi_minus.iloc[-1] and \
       vi_plus.iloc[-2] <= vi_minus.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif vi_plus.iloc[-1] < vi_minus.iloc[-1] and \
         vi_plus.iloc[-2] >= vi_minus.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def aroon_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Aroon Indicator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 25
    
    # Calculate Aroon indicators
    rolling_high = historical_data['high'].rolling(period + 1)
    rolling_low = historical_data['low'].rolling(period + 1)
    
    aroon_up = rolling_high.apply(lambda x: float(np.argmax(x)) / period * 100)
    aroon_down = rolling_low.apply(lambda x: float(np.argmin(x)) / period * 100)
    
    if aroon_up.iloc[-1] > 70 and aroon_down.iloc[-1] < 30 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif aroon_up.iloc[-1] < 30 and aroon_down.iloc[-1] > 70 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def ultimate_oscillator_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Ultimate Oscillator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    
    # Calculate buying pressure and true range
    bp = historical_data['close'] - pd.concat([historical_data['low'], 
                                             historical_data['close'].shift(1)], axis=1).min(axis=1)
    tr = pd.concat([historical_data['high'] - historical_data['low'],
                   abs(historical_data['high'] - historical_data['close'].shift(1)),
                   abs(historical_data['low'] - historical_data['close'].shift(1))], axis=1).max(axis=1)
    
    # Calculate averages for different periods
    avg7 = bp.rolling(7).sum() / tr.rolling(7).sum()
    avg14 = bp.rolling(14).sum() / tr.rolling(14).sum()
    avg28 = bp.rolling(28).sum() / tr.rolling(28).sum()
    
    # Calculate Ultimate Oscillator
    uo = 100 * ((4 * avg7 + 2 * avg14 + avg28) / (4 + 2 + 1))
    
    if uo.iloc[-1] < 30 and uo.iloc[-1] > uo.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif uo.iloc[-1] > 70 and uo.iloc[-1] < uo.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def trix_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    TRIX Strategy: Triple Exponential Average
    """
    max_investment = total_portfolio_value * 0.10
    period = 15
    signal_period = 9
    
    # Calculate TRIX
    ema1 = historical_data['close'].ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    trix = 100 * (ema3 - ema3.shift(1)) / ema3.shift(1)
    signal = trix.rolling(window=signal_period).mean()
    
    if trix.iloc[-1] > signal.iloc[-1] and trix.iloc[-2] <= signal.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif trix.iloc[-1] < signal.iloc[-1] and trix.iloc[-2] >= signal.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def kst_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Know Sure Thing (KST) Oscillator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    
    # ROC periods
    r1, r2, r3, r4 = 10, 15, 20, 30
    # SMA periods
    s1, s2, s3, s4 = 10, 10, 10, 15
    
    # Calculate ROC values
    roc1 = historical_data['close'].diff(r1) / historical_data['close'].shift(r1) * 100
    roc2 = historical_data['close'].diff(r2) / historical_data['close'].shift(r2) * 100
    roc3 = historical_data['close'].diff(r3) / historical_data['close'].shift(r3) * 100
    roc4 = historical_data['close'].diff(r4) / historical_data['close'].shift(r4) * 100
    
    # Calculate KST
    k1 = roc1.rolling(s1).mean()
    k2 = roc2.rolling(s2).mean()
    k3 = roc3.rolling(s3).mean()
    k4 = roc4.rolling(s4).mean()
    
    kst = (k1 * 1) + (k2 * 2) + (k3 * 3) + (k4 * 4)
    signal = kst.rolling(9).mean()
    
    if kst.iloc[-1] > signal.iloc[-1] and kst.iloc[-2] <= signal.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif kst.iloc[-1] < signal.iloc[-1] and kst.iloc[-2] >= signal.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def psar_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Parabolic SAR Strategy
    """
    max_investment = total_portfolio_value * 0.10
    af = 0.02  # Acceleration Factor
    max_af = 0.2
    
    high = historical_data['high'].values
    low = historical_data['low'].values
    
    # Initialize arrays
    psar = np.zeros(len(high))
    trend = np.zeros(len(high))
    ep = np.zeros(len(high))
    af_values = np.zeros(len(high))
    
    # Set initial values
    trend[0] = 1 if high[0] > low[0] else -1
    ep[0] = high[0] if trend[0] == 1 else low[0]
    psar[0] = low[0] if trend[0] == 1 else high[0]
    af_values[0] = af
    
    # Calculate PSAR
    for i in range(1, len(high)):
        psar[i] = psar[i-1] + af_values[i-1] * (ep[i-1] - psar[i-1])
        
        if trend[i-1] == 1:
            if low[i] > psar[i]:
                trend[i] = 1
                if high[i] > ep[i-1]:
                    ep[i] = high[i]
                    af_values[i] = min(af_values[i-1] + af, max_af)
                else:
                    ep[i] = ep[i-1]
                    af_values[i] = af_values[i-1]
            else:
                trend[i] = -1
                ep[i] = low[i]
                af_values[i] = af
        else:
            if high[i] < psar[i]:
                trend[i] = -1
                if low[i] < ep[i-1]:
                    ep[i] = low[i]
                    af_values[i] = min(af_values[i-1] + af, max_af)
                else:
                    ep[i] = ep[i-1]
                    af_values[i] = af_values[i-1]
            else:
                trend[i] = 1
                ep[i] = high[i]
                af_values[i] = af
    
    if trend[-1] == 1 and trend[-2] == -1 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif trend[-1] == -1 and trend[-2] == 1 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def stochastic_momentum_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Stochastic Momentum Strategy
    """
    max_investment = total_portfolio_value * 0.10
    k_period = 14
    d_period = 3
    
    # Calculate Stochastic Oscillator
    low_min = historical_data['low'].rolling(window=k_period).min()
    high_max = historical_data['high'].rolling(window=k_period).max()
    
    k = 100 * (historical_data['close'] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    
    # Calculate Momentum
    momentum = historical_data['close'].diff(k_period)
    
    if k.iloc[-1] < 20 and momentum.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif k.iloc[-1] > 80 and momentum.iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def williams_vix_fix_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Williams VIX Fix Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 22
    
    # Calculate highest high and lowest low
    highest_high = historical_data['high'].rolling(window=period).max()
    lowest_low = historical_data['low'].rolling(window=period).min()
    
    # Calculate Williams VIX Fix
    wvf = ((highest_high - historical_data['low']) / highest_high) * 100
    
    # Calculate Bollinger Bands for WVF
    wvf_sma = wvf.rolling(window=period).mean()
    wvf_std = wvf.rolling(window=period).std()
    upper_band = wvf_sma + (2 * wvf_std)
    
    if wvf.iloc[-1] > upper_band.iloc[-1] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif wvf.iloc[-1] < wvf_sma.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def connors_rsi_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Connors RSI Strategy
    """
    max_investment = total_portfolio_value * 0.10
    rsi_period = 3
    streak_period = 2
    rank_period = 100
    
    # Calculate RSI
    delta = historical_data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Calculate Streak RSI
    streak = np.zeros(len(historical_data))
    for i in range(1, len(historical_data)):
        if historical_data['close'].iloc[i] > historical_data['close'].iloc[i-1]:
            streak[i] = min(streak[i-1] + 1, streak_period)
        elif historical_data['close'].iloc[i] < historical_data['close'].iloc[i-1]:
            streak[i] = max(streak[i-1] - 1, -streak_period)
    streak_rsi = 100 * (streak - streak.min()) / (streak.max() - streak.min())
    
    # Calculate Percentile Rank
    def percentile_rank(x):
        return 100 * (stats.percentileofscore(x, x.iloc[-1]) / 100)
    
    rank = historical_data['close'].rolling(rank_period).apply(percentile_rank)
    
    # Combine all components
    crsi = (rsi + streak_rsi + rank) / 3
    
    if crsi.iloc[-1] < 20 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif crsi.iloc[-1] > 80 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def dpo_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Detrended Price Oscillator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    # Calculate DPO
    shift = period // 2 + 1
    ma = historical_data['close'].rolling(window=period).mean()
    dpo = historical_data['close'].shift(shift) - ma
    
    if dpo.iloc[-1] < 0 and dpo.iloc[-1] > dpo.iloc[-2] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif dpo.iloc[-1] > 0 and dpo.iloc[-1] < dpo.iloc[-2] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def fisher_transform_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Fisher Transform Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 10
    
    # Calculate the median price
    median_price = (historical_data['high'] + historical_data['low']) / 2
    
    # Normalize price
    normalized = (median_price - median_price.rolling(period).min()) / \
                (median_price.rolling(period).max() - median_price.rolling(period).min())
    
    # Calculate Fisher Transform
    fisher = 0.5 * np.log((1 + normalized) / (1 - normalized))
    signal = fisher.shift(1)
    
    if fisher.iloc[-1] > signal.iloc[-1] and fisher.iloc[-1] < 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif fisher.iloc[-1] < signal.iloc[-1] and fisher.iloc[-1] > 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def ehlers_fisher_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Ehlers Fisher Transform Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 10
    
    # Calculate EMA of close prices
    ema = historical_data['close'].ewm(span=period, adjust=False).mean()
    
    # Calculate Fisher Transform of EMA
    normalized = (ema - ema.rolling(period).min()) / \
                (ema.rolling(period).max() - ema.rolling(period).min())
    normalized = 0.999 * normalized  # Ensure bounds
    
    fisher = 0.5 * np.log((1 + normalized) / (1 - normalized))
    trigger = fisher.shift(1)
    
    if fisher.iloc[-1] > trigger.iloc[-1] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif fisher.iloc[-1] < trigger.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def schaff_trend_cycle_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Schaff Trend Cycle Strategy
    """
    max_investment = total_portfolio_value * 0.10
    stc_period = 10
    fast_period = 23
    slow_period = 50
    
    # Calculate MACD
    exp1 = historical_data['close'].ewm(span=fast_period, adjust=False).mean()
    exp2 = historical_data['close'].ewm(span=slow_period, adjust=False).mean()
    macd = exp1 - exp2
    
    # Calculate Schaff Trend Cycle
    def calculate_stc(data):
        lowest_low = data.rolling(window=stc_period).min()
        highest_high = data.rolling(window=stc_period).max()
        k = 100 * (data - lowest_low) / (highest_high - lowest_low)
        return k
    
    k = calculate_stc(macd)
    d = calculate_stc(k)
    
    if d.iloc[-1] < 25 and d.iloc[-2] >= 25 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif d.iloc[-1] > 75 and d.iloc[-2] <= 75 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def laguerre_rsi_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Laguerre RSI Strategy
    """
    max_investment = total_portfolio_value * 0.10
    gamma = 0.7
    
    prices = historical_data['close'].values
    l0 = np.zeros_like(prices)
    l1 = np.zeros_like(prices)
    l2 = np.zeros_like(prices)
    l3 = np.zeros_like(prices)
    
    # Calculate Laguerre RSI
    for i in range(1, len(prices)):
        l0[i] = (1 - gamma) * prices[i] + gamma * l0[i-1]
        l1[i] = -gamma * l0[i] + l0[i-1] + gamma * l1[i-1]
        l2[i] = -gamma * l1[i] + l1[i-1] + gamma * l2[i-1]
        l3[i] = -gamma * l2[i] + l2[i-1] + gamma * l3[i-1]
    
    lrsi = (l0 - l3) / (l0 + l3) * 100
    
    if lrsi[-1] < 20 and lrsi[-2] >= 20 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif lrsi[-1] > 80 and lrsi[-2] <= 80 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def rainbow_oscillator_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Rainbow Oscillator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    periods = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    
    # Calculate multiple SMAs
    smas = pd.DataFrame()
    for period in periods:
        smas[f'SMA_{period}'] = historical_data['close'].rolling(window=period).mean()
    
    # Calculate Rainbow Oscillator
    highest = smas.max(axis=1)
    lowest = smas.min(axis=1)
    rainbow = ((historical_data['close'] - lowest) / (highest - lowest)) * 100
    
    if rainbow.iloc[-1] < 20 and rainbow.iloc[-2] >= 20 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif rainbow.iloc[-1] > 80 and rainbow.iloc[-2] <= 80 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def heikin_ashi_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Heikin Ashi Candlestick Strategy
    """
    max_investment = total_portfolio_value * 0.10
    
    # Calculate Heikin Ashi candles
    ha_close = (historical_data['open'] + historical_data['high'] + 
                historical_data['low'] + historical_data['close']) / 4
    ha_open = pd.Series(index=historical_data.index)
    ha_open.iloc[0] = historical_data['open'].iloc[0]
    for i in range(1, len(historical_data)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
    
    ha_high = historical_data[['high', 'open', 'close']].max(axis=1)
    ha_low = historical_data[['low', 'open', 'close']].min(axis=1)
    
    # Generate signals based on Heikin Ashi patterns
    if (ha_close.iloc[-1] > ha_open.iloc[-1] and 
        ha_close.iloc[-2] > ha_open.iloc[-2] and 
        ha_close.iloc[-3] < ha_open.iloc[-3] and 
        account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif (ha_close.iloc[-1] < ha_open.iloc[-1] and 
          ha_close.iloc[-2] < ha_open.iloc[-2] and 
          portfolio_qty > 0):
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def volume_weighted_macd_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Volume-Weighted MACD Strategy
    """
    max_investment = total_portfolio_value * 0.10
    
    # Calculate volume-weighted price
    vwp = (historical_data['close'] * historical_data['volume']).rolling(window=12).sum() / \
          historical_data['volume'].rolling(window=12).sum()
    
    # Calculate VWMACD
    exp1 = vwp.ewm(span=12, adjust=False).mean()
    exp2 = vwp.ewm(span=26, adjust=False).mean()
    vwmacd = exp1 - exp2
    signal = vwmacd.ewm(span=9, adjust=False).mean()
    
    if (vwmacd.iloc[-1] > signal.iloc[-1] and 
        vwmacd.iloc[-2] <= signal.iloc[-2] and 
        account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif (vwmacd.iloc[-1] < signal.iloc[-1] and 
          vwmacd.iloc[-2] >= signal.iloc[-2] and 
          portfolio_qty > 0):
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def fractal_adaptive_moving_average_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Fractal Adaptive Moving Average (FRAMA) Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 10
    
    # Calculate Fractal Dimension
    def calc_fractal_dimension(high, low, period):
        n1 = (np.log(high.rolling(period).max() - low.rolling(period).min()) - 
              np.log(high - low)).rolling(period).mean()
        n2 = np.log(period) * 0.5
        dimension = 2 - (n1 / n2)
        return dimension
    
    fd = calc_fractal_dimension(historical_data['high'], historical_data['low'], period)
    alpha = np.exp(-4.6 * (fd - 1))
    frama = historical_data['close'].copy()
    
    for i in range(period, len(historical_data)):
        frama.iloc[i] = alpha.iloc[i] * historical_data['close'].iloc[i] + \
                       (1 - alpha.iloc[i]) * frama.iloc[i-1]
    
    if (current_price > frama.iloc[-1] and 
        historical_data['close'].iloc[-2] <= frama.iloc[-2] and 
        account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif (current_price < frama.iloc[-1] and 
          historical_data['close'].iloc[-2] >= frama.iloc[-2] and 
          portfolio_qty > 0):
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def relative_vigor_index_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Relative Vigor Index (RVI) Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 10
    
    # Calculate RVI
    close_open = historical_data['close'] - historical_data['open']
    high_low = historical_data['high'] - historical_data['low']
    
    num = close_open.rolling(period).mean()
    den = high_low.rolling(period).mean()
    
    rvi = num / den
    signal = rvi.rolling(4).mean()
    
    if (rvi.iloc[-1] > signal.iloc[-1] and 
        rvi.iloc[-2] <= signal.iloc[-2] and 
        account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif (rvi.iloc[-1] < signal.iloc[-1] and 
          rvi.iloc[-2] >= signal.iloc[-2] and 
          portfolio_qty > 0):
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def center_of_gravity_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Center of Gravity Oscillator Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 10
    
    # Calculate Center of Gravity
    prices = historical_data['close'].values
    weights = np.arange(1, period + 1)
    cog = np.zeros_like(prices)
    
    for i in range(period-1, len(prices)):
        window = prices[i-period+1:i+1]
        cog[i] = -np.sum(window * weights) / np.sum(window)
    
    cog_series = pd.Series(cog, index=historical_data.index)
    signal = cog_series.rolling(3).mean()
    
    if (cog_series.iloc[-1] > signal.iloc[-1] and 
        cog_series.iloc[-2] <= signal.iloc[-2] and 
        account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif (cog_series.iloc[-1] < signal.iloc[-1] and 
          cog_series.iloc[-2] >= signal.iloc[-2] and 
          portfolio_qty > 0):
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def kaufman_efficiency_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Kaufman Efficiency Ratio Strategy with Adaptive Parameters
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    # Calculate Price Change and Volatility
    price_change = abs(historical_data['close'] - historical_data['close'].shift(period))
    volatility = historical_data['close'].diff().abs().rolling(period).sum()
    
    # Calculate Efficiency Ratio
    efficiency_ratio = price_change / volatility
    
    # Adaptive Parameters
    fast_alpha = 0.6
    slow_alpha = 0.2
    
    # Calculate Adaptive EMA
    alpha = (efficiency_ratio * (fast_alpha - slow_alpha)) + slow_alpha
    adaptive_ema = historical_data['close'].copy()
    
    for i in range(1, len(historical_data)):
        adaptive_ema.iloc[i] = (alpha.iloc[i] * historical_data['close'].iloc[i] + 
                               (1 - alpha.iloc[i]) * adaptive_ema.iloc[i-1])
    
    if current_price > adaptive_ema.iloc[-1] and efficiency_ratio.iloc[-1] > 0.6 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif current_price < adaptive_ema.iloc[-1] and efficiency_ratio.iloc[-1] < 0.3 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def phase_change_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Market Phase Change Detection Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    # Calculate Hilbert Transform
    hilbert = historical_data['close'].diff()
    phase = np.arctan2(hilbert, historical_data['close'])
    
    # Smooth the phase
    smooth_phase = phase.rolling(window=period).mean()
    phase_change = smooth_phase.diff()
    
    # Calculate momentum
    momentum = historical_data['close'].pct_change(period)
    
    if phase_change.iloc[-1] > 0 and momentum.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif phase_change.iloc[-1] < 0 and momentum.iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def volatility_breakout_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Volatility-Based Breakout Strategy
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    # Calculate ATR-based volatility
    high_low = historical_data['high'] - historical_data['low']
    high_close = abs(historical_data['high'] - historical_data['close'].shift())
    low_close = abs(historical_data['low'] - historical_data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    # Calculate volatility bands
    upper_band = historical_data['close'].rolling(period).mean() + (2 * atr)
    lower_band = historical_data['close'].rolling(period).mean() - (2 * atr)
    
    # Volume confirmation
    volume_ma = historical_data['volume'].rolling(period).mean()
    
    if (current_price > upper_band.iloc[-1] and 
        historical_data['volume'].iloc[-1] > 1.5 * volume_ma.iloc[-1] and 
        account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif current_price < lower_band.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def momentum_divergence_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Momentum Divergence Strategy with Multiple Timeframes
    """
    max_investment = total_portfolio_value * 0.10
    short_period = 14
    long_period = 28
    
    # Calculate RSI for multiple timeframes
    def calculate_rsi(data, period):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    short_rsi = calculate_rsi(historical_data['close'], short_period)
    long_rsi = calculate_rsi(historical_data['close'], long_period)
    
    # Detect divergence
    price_trend = historical_data['close'].diff(short_period).iloc[-1]
    rsi_trend = short_rsi.diff(short_period).iloc[-1]
    
    if price_trend < 0 and rsi_trend > 0 and short_rsi.iloc[-1] < 30 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif price_trend > 0 and rsi_trend < 0 and short_rsi.iloc[-1] > 70 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def adaptive_channel_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Adaptive Channel Breakout Strategy with Dynamic Thresholds
    """
    max_investment = total_portfolio_value * 0.10
    base_period = 20
    
    # Calculate volatility-adjusted period
    volatility = historical_data['close'].pct_change().std()
    adaptive_period = int(base_period * (1 + volatility))
    
    # Calculate adaptive channels
    upper_channel = historical_data['high'].rolling(adaptive_period).max()
    lower_channel = historical_data['low'].rolling(adaptive_period).min()
    middle_channel = (upper_channel + lower_channel) / 2
    
    # Calculate channel width
    channel_width = (upper_channel - lower_channel) / middle_channel
    
    if (current_price > upper_channel.iloc[-1] and 
        channel_width.iloc[-1] > channel_width.rolling(base_period).mean().iloc[-1] and 
        account_cash > 0):
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif current_price < lower_channel.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def wavelet_decomposition_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Wavelet-based Trading Strategy using Multi-Scale Analysis
    """
    max_investment = total_portfolio_value * 0.10
    
    # Calculate price differences at multiple scales
    def wavelet_transform(data, levels=3):
        coeffs = []
        current = data
        for _ in range(levels):
            smooth = current.rolling(2).mean()
            detail = current - smooth
            coeffs.append(detail)
            current = smooth
        return coeffs
    
    price_wavelets = wavelet_transform(historical_data['close'])
    trend = price_wavelets[2].rolling(5).mean()
    momentum = price_wavelets[1].rolling(3).mean()
    noise = price_wavelets[0]
    
    if trend.iloc[-1] > 0 and momentum.iloc[-1] > 0 and noise.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif trend.iloc[-1] < 0 and momentum.iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def entropy_flow_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Entropy Flow Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    # Calculate price changes and their probabilities
    returns = historical_data['close'].pct_change()
    bins = np.linspace(returns.min(), returns.max(), 10)
    
    def calculate_entropy(x):
        hist, _ = np.histogram(x, bins=bins, density=True)
        hist = hist[hist > 0]
        return -np.sum(hist * np.log(hist))
    
    entropy = returns.rolling(window).apply(calculate_entropy)
    entropy_ma = entropy.rolling(5).mean()
    
    if entropy.iloc[-1] < entropy_ma.iloc[-1] and returns.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif entropy.iloc[-1] > entropy_ma.iloc[-1] and returns.iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def regime_detection_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Market Regime Detection Strategy using Hidden Markov Model concepts
    """
    max_investment = total_portfolio_value * 0.10
    window = 30
    
    returns = historical_data['close'].pct_change()
    volatility = returns.rolling(window).std()
    momentum = returns.rolling(window).mean()
    
    # Simple regime classification
    def classify_regime(vol, mom):
        if vol > vol.quantile(0.7):
            return 'high_volatility'
        elif mom > mom.quantile(0.7):
            return 'momentum'
        else:
            return 'mean_reversion'
    
    regime = pd.Series(index=historical_data.index)
    regime = pd.Series([classify_regime(volatility.iloc[i], momentum.iloc[i]) 
                       for i in range(len(volatility))])
    
    if regime.iloc[-1] == 'momentum' and momentum.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif (regime.iloc[-1] == 'high_volatility' or momentum.iloc[-1] < 0) and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def spectral_analysis_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Spectral Analysis Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 30
    
    # Calculate FFT components
    prices = historical_data['close'].values
    fft = np.fft.fft(prices[-window:])
    power = np.abs(fft) ** 2
    
    # Get dominant frequencies
    dominant_freq = np.argsort(power[1:window//2])[-3:]
    reconstructed = np.real(np.fft.ifft(fft))
    
    trend = reconstructed[-1] - reconstructed[-2]
    strength = power[dominant_freq].sum() / power[1:window//2].sum()
    
    if trend > 0 and strength > 0.6 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif trend < 0 and strength > 0.6 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def kalman_filter_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Kalman Filter Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    
    # Initialize Kalman Filter parameters
    Q = 1e-5  # Process variance
    R = 0.01  # Measurement variance
    P = 1.0   # Initial estimation error covariance
    K = 0.0   # Initial Kalman Gain
    x = historical_data['close'].iloc[0]  # Initial estimate
    
    estimates = []
    for price in historical_data['close']:
        # Prediction
        P = P + Q
        
        # Update
        K = P / (P + R)
        x = x + K * (price - x)
        P = (1 - K) * P
        
        estimates.append(x)
    
    kalman_series = pd.Series(estimates, index=historical_data.index)
    kalman_slope = kalman_series.diff()
    
    if current_price > kalman_series.iloc[-1] and kalman_slope.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif current_price < kalman_series.iloc[-1] and kalman_slope.iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def particle_filter_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Particle Filter Strategy for Non-Linear Price Dynamics
    """
    max_investment = total_portfolio_value * 0.10
    n_particles = 100
    
    returns = historical_data['close'].pct_change().dropna()
    
    # Generate particles
    particles = np.random.normal(returns.mean(), returns.std(), (len(returns), n_particles))
    weights = np.ones(n_particles) / n_particles
    
    # Update particle weights based on likelihood
    for i in range(len(returns)):
        weights *= np.exp(-0.5 * ((returns.iloc[i] - particles[i]) ** 2))
        weights /= weights.sum()
        
        # Resample if effective particle size is too small
        if 1.0 / (weights ** 2).sum() < n_particles / 2:
            indices = np.random.choice(n_particles, size=n_particles, p=weights)
            particles = particles[:, indices]
            weights = np.ones(n_particles) / n_particles
    
    predicted_return = (particles[-1] * weights).sum()
    prediction_std = np.sqrt(((particles[-1] - predicted_return) ** 2 * weights).sum())
    
    if predicted_return > prediction_std and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif predicted_return < -prediction_std and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def quantum_oscillator_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Quantum Oscillator Strategy using Wave Function Concepts
    """
    max_investment = total_portfolio_value * 0.10
    period = 20
    
    # Calculate price momentum and volatility
    returns = historical_data['close'].pct_change()
    momentum = returns.rolling(period).mean()
    volatility = returns.rolling(period).std()
    
    # Create quantum-inspired oscillator
    psi = np.exp(-1j * np.pi * momentum / volatility)
    probability = np.abs(psi) ** 2
    phase = np.angle(psi)
    
    # Generate trading signals based on wave function collapse
    if probability.iloc[-1] > 0.7 and phase.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif probability.iloc[-1] > 0.7 and phase.iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def topological_data_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Topological Data Analysis Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_persistence(data):
        # Simplified persistence calculation
        peaks = (data > data.shift(1)) & (data > data.shift(-1))
        valleys = (data < data.shift(1)) & (data < data.shift(-1))
        return peaks.sum() - valleys.sum()
    
    # Calculate topological features
    price_topology = historical_data['close'].rolling(window).apply(calculate_persistence)
    volume_topology = historical_data['volume'].rolling(window).apply(calculate_persistence)
    
    if price_topology.iloc[-1] > 0 and volume_topology.iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif price_topology.iloc[-1] < 0 and volume_topology.iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def neural_flow_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Neural Flow Strategy using Price Action Dynamics
    """
    max_investment = total_portfolio_value * 0.10
    window = 30
    
    # Calculate price flow features
    price_diff = historical_data['close'].diff()
    flow = price_diff.rolling(window).apply(lambda x: np.sum(np.sign(x) * np.log1p(np.abs(x))))
    
    # Calculate activation
    activation = np.tanh(flow / flow.rolling(window).std())
    
    # Generate signals based on neural flow dynamics
    if activation.iloc[-1] > 0.5 and activation.diff().iloc[-1] > 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif activation.iloc[-1] < -0.5 and activation.diff().iloc[-1] < 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def fractal_dimension_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Fractal Dimension Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_fractal_dimension(series):
        # Higuchi Fractal Dimension
        lags = range(2, 9)
        lengths = []
        for lag in lags:
            length = 0
            for i in range(lag):
                subset = series[i::lag]
                length += sum(abs(subset[1:] - subset[:-1]))
            length = length * (len(series) - 1) / (lag * lag * (len(series) // lag))
            lengths.append(np.log(length))
        
        # Calculate dimension from slope
        dimension = -np.polyfit(np.log(lags), lengths, 1)[0]
        return dimension
    
    # Calculate fractal dimension over rolling windows
    fractal_dim = historical_data['close'].rolling(window).apply(calculate_fractal_dimension)
    dim_sma = fractal_dim.rolling(5).mean()
    
    if fractal_dim.iloc[-1] < dim_sma.iloc[-1] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif fractal_dim.iloc[-1] > dim_sma.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def information_flow_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Information Flow Trading Strategy using Transfer Entropy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_transfer_entropy(source, target, delay=1):
        source_past = source[:-delay]
        target_future = target[delay:]
        target_past = target[:-delay]
        
        # Joint and marginal probabilities
        joint_counts = np.histogram2d(source_past, target_future)[0]
        marginal_counts = np.histogram(target_past)[0]
        
        # Normalize to get probabilities
        joint_prob = joint_counts / np.sum(joint_counts)
        marginal_prob = marginal_counts / np.sum(marginal_counts)
        
        # Calculate transfer entropy
        entropy = np.sum(joint_prob * np.log2(joint_prob / marginal_prob))
        return entropy
    
    # Calculate information flow between price and volume
    price_changes = historical_data['close'].pct_change()
    volume_changes = historical_data['volume'].pct_change()
    
    info_flow = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        info_flow.iloc[i] = calculate_transfer_entropy(
            volume_changes.iloc[i-window:i],
            price_changes.iloc[i-window:i]
        )
    
    if info_flow.iloc[-1] > info_flow.mean() + info_flow.std() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif info_flow.iloc[-1] < info_flow.mean() - info_flow.std() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def manifold_learning_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Manifold Learning Strategy using Local Linear Embedding
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    n_neighbors = 10
    
    def local_linear_embedding(data, n_components=2):
        # Calculate pairwise distances
        distances = np.zeros((len(data), len(data)))
        for i in range(len(data)):
            for j in range(len(data)):
                distances[i,j] = np.sum((data[i] - data[j])**2)
        
        # Find nearest neighbors
        neighbors = np.argsort(distances, axis=1)[:, 1:n_neighbors+1]
        
        # Calculate weights
        weights = np.zeros((len(data), n_neighbors))
        for i in range(len(data)):
            Z = data[neighbors[i]] - data[i]
            C = np.dot(Z, Z.T)
            weights[i] = np.linalg.solve(C + np.eye(n_neighbors)*1e-3, np.ones(n_neighbors))
            weights[i] /= np.sum(weights[i])
        
        return weights.flatten()
    
    # Prepare feature matrix
    features = np.column_stack([
        historical_data['close'].rolling(5).mean(),
        historical_data['volume'].rolling(5).mean(),
        historical_data['high'].rolling(5).max(),
        historical_data['low'].rolling(5).min()
    ])
    
    # Calculate manifold coordinates
    manifold_coords = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        weights = local_linear_embedding(features[i-window:i])
        manifold_coords.iloc[i] = np.mean(weights)
    
    if manifold_coords.iloc[-1] > manifold_coords.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif manifold_coords.iloc[-1] < manifold_coords.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def symbolic_dynamics_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Symbolic Dynamics Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def symbolize_series(series, n_symbols=4):
        # Convert continuous series to symbolic sequence
        bins = np.linspace(series.min(), series.max(), n_symbols+1)
        return np.digitize(series, bins[1:-1])
    
    # Calculate symbolic sequences
    returns = historical_data['close'].pct_change()
    symbols = symbolize_series(returns)
    
    # Calculate transition probabilities
    def get_transition_prob(symbols, current_state):
        transitions = symbols[symbols[:-1] == current_state]
        if len(transitions) > 0:
            return np.mean(transitions)
        return 0
    
    current_symbol = symbols.iloc[-1]
    transition_prob = get_transition_prob(symbols, current_symbol)
    
    if transition_prob > 0.6 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif transition_prob < 0.4 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def persistent_homology_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Persistent Homology Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_betti_numbers(data):
        # Simplified persistence calculation using price levels
        sorted_data = np.sort(data)
        birth_times = sorted_data[:-1]
        death_times = sorted_data[1:]
        persistence = death_times - birth_times
        return np.sum(persistence)
    
    # Calculate topological features
    betti_numbers = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        betti_numbers.iloc[i] = calculate_betti_numbers(historical_data['close'].iloc[i-window:i])
    
    betti_sma = betti_numbers.rolling(5).mean()
    
    if betti_numbers.iloc[-1] > betti_sma.iloc[-1] and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif betti_numbers.iloc[-1] < betti_sma.iloc[-1] and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def ergodic_measure_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Ergodic Measure Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_ergodic_measure(series):
        # Calculate time average and space average
        time_avg = series.mean()
        space_avg = series.expanding().mean().iloc[-1]
        
        # Calculate ergodic measure
        return np.abs(time_avg - space_avg)
    
    returns = historical_data['close'].pct_change()
    ergodic_measure = pd.Series(index=historical_data.index)
    
    for i in range(window, len(historical_data)):
        ergodic_measure.iloc[i] = calculate_ergodic_measure(returns.iloc[i-window:i])
    
    if ergodic_measure.iloc[-1] < ergodic_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif ergodic_measure.iloc[-1] > ergodic_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def recurrence_network_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Recurrence Network Analysis Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    threshold = 0.1
    
    def build_recurrence_network(data):
        # Create distance matrix
        dist_matrix = np.zeros((len(data), len(data)))
        for i in range(len(data)):
            for j in range(len(data)):
                dist_matrix[i,j] = abs(data[i] - data[j])
        
        # Create recurrence matrix
        recurrence_matrix = dist_matrix < threshold
        
        # Calculate network metrics
        degree = np.sum(recurrence_matrix, axis=1)
        clustering = np.mean(degree)
        
        return clustering
    
    # Calculate network metrics over time
    network_measure = pd.Series(index=historical_data.index)
    returns = historical_data['close'].pct_change()
    
    for i in range(window, len(historical_data)):
        network_measure.iloc[i] = build_recurrence_network(returns.iloc[i-window:i])
    
    if network_measure.iloc[-1] > network_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif network_measure.iloc[-1] < network_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def permutation_entropy_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Permutation Entropy Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    order = 3
    
    def calculate_permutation_entropy(data, order):
        n = len(data)
        permutations = np.array(list(itertools.permutations(range(order))))
        counts = np.zeros(len(permutations))
        
        for i in range(n - order + 1):
            # Get the ordinal pattern
            pattern = np.argsort(data[i:i+order])
            # Find which permutation it matches
            for j, p in enumerate(permutations):
                if np.all(pattern == p):
                    counts[j] += 1
                    break
        
        # Calculate entropy
        probs = counts[counts > 0] / sum(counts)
        return -np.sum(probs * np.log2(probs))
    
    entropy = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        entropy.iloc[i] = calculate_permutation_entropy(
            historical_data['close'].iloc[i-window:i].values, 
            order
        )
    
    if entropy.iloc[-1] < entropy.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif entropy.iloc[-1] > entropy.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def visibility_graph_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Natural Visibility Graph Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_visibility_degree(data):
        n = len(data)
        adjacency_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                visible = True
                for k in range(i+1, j):
                    if (data[k] >= data[i] + (data[j] - data[i]) * (k-i)/(j-i)):
                        visible = False
                        break
                if visible:
                    adjacency_matrix[i,j] = adjacency_matrix[j,i] = 1
        
        return np.sum(adjacency_matrix, axis=1)
    
    visibility_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        degrees = calculate_visibility_degree(historical_data['close'].iloc[i-window:i].values)
        visibility_measure.iloc[i] = np.mean(degrees)
    
    if visibility_measure.iloc[-1] > visibility_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif visibility_measure.iloc[-1] < visibility_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def multiscale_entropy_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Multiscale Entropy Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 30
    scales = [1, 2, 3, 4, 5]
    
    def sample_entropy(data, m=2, r=0.2):
        n = len(data)
        template_matches = np.zeros(2)
        
        for i in range(n - m):
            template = data[i:i+m]
            for j in range(i+1, n-m):
                if np.max(np.abs(template - data[j:j+m])) < r:
                    template_matches[0] += 1
                    if i < n-m-1 and np.max(np.abs(data[i:i+m+1] - data[j:j+m+1])) < r:
                        template_matches[1] += 1
        
        return -np.log(template_matches[1] / template_matches[0])
    
    def coarse_grain(data, scale):
        return np.array([np.mean(data[i:i+scale]) for i in range(0, len(data)-scale+1, scale)])
    
    entropy_measure = pd.Series(index=historical_data.index)
    returns = historical_data['close'].pct_change().dropna()
    
    for i in range(window, len(historical_data)):
        multiscale_entropy = []
        for scale in scales:
            coarse_grained = coarse_grain(returns.iloc[i-window:i].values, scale)
            multiscale_entropy.append(sample_entropy(coarse_grained))
        entropy_measure.iloc[i] = np.mean(multiscale_entropy)
    
    if entropy_measure.iloc[-1] < entropy_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif entropy_measure.iloc[-1] > entropy_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def ordinal_pattern_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Ordinal Pattern Transition Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    pattern_length = 3
    
    def get_ordinal_pattern(data):
        return tuple(np.argsort(data))
    
    def calculate_transition_probability(patterns):
        transitions = {}
        for i in range(len(patterns)-1):
            current = patterns[i]
            next_pattern = patterns[i+1]
            if current not in transitions:
                transitions[current] = {}
            if next_pattern not in transitions[current]:
                transitions[current][next_pattern] = 0
            transitions[current][next_pattern] += 1
        
        # Normalize probabilities
        for current in transitions:
            total = sum(transitions[current].values())
            for next_pattern in transitions[current]:
                transitions[current][next_pattern] /= total
        
        return transitions
    
    patterns = []
    for i in range(len(historical_data) - pattern_length + 1):
        pattern = get_ordinal_pattern(historical_data['close'].iloc[i:i+pattern_length].values)
        patterns.append(pattern)
    
    transitions = calculate_transition_probability(patterns)
    current_pattern = patterns[-1]
    
    if current_pattern in transitions:
        most_likely_next = max(transitions[current_pattern].items(), key=lambda x: x[1])[0]
        if most_likely_next[-1] > current_pattern[-1] and account_cash > 0:
            quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
            if quantity_to_buy > 0:
                return ('buy', quantity_to_buy, ticker)
        elif most_likely_next[-1] < current_pattern[-1] and portfolio_qty > 0:
            quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
            return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def lyapunov_exponent_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Lyapunov Exponent Trading Strategy for Chaos Detection
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_lyapunov(data, tau=1, m=2):
        n = len(data)
        divergence = np.zeros(n)
        
        for i in range(n-tau):
            distances = np.abs(data[i+tau] - data[i])
            if distances > 0:
                divergence[i] = np.log(distances)
                
        lyap = np.mean(divergence[divergence != 0])
        return lyap
    
    returns = historical_data['close'].pct_change().dropna()
    lyapunov = pd.Series(index=historical_data.index)
    
    for i in range(window, len(historical_data)):
        lyapunov.iloc[i] = calculate_lyapunov(returns.iloc[i-window:i].values)
    
    if lyapunov.iloc[-1] < 0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif lyapunov.iloc[-1] > 0 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def kolmogorov_complexity_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Kolmogorov Complexity Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def estimate_complexity(data):
        # Convert to binary string using mean as threshold
        binary = ''.join(['1' if x > np.mean(data) else '0' for x in data])
        compressed = len(zlib.compress(binary.encode()))
        return compressed / len(binary)
    
    complexity = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        complexity.iloc[i] = estimate_complexity(historical_data['close'].iloc[i-window:i].values)
    
    if complexity.iloc[-1] < complexity.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif complexity.iloc[-1] > complexity.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def wasserstein_distance_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Wasserstein Distance Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_wasserstein(dist1, dist2):
        # Sort distributions
        dist1_sorted = np.sort(dist1)
        dist2_sorted = np.sort(dist2)
        
        # Calculate empirical CDFs
        n = len(dist1_sorted)
        cdf1 = np.arange(1, n + 1) / n
        cdf2 = np.arange(1, n + 1) / n
        
        # Calculate Wasserstein distance
        return np.sum(np.abs(dist1_sorted - dist2_sorted))
    
    distances = pd.Series(index=historical_data.index)
    returns = historical_data['close'].pct_change().dropna()
    
    for i in range(2*window, len(historical_data)):
        dist1 = returns.iloc[i-2*window:i-window]
        dist2 = returns.iloc[i-window:i]
        distances.iloc[i] = calculate_wasserstein(dist1, dist2)
    
    if distances.iloc[-1] < distances.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif distances.iloc[-1] > distances.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def persistent_homology_landscape_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Persistent Homology Landscape Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_persistence_landscape(data):
        # Simplified persistence landscape calculation
        sorted_data = np.sort(data)
        peaks = []
        
        for i in range(1, len(sorted_data)-1):
            if sorted_data[i] > sorted_data[i-1] and sorted_data[i] > sorted_data[i+1]:
                peaks.append((i, sorted_data[i]))
        
        return len(peaks)
    
    landscape_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        landscape_measure.iloc[i] = calculate_persistence_landscape(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if landscape_measure.iloc[-1] > landscape_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif landscape_measure.iloc[-1] < landscape_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def diffusion_map_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Diffusion Map Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    epsilon = 0.1
    
    def compute_diffusion_coords(data):
        # Compute pairwise distances
        dist_matrix = np.zeros((len(data), len(data)))
        for i in range(len(data)):
            for j in range(len(data)):
                dist_matrix[i,j] = (data[i] - data[j])**2
        
        # Compute kernel matrix
        kernel = np.exp(-dist_matrix / epsilon)
        
        # Normalize
        row_sums = kernel.sum(axis=1)
        normalized_kernel = kernel / row_sums[:, np.newaxis]
        
        # First non-trivial eigenvector
        eigenvals, eigenvecs = np.linalg.eigh(normalized_kernel)
        return eigenvecs[:, -2]
    
    diffusion_coords = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        coords = compute_diffusion_coords(historical_data['close'].iloc[i-window:i].values)
        diffusion_coords.iloc[i] = np.mean(coords)
    
    if diffusion_coords.iloc[-1] > diffusion_coords.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif diffusion_coords.iloc[-1] < diffusion_coords.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def topological_pressure_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Topological Pressure Trading Strategy using Dynamic Systems Theory
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_topological_pressure(data):
        # Compute symbolic dynamics
        symbols = np.sign(np.diff(data))
        # Calculate word frequencies
        word_length = 3
        words = [''.join(map(str, symbols[i:i+word_length])) 
                for i in range(len(symbols)-word_length+1)]
        frequencies = pd.Series(words).value_counts() / len(words)
        # Calculate pressure
        return -np.sum(frequencies * np.log(frequencies))
    
    pressure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        pressure.iloc[i] = calculate_topological_pressure(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if pressure.iloc[-1] > pressure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif pressure.iloc[-1] < pressure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def persistent_cohomology_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Persistent Cohomology Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def compute_cohomology_features(data):
        # Create time-delay embedding
        tau = 2
        embedding_dim = 3
        embedding = np.array([data[i:i+embedding_dim*tau:tau] 
                            for i in range(len(data)-embedding_dim*tau+1)])
        
        # Calculate pairwise distances
        distances = np.zeros((len(embedding), len(embedding)))
        for i in range(len(embedding)):
            for j in range(len(embedding)):
                distances[i,j] = np.linalg.norm(embedding[i] - embedding[j])
        
        return np.mean(distances)
    
    cohomology = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        cohomology.iloc[i] = compute_cohomology_features(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if cohomology.iloc[-1] < cohomology.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif cohomology.iloc[-1] > cohomology.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def spectral_clustering_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Spectral Clustering Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    n_clusters = 2
    
    def perform_spectral_clustering(data):
        # Create similarity matrix
        similarity = np.zeros((len(data), len(data)))
        for i in range(len(data)):
            for j in range(len(data)):
                similarity[i,j] = np.exp(-np.abs(data[i] - data[j]))
        
        # Compute Laplacian
        degree = np.sum(similarity, axis=1)
        laplacian = np.diag(degree) - similarity
        
        # Get eigenvectors
        eigenvals, eigenvecs = np.linalg.eigh(laplacian)
        return eigenvecs[:, 1]  # Second smallest eigenvector
    
    cluster_features = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        cluster_features.iloc[i] = np.mean(perform_spectral_clustering(
            historical_data['close'].iloc[i-window:i].values
        ))
    
    if cluster_features.iloc[-1] > cluster_features.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif cluster_features.iloc[-1] < cluster_features.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def optimal_transport_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Optimal Transport Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def compute_transport_cost(source, target):
        # Simplified Optimal Transport calculation
        source_sorted = np.sort(source)
        target_sorted = np.sort(target)
        return np.sum(np.abs(source_sorted - target_sorted))
    
    transport_costs = pd.Series(index=historical_data.index)
    returns = historical_data['close'].pct_change()
    
    for i in range(2*window, len(historical_data)):
        source = returns.iloc[i-2*window:i-window]
        target = returns.iloc[i-window:i]
        transport_costs.iloc[i] = compute_transport_cost(source, target)
    
    if transport_costs.iloc[-1] < transport_costs.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif transport_costs.iloc[-1] > transport_costs.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def sheaf_cohomology_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Sheaf Cohomology Trading Strategy
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def compute_sheaf_features(data):
        # Create overlapping intervals
        intervals = [(i, i+5) for i in range(len(data)-5)]
        
        # Calculate local features
        local_means = [np.mean(data[start:end]) for start, end in intervals]
        local_vars = [np.var(data[start:end]) for start, end in intervals]
        
        # Compute consistency measure
        consistency = np.mean([abs(local_means[i] - local_means[i+1]) 
                             for i in range(len(local_means)-1)])
        return consistency
    
    sheaf_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        sheaf_measure.iloc[i] = compute_sheaf_features(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if sheaf_measure.iloc[-1] < sheaf_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif sheaf_measure.iloc[-1] > sheaf_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def algebraic_topology_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Algebraic Topology Trading Strategy using Simplicial Complexes
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def build_simplicial_complex(data):
        # Create distance matrix
        distances = np.zeros((len(data), len(data)))
        for i in range(len(data)):
            for j in range(len(data)):
                distances[i,j] = abs(data[i] - data[j])
        
        # Build 1-skeleton
        epsilon = np.median(distances)
        adjacency = distances < epsilon
        
        # Count connected components
        return np.sum(adjacency)
    
    topology_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        topology_measure.iloc[i] = build_simplicial_complex(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if topology_measure.iloc[-1] > topology_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif topology_measure.iloc[-1] < topology_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def morse_theory_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Morse Theory Trading Strategy using Critical Points
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def find_critical_points(data):
        # Find local maxima and minima
        diff = np.diff(data)
        sign_changes = np.diff(np.sign(diff))
        critical_points = np.where(sign_changes != 0)[0] + 1
        
        # Calculate Morse index
        morse_index = sum(diff[critical_points-1] > 0)
        return morse_index
    
    morse_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        morse_measure.iloc[i] = find_critical_points(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if morse_measure.iloc[-1] < morse_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif morse_measure.iloc[-1] > morse_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def category_theory_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Category Theory Trading Strategy using Functorial Analysis
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def compute_functorial_features(data):
        # Create time series categories
        short_term = data[-5:]
        medium_term = data[-10:]
        long_term = data[-20:]
        
        # Calculate morphisms between time scales
        short_to_medium = np.corrcoef(short_term, medium_term[-5:])[0,1]
        medium_to_long = np.corrcoef(medium_term, long_term[-10:])[0,1]
        
        # Measure functorial consistency
        return abs(short_to_medium - medium_to_long)
    
    category_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        category_measure.iloc[i] = compute_functorial_features(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if category_measure.iloc[-1] < category_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif category_measure.iloc[-1] > category_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def symplectic_geometry_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Symplectic Geometry Trading Strategy using Phase Space Analysis
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def compute_symplectic_features(data):
        # Create phase space coordinates (price, momentum)
        price = data
        momentum = np.diff(data, prepend=data[0])
        
        # Calculate symplectic form
        omega = np.sum(price[:-1] * momentum[1:] - price[1:] * momentum[:-1])
        return omega
    
    symplectic_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        symplectic_measure.iloc[i] = compute_symplectic_features(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if symplectic_measure.iloc[-1] > symplectic_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif symplectic_measure.iloc[-1] < symplectic_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def differential_forms_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Differential Forms Trading Strategy using Exterior Calculus
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def compute_differential_forms(data):
        # Create 1-forms from price differences
        d_price = np.diff(data)
        
        # Create 2-forms from wedge products
        wedge_product = np.outer(d_price[:-1], d_price[1:])
        
        # Calculate exterior derivative
        return np.sum(np.triu(wedge_product))
    
    differential_measure = pd.Series(index=historical_data.index)
    for i in range(window, len(historical_data)):
        differential_measure.iloc[i] = compute_differential_forms(
            historical_data['close'].iloc[i-window:i].values
        )
    
    if differential_measure.iloc[-1] > differential_measure.mean() and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
    
    elif differential_measure.iloc[-1] < differential_measure.mean() and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
    
    return ('hold', portfolio_qty, ticker)

def renaissance_medallion_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Inspired by Jim Simons' Renaissance Technologies Medallion Fund
    Known for: Statistical arbitrage and pattern recognition
    Returns: 66% annual returns (before fees) over several decades
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    # Multi-factor statistical arbitrage
    def compute_statistical_signals(data):
        # Price momentum factor
        momentum = data['close'].pct_change(5)
        
        # Mean reversion factor
        zscore = (data['close'] - data['close'].rolling(window).mean()) / data['close'].rolling(window).std()
        
        # Volume-price divergence
        volume_price_correlation = data['volume'].rolling(window).corr(data['close'])
        
        # Combine signals using adaptive weights
        signal = (0.4 * momentum + 0.3 * -zscore + 0.3 * volume_price_correlation).iloc[-1]
        return signal
    
    signal = compute_statistical_signals(historical_data)
    
    if signal > 0.5 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif signal < -0.5 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def soros_reflexivity_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Inspired by George Soros' Theory of Reflexivity
    Known for: Breaking the Bank of England, $1B profit in a single day
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_reflexivity_indicator(data):
        # Price trend strength
        trend = data['close'].pct_change(window).iloc[-1]
        
        # Volume confirmation of trend
        volume_trend = data['volume'].pct_change(window).iloc[-1]
        
        # Market sentiment proxy (price acceleration)
        sentiment = data['close'].pct_change().diff().rolling(window).mean().iloc[-1]
        
        return trend * volume_trend * np.sign(sentiment)
    
    reflexivity_signal = calculate_reflexivity_indicator(historical_data)
    
    if reflexivity_signal > 0.02 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif reflexivity_signal < -0.02 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def ptj_global_macro_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Inspired by Paul Tudor Jones' Global Macro Approach
    Known for: Predicting Black Monday, 200% returns in 1987
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_macro_score(data):
        # Price momentum across multiple timeframes
        mom_short = data['close'].pct_change(5).iloc[-1]
        mom_medium = data['close'].pct_change(10).iloc[-1]
        mom_long = data['close'].pct_change(20).iloc[-1]
        
        # Volatility breakout signal
        volatility = data['close'].pct_change().rolling(window).std().iloc[-1]
        vol_signal = 1 if volatility > volatility * 2 else 0
        
        # Combined signal with momentum confluence
        return (mom_short + mom_medium + mom_long) * (1 + vol_signal)
    
    macro_signal = calculate_macro_score(historical_data)
    
    if macro_signal > 0.03 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif macro_signal < -0.03 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def druckenmiller_momentum_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Inspired by Stanley Druckenmiller's Momentum Approach
    Known for: 30% average annual returns over 30 years
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_momentum_strength(data):
        # Trend strength across timeframes
        trends = [data['close'].pct_change(t).iloc[-1] for t in [5, 10, 20, 40]]
        trend_alignment = np.sum([1 if t > 0 else -1 for t in trends])
        
        # Volume-weighted momentum
        volume_momentum = data['close'].pct_change() * data['volume']
        vol_signal = volume_momentum.rolling(window).mean().iloc[-1]
        
        return trend_alignment * vol_signal
    
    momentum_signal = calculate_momentum_strength(historical_data)
    
    if momentum_signal > 0.5 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif momentum_signal < -0.5 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)

def lynch_growth_strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value):
    """
    Inspired by Peter Lynch's Growth at Reasonable Price
    Known for: 29.2% average annual returns at Magellan Fund
    """
    max_investment = total_portfolio_value * 0.10
    window = 20
    
    def calculate_growth_signal(data):
        # Price momentum quality
        returns = data['close'].pct_change()
        growth_quality = returns.rolling(window).mean() / returns.rolling(window).std()
        
        # Volume trend confirmation
        volume_trend = data['volume'].rolling(window).mean().pct_change()
        
        # Combined growth signal
        return growth_quality.iloc[-1] * (1 + volume_trend.iloc[-1])
    
    growth_signal = calculate_growth_signal(historical_data)
    
    if growth_signal > 1.0 and account_cash > 0:
        quantity_to_buy = min(int(max_investment // current_price), int(account_cash // current_price))
        if quantity_to_buy > 0:
            return ('buy', quantity_to_buy, ticker)
            
    elif growth_signal < -0.5 and portfolio_qty > 0:
        quantity_to_sell = min(portfolio_qty, max(1, int(portfolio_qty * 0.5)))
        return ('sell', quantity_to_sell, ticker)
        
    return ('hold', portfolio_qty, ticker)