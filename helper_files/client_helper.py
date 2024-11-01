# client_helper.py

from pymongo import MongoClient
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import logging
import yfinance as yf
from strategies.trading_strategies_v2 import (  
   rsi_strategy, bollinger_bands_strategy, momentum_strategy, mean_reversion_strategy,  
   triple_moving_average_strategy, volume_price_trend_strategy, keltner_channel_strategy,  
   dual_thrust_strategy, adaptive_momentum_strategy, hull_moving_average_strategy,  
   elder_ray_strategy, chande_momentum_strategy, dema_strategy, price_channel_strategy,  
   mass_index_strategy, vortex_indicator_strategy, aroon_strategy, ultimate_oscillator_strategy,  
   trix_strategy, kst_strategy, psar_strategy, stochastic_momentum_strategy,  
   williams_vix_fix_strategy, conners_rsi_strategy, dpo_strategy, fisher_transform_strategy,  
   ehlers_fisher_strategy, schaff_trend_cycle_strategy, rainbow_oscillator_strategy,  
   heikin_ashi_strategy, volume_weighted_macd_strategy, fractal_adaptive_moving_average_strategy,  
   relative_vigor_index_strategy, center_of_gravity_strategy, kauffman_efficiency_strategy,  
   phase_change_strategy, volatility_breakout_strategy, momentum_divergence_strategy,  
   adaptive_channel_strategy, wavelet_decomposition_strategy, entropy_flow_strategy,  
   bollinger_band_width_strategy, commodity_channel_index_strategy, force_index_strategy,  
   ichimoku_cloud_strategy, klinger_oscillator_strategy, money_flow_index_strategy,  
   on_balance_volume_strategy, stochastic_oscillator_strategy, euler_fibonacci_zone_strategy  
)

strategies = [rsi_strategy, bollinger_bands_strategy, momentum_strategy, mean_reversion_strategy,  
   triple_moving_average_strategy, volume_price_trend_strategy, keltner_channel_strategy,  
   dual_thrust_strategy, adaptive_momentum_strategy, hull_moving_average_strategy,  
   elder_ray_strategy, chande_momentum_strategy, dema_strategy, price_channel_strategy,  
   mass_index_strategy, vortex_indicator_strategy, aroon_strategy, ultimate_oscillator_strategy,  
   trix_strategy, kst_strategy, psar_strategy, stochastic_momentum_strategy,  
   williams_vix_fix_strategy, conners_rsi_strategy, dpo_strategy, fisher_transform_strategy,  
   ehlers_fisher_strategy, schaff_trend_cycle_strategy, rainbow_oscillator_strategy,  
   heikin_ashi_strategy, volume_weighted_macd_strategy, fractal_adaptive_moving_average_strategy,  
   relative_vigor_index_strategy, center_of_gravity_strategy, kauffman_efficiency_strategy,  
   phase_change_strategy, volatility_breakout_strategy, momentum_divergence_strategy,  
   adaptive_channel_strategy, wavelet_decomposition_strategy, entropy_flow_strategy,  
   bollinger_band_width_strategy, commodity_channel_index_strategy, force_index_strategy,  
   ichimoku_cloud_strategy, klinger_oscillator_strategy, money_flow_index_strategy,  
   on_balance_volume_strategy, stochastic_oscillator_strategy, euler_fibonacci_zone_strategy]

# MongoDB connection helper
def connect_to_mongo(mongo_url):
    """Connect to MongoDB and return the client."""
    return MongoClient(mongo_url)

# Helper to place an order
def place_order(trading_client, symbol, side, qty, mongo_url):
    """
    Place a market order and log the order to MongoDB.

    :param trading_client: The Alpaca trading client instance
    :param symbol: The stock symbol to trade
    :param side: Order side (OrderSide.BUY or OrderSide.SELL)
    :param qty: Quantity to trade
    :param mongo_url: MongoDB connection URL
    :return: Order result from Alpaca API
    """
    market_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    order = trading_client.submit_order(market_order_data)
    qty = round(qty, 3)

    # Log trade details to MongoDB
    mongo_client = connect_to_mongo(mongo_url)
    db = mongo_client.trades
    db.paper.insert_one({
        'symbol': symbol,
        'qty': qty,
        'side': side.name,
        'time_in_force': TimeInForce.DAY.name,
        'time': datetime.now()
    })
    mongo_client.close()

    #Track assets as well
    db = mongo_client.trades
    assets = db.assets
    
    
    return order

# Helper to retrieve NASDAQ-100 tickers from MongoDB
def get_ndaq_tickers(mongo_url):
    """
    Connects to MongoDB and retrieves NASDAQ-100 tickers.

    :param mongo_url: MongoDB connection URL
    :return: List of NASDAQ-100 ticker symbols.
    """
    mongo_client = connect_to_mongo(mongo_url)
    tickers = [stock['symbol'] for stock in mongo_client.stock_list.ndaq100_tickers.find()]
    mongo_client.close()
    return tickers

# Market status checker helper
def market_status(polygon_client):
    """
    Check market status using the Polygon API.

    :param polygon_client: An instance of the Polygon RESTClient
    :return: Current market status ('open', 'early_hours', 'closed')
    """
    try:
        status = polygon_client.get_market_status()
        if status.exchanges.nasdaq == "open" and status.exchanges.nyse == "open":
            return "open"
        elif status.early_hours:
            return "early_hours"
        else:
            return "closed"
    except Exception as e:
        logging.error(f"Error retrieving market status: {e}")
        return "error"

# Helper to get latest price
def get_latest_price(ticker):  
   """  
   Fetch the latest price for a given stock ticker using yfinance.  
  
   :param ticker: The stock ticker symbol  
   :return: The latest price of the stock  
   """  
   try:  
      ticker_yahoo = yf.Ticker(ticker)  
      data = ticker_yahoo.history(period="1d")  
      return round(data['Close'].iloc[-1], 2)  
   except Exception as e:  
      logging.error(f"Error fetching latest price for {ticker}: {e}")  
      return None