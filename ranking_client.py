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
from helper_files.client_helper import strategies, get_latest_price, get_ndaq_tickers
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
import heapq 


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('rank_system.log'),  # Log messages to a file
        logging.StreamHandler()             # Log messages to the console
    ]
)

# Connect to MongoDB  
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net"

def insert_rank_to_coefficient(i):
   """
   currently i is at 50
   next i is at 51
   """
    
   client = MongoClient(mongo_url)  
   db = client.trading_simulator 
   collections  = db.rank_to_coefficient
   """
   clear all collections entry first and then insert from 1 to i
   """
   collections.delete_many({})
   for i in range(1, i + 1):
   
      e = math.e
      rate = (e**e)/(e**2) - 1
      coefficient = rate**(2 * i)
      collections.insert_one(
         {"rank": i, 
         "coefficient": coefficient
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
            "last_updated": initialization_date, 
            "portfolio_value": 50000 
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
    
    # Simulate trading action from strategy
    action, quantity, _ = strategy(ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value)
    
    # MongoDB setup
    client = MongoClient(mongo_url)
    db = client.trading_simulator
    holdings_collection = db.algorithm_holdings
    points_collection = db.points_tally

    # Find the strategy document in MongoDB
    strategy_doc = holdings_collection.find_one({"strategy": strategy.__name__})
    holdings_doc = strategy_doc.get("holdings", {})
    time_delta = db.time_delta['time_delta']
    
    # Update holdings and cash based on trade action
    if action in ["buy", "strong buy"] and strategy_doc["amount_cash"] - quantity * current_price > 15000:
        logging.info(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
        # Calculate average price if already holding some shares of the ticker
        if ticker in holdings_doc:
            current_qty = holdings_doc[ticker]["quantity"]
            new_qty = current_qty + quantity
            average_price = (holdings_doc[ticker]["price"] * current_qty + current_price * quantity) / new_qty
        else:
            new_qty = quantity
            average_price = current_price

        # Update the holdings document
        holdings_doc[ticker] = {
            "quantity": new_qty,
            "price": average_price
        }

        # Deduct the cash used for buying
        strategy_doc["amount_cash"] -= quantity * current_price
        strategy_doc["total_trades"] += 1

    elif action in ["sell", "strong sell"] and ticker in holdings_doc and holdings_doc[ticker]["quantity"] > 0:
        logging.info(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
        current_qty = holdings_doc[ticker]["quantity"]
        
        # Ensure we do not sell more than we have
        sell_qty = min(quantity, current_qty)
        holdings_doc[ticker]["quantity"] -= sell_qty

        # Update cash after selling
        strategy_doc["amount_cash"] += sell_qty * current_price
        strategy_doc["total_trades"] += 1

        

        # Points tally based on price increase/decrease

        price_change_ratio = current_price / holdings_doc[ticker]["price"] if ticker in holdings_doc else 1

        if current_price > holdings_doc[ticker]["price"]:
           #increment successful trades
           strategy_doc["successful_trades"] += 1
           # Calculate points to add if the current price is higher than the purchase price
           if price_change_ratio < 1.05:
              points = time_delta * 1
           elif price_change_ratio < 1.1:
              points = time_delta * 1.5
           else:
              points = time_delta * 2
           points_collection.update_one({"strategy": strategy.__name__}, {"$inc": {"total_points": points}})
        else:
           # Calculate points to deduct if the current price is lower than the purchase price
           if holdings_doc[ticker]["price"] == current_price:
              strategy_doc["neutral_trades"] += 1
           else:   
              strategy_doc["failed_trades"] += 1
            
           if price_change_ratio > 0.975:
              points = -time_delta * 1
           elif price_change_ratio > 0.95:
              points = -time_delta * 1.5
           else:
              points = -time_delta * 2
           points_collection.update_one({"strategy": strategy.__name__}, {"$inc": {"total_points": points}})
        
        # Remove the ticker if quantity reaches zero
        if holdings_doc[ticker]["quantity"] == 0:
            del holdings_doc[ticker]
    else:
       logging.info(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
       
    # Update the strategy document in MongoDB
    holdings_collection.update_one(
        {"strategy": strategy.__name__},
        {"$set": {
            "holdings": holdings_doc,
            "amount_cash": strategy_doc["amount_cash"],
            "total_trades": strategy_doc["total_trades"],
            "last_updated": datetime.now()
        }},
        upsert=True
    )

    points_collection.update_one(
        {"strategy": strategy.__name__},
        {"$set": {"last_updated": datetime.now()}},
        upsert=True
    )

    # Close the MongoDB connection
    client.close()

def update_portfolio_values():
   """
   still need to implement.
   we go through each strategy and update portfolio value buy cash + summation(holding * current price)
   """
   client = MongoClient(mongo_url)  
   db = client.trading_simulator  
   holdings_collection = db.algorithm_holdings
   # Update portfolio values
   for strategy_doc in holdings_collection.find({}):
      # Calculate the portfolio value for the strategy
      portfolio_value = strategy_doc["amount_cash"]
      
      for ticker, holding in strategy_doc["holdings"].items():
          print(f"{ticker}: {holding}")
          # Get the current price of the ticker from the Polygon API
          current_price = get_latest_price(ticker)
          # Calculate the value of the holding
          holding_value = holding["quantity"] * current_price
          # Add the holding value to the portfolio value
          portfolio_value += holding_value
      # Update the portfolio value in the strategy document
      holdings_collection.update_one({"strategy": strategy_doc["strategy"]}, {"$set": {"portfolio_value": portfolio_value}})

   # Update MongoDB with the modified strategy documents
   client.close()

def update_ranks():
   """"
   based on portfolio values, rank the strategies to use for actual trading_simulator
   """
   client = MongoClient(mongo_url)
   db = client.trading_simulator
   points_collection = db.points_tally
   rank_collection = db.rank
   algo_holdings = db.algorithm_holdings
   """
   delete all documents in rank collection first
   """
   rank_collection.delete_many({})
   """
   now update rank based on successful_trades - failed
   """
   q = []
   for strategy_doc in algo_holdings.find({}):
      """
      based on (points_tally (less points pops first), failed-successful(more neagtive pops first), portfolio value (less value pops first), and then strategy_name), we add to heapq.
      """
      strategy_name = strategy_doc["strategy"]
      heapq.heappush(q, (points_collection.find_one({"strategy": strategy_name})["total_points"], strategy_doc["failed_trades"] - strategy_doc["successful_trades"], strategy_doc["portfolio_value"], strategy_doc["strategy"]))
   rank = 1
   while q:
      
      _, _, _, strategy_name = heapq.heappop(q)
      rank_collection.insert_one({"strategy": strategy_name, "rank": rank})
      rank+=1
   client.close()

def main():  
   """  
   Main function to control the workflow based on the market's status.  
   """  
   ndaq_tickers = []  
   early_hour_first_iteration = True
   post_market_hour_first_iteration = True
   data_client = StockHistoricalDataClient(API_KEY, API_SECRET)  
   mongo_client = MongoClient(mongo_url)  
   db = mongo_client.trading_simulator  
   holdings_collection = db.algorithm_holdings  
   
   
   while True:  
      status = mongo_client.market_data.market_status.find_one({})["market_status"]
      
      if status == "open":  
        logging.info("Market is open. Processing strategies.")  
        if not ndaq_tickers:  
           ndaq_tickers = get_ndaq_tickers(mongo_url)  
          
        for strategy in strategies:  
            strategy_doc = holdings_collection.find_one({"strategy": strategy.__name__})  
            if not strategy_doc:
               logging.warning(f"Strategy {strategy.__name__} not found in database. Skipping.")  
               continue  
  
            account_cash = strategy_doc["amount_cash"]  
            total_portfolio_value = strategy_doc["portfolio_value"] 
           
            for ticker in ndaq_tickers:  
               try:  
                  current_price = get_latest_price(ticker)  
                  if current_price is None:  
                     logging.warning(f"Could not fetch price for {ticker}. Skipping.")  
                     continue  
  
                  historical_data = trading_strategies.get_historical_data(ticker, data_client)  
                  portfolio_qty = strategy_doc["holdings"].get(ticker, 0)  
                  
                  simulate_trade(ticker, strategy, historical_data, current_price,  
                          account_cash, portfolio_qty, total_portfolio_value, mongo_url)  
                  
                  if mongo_client.market_data.market_status.find_one({})["market_status"] == "closed":
                     break
               except Exception as e:  
                  logging.error(f"Error processing {ticker} for {strategy.__name__}: {e}")
            if mongo_client.market_data.market_status.find_one({})["market_status"] == "closed":
               break 
            print(f"{strategy} completed")
        update_portfolio_values()
  
        logging.info("Finished processing all strategies. Waiting for 60 seconds.")  
        time.sleep(60)  
  
      elif status == "early_hours":  
        if early_hour_first_iteration:  
           ndaq_tickers = get_ndaq_tickers(mongo_url)  
           early_hour_first_iteration = False  
           post_market_hour_first_iteration = True
        logging.info("Market is in early hours. Waiting for 60 seconds.")  
        time.sleep(60)  
  
      elif status == "closed":  
        logging.info("Market is closed. Performing post-market analysis.")  
        early_hour_first_iteration = True
        if post_market_hour_first_iteration:
            post_market_hour_first_iteration = False
            #increment time_Delta in database by 0.01
            
            mongo_client.trading_simulator.time_delta.update_one({}, {"$inc": {"time_delta": 0.01}})
            mongo_client.close()
            #Update ranks
            update_portfolio_values()
            update_ranks()
        logging.info("Market is closed. Waiting for 60 seconds.")
        time.sleep(60)  
      else:  
        logging.error("An error occurred while checking market status.")  
        time.sleep(60)  
   
  
if __name__ == "__main__":  
   main()