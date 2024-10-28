from polygon import RESTClient
from config import POLYGON_API_KEY, FINANCIAL_PREP_API_KEY, MONGO_DB_USER, MONGO_DB_PASS, API_KEY, API_SECRET, BASE_URL
import json
import certifi
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from pymongo import MongoClient
import time
from datetime import datetime, timedelta
import alpaca
from alpaca.trading.client import TradingClient
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.stream import TradingStream
from alpaca.data.live.stock import StockDataStream
from alpaca.data.requests import (
    StockBarsRequest,
    StockTradesRequest,
    StockQuotesRequest
)
from alpaca.trading.requests import (
    GetAssetsRequest, 
    MarketOrderRequest, 
    LimitOrderRequest, 
    StopOrderRequest, 
    StopLimitOrderRequest, 
    TakeProfitRequest, 
    StopLossRequest, 
    TrailingStopOrderRequest, 
    GetOrdersRequest, 
    ClosePositionRequest
)
from alpaca.trading.enums import ( 
    AssetStatus, 
    AssetExchange, 
    OrderSide, 
    OrderType, 
    TimeInForce, 
    OrderClass, 
    QueryOrderStatus
)
from alpaca.common.exceptions import APIError
import strategies.trading_strategies_v2 as trading_strategies
import math
import yfinance as yf
import logging
from collections import Counter
from trading_client import market_status
import helper_files.client_helper
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
from datetime import datetime  
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
   on_balance_volume_strategy, stochastic_oscillator_strategy, euler_fibonacci_zone_strategy   
   ]  
# Connect to MongoDB  
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"

def insert_rank_to_coefficient(i):
    """
    currently i is at 50
    next i is at 51
    """
    client = MongoClient(mongo_url)  
    db = client.trading_simulator 
    collections  = db.rank_to_coefficient
    e = math.e
    rate = (e**e)/(e**2) - 1
    coefficient = rate**(2 * i)
    collections.insert_one(
        {f'{i}' : coefficient

        }
    )
    client.close()

  
  
def initialize_rank():  
   client = MongoClient(mongo_url)  
   db = client.trading_simulator  
   collections = db.algorithm_holdings  
    
   initialization_date = datetime.now()  
  
   
   for strategy in strategies:  
        strategy_name = strategy.__name__ 
        print(strategy_name)
        collections = db.algorithm_holdings 
        collections.insert_one({  
            "strategy": strategy_name,  
            "holdings": {},  
            "amount_cash": 50000,  
            "initialized_date": initialization_date,  
            "total_trades": 0,  
            "successful_trades": 0,
            "neutral_trades": 0,
            "failed_trades": 0,  
            "current_portfolio_value": 50000,  
            "last_updated": initialization_date  
        })  
    
        collections = db.points_tally  
        collections.insert_one({  
            "strategy": strategy_name,  
            "total_points": 0,  
            "initialized_date": initialization_date,  
            "last_updated": initialization_date  
        })  
   client.close()

def simulate_trade(ticker, strategy, historical_data, current_price, account_cash, portfolio_qty, total_portfolio_value, mongo_url):  
   """  
   Simulates a trade based on the given strategy and updates MongoDB.  
   """  
   action, quantity, _ = strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value)  
    
   # Update MongoDB with trade details  
   client = MongoClient(mongo_url)  
   db = client.trading_simulator  
   holdings_collection = db.algorithm_holdings  
   points_collection = db.points_tally  
  
   # Find the strategy document in MongoDB  
   strategy_doc = holdings_collection.find_one({"strategy": strategy.__name__})  
   holdings_doc = holdings_collection["holdings"]
   # Update holdings and cash based on the trade action - still need to work a little more on buy sell simulation including updating holding stats  
   if action == "buy" or action == "strong buy":  
        
      strategy_doc["amount_cash"] -= quantity * current_price  
      strategy_doc["total_trades"] += 1  
      strategy_doc["current_portfolio_value"] += quantity * current_price  
      if quantity > 0:  
        strategy_doc["successful_trades"] += 1  
   elif action == "sell" or action == "strong sell":  
      """
      if sold and quantity is 0, we delete it from holdings because we don't have any more holdings anymore
      we have to deduct quantity . there's a lot to do
      """
      strategy_doc["holdings"][ticker] = 0  
      strategy_doc["amount_cash"] += quantity * current_price  
      strategy_doc["total_trades"] += 1  
      strategy_doc["current_portfolio_value"] -= quantity * current_price  
      if quantity > 0:  
        strategy_doc["successful_trades"] += 1  
   """
   hold - is there anything to do?
   also need to fix asset_quantities for trding cliet because if quantity is 0 after sell, we need to delete it to conserve mem
   """
   
   # Update points tally based on the trade action  
   points_doc = points_collection.find_one({"strategy": strategy.__name__})  
   if action == "buy":  
      points_doc["total_points"] += 10  
   elif action == "sell":  
      points_doc["total_points"] += 5  
   elif action == "hold":  
      points_doc["total_points"] += 1  
  
   # Update MongoDB with the modified strategy documents  
   holdings_collection.update_one({"strategy": strategy.__name__}, {"$set": strategy_doc})  
   points_collection.update_one({"strategy": strategy.__name__}, {"$set": points_doc})  
  
   client.close()  

def update_portfolio_values():
    """
    still need to implement.
    we go through each strategy and update portfolio value buy cash + summation(holding * current price)
    """
    return None

def main():  
   """  
   Main function to control the workflow based on the market's status.  
   """  
   ndaq_tickers = []  
   early_hour_first_iteration = False  
   client = RESTClient(api_key=POLYGON_API_KEY)  
   trading_client = TradingClient(API_KEY, API_SECRET)  
   data_client = StockHistoricalDataClient(API_KEY, API_SECRET)  
   mongo_client = MongoClient(mongo_url)  
   db = mongo_client.trading_simulator  
   holdings_collection = db.algorithm_holdings  
  
   while True:  
      status = market_status(client)  # Use the helper function for market status  
  
      if status == "open":  
        logging.info("Market is open. Processing strategies.")  
        if not ndaq_tickers:  
           ndaq_tickers = helper_files.client_helper.get_ndaq_tickers(mongo_url)  
          
        for strategy in strategies:  
           strategy_doc = holdings_collection.find_one({"strategy": strategy.__name__})  
           if not strategy_doc:
              logging.warning(f"Strategy {strategy.__name__} not found in database. Skipping.")  
              continue  
  
           account_cash = strategy_doc["amount_cash"]  
           total_portfolio_value = strategy_doc["current_portfolio_value"]  
  
           for ticker in ndaq_tickers:  
              try:  
                current_price = helper_files.client_helper.get_latest_price(ticker)  
                if current_price is None:  
                   logging.warning(f"Could not fetch price for {ticker}. Skipping.")  
                   continue  
  
                historical_data = trading_strategies.get_historical_data(ticker, data_client)  
                portfolio_qty = strategy_doc["holdings"].get(ticker, 0)  
  
                simulate_trade(ticker, strategy, historical_data, current_price,  
                          account_cash, portfolio_qty, total_portfolio_value, mongo_url)  
                  
                # Update account cash and portfolio value after each trade  
                updated_doc = holdings_collection.find_one({"strategy": strategy.__name__})  
                account_cash = updated_doc["amount_cash"]  
                total_portfolio_value = updated_doc["current_portfolio_value"]  
  
              except Exception as e:  
                logging.error(f"Error processing {ticker} for {strategy.__name__}: {e}")  
  
        # After processing all strategies and tickers, update portfolio values  
        update_portfolio_values()  
  
        logging.info("Finished processing all strategies. Waiting for 60 seconds.")  
        time.sleep(60)  
  
      elif status == "early_hours":  
        if not early_hour_first_iteration:  
           ndaq_tickers = helper_files.client_helper.get_ndaq_tickers(mongo_url)  
           early_hour_first_iteration = True  
        logging.info("Market is in early hours. Waiting for 60 seconds.")  
        time.sleep(60)  
  
      elif status == "closed":  
        logging.info("Market is closed. Performing post-market analysis.")  
        time.sleep(60)  
      else:  
        logging.error("An error occurred while checking market status.")  
        time.sleep(60)  
  
if __name__ == "__main__":  
   main()