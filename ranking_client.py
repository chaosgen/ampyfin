from polygon import RESTClient
from config import POLYGON_API_KEY, FINANCIAL_PREP_API_KEY, MONGO_DB_USER, MONGO_DB_PASS, API_KEY, API_SECRET, BASE_URL
import threading
from concurrent.futures import ThreadPoolExecutor

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

def find_nans_within_rank_holding():
   mongo_client = MongoClient(mongo_url)
   db = mongo_client.trading_simulator
   collections = db.algorithm_holdings
   for strategy in strategies:
      strategy_doc = collections.find_one({"strategy": strategy.__name__})
      holdings_doc = strategy_doc.get("holdings", {})
      for ticker in holdings_doc:
         if holdings_doc[ticker]['quantity'] == 0:
            print(f"{ticker} : {strategy.__name__}")

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
  
   
    
   strategy_name = "test_strategy"
   
   collections = db.algorithm_holdings 
   
   if not collections.find_one({"strategy": strategy_name}):
      
      collections.insert_one({  
         "strategy": strategy_name,  
         "holdings": {},  
         "amount_cash": 50000,  
         "initialized_date": initialization_date,  
         "total_trades": 0,  
         "successful_trades": 0,
         "neutral_trades": 0,
         "failed_trades": 0,   
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
   print(f"Simulating trade for {ticker} with strategy {strategy.__name__} and quantity of {portfolio_qty}")
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
   if action in ["buy", "strong buy"] and strategy_doc["amount_cash"] - quantity * current_price > 15000 and quantity > 0:
      logging.info(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
      # Calculate average price if already holding some shares of the ticker
      if ticker in holdings_doc:
         current_qty = holdings_doc[ticker]["quantity"]
         new_qty = current_qty + quantity
         average_price = (holdings_doc[ticker]["price"] * current_qty + current_price * quantity) / new_qty
      else:
         new_qty = quantity
         average_price = current_price

      # Update the holdings document for the ticker. 
      holdings_doc[ticker] = {
            "quantity": new_qty,
            "price": average_price
      }

      # Deduct the cash used for buying and increment total trades
      holdings_collection.update_one(
         {"strategy": strategy.__name__},
         {
            "$set": {
                  "holdings": holdings_doc,
                  "amount_cash": strategy_doc["amount_cash"] - quantity * current_price,
                  "last_updated": datetime.now()
            },
            "$inc": {"total_trades": 1}
         },
         upsert=True
      )
      

   elif action in ["sell", "strong sell"] and str(ticker) in holdings_doc and holdings_doc[str(ticker)]["quantity"] > 0:
      
      logging.info(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
      current_qty = holdings_doc[ticker]["quantity"]
        
      # Ensure we do not sell more than we have
      sell_qty = min(quantity, current_qty)
      holdings_doc[ticker]["quantity"] = current_qty - sell_qty
      
      price_change_ratio = current_price / holdings_doc[ticker]["price"] if ticker in holdings_doc else 1
      
      

      if current_price > holdings_doc[ticker]["price"]:
         #increment successful trades
         holdings_collection.update_one(
            {"strategy": strategy.__name__},
            {"$inc": {"successful_trades": 1}},
            upsert=True
         )
         
         # Calculate points to add if the current price is higher than the purchase price
         if price_change_ratio < 1.05:
            points = time_delta * 1
         elif price_change_ratio < 1.1:
            points = time_delta * 1.5
         else:
            points = time_delta * 2
         
      else:
         # Calculate points to deduct if the current price is lower than the purchase price
         if holdings_doc[ticker]["price"] == current_price:
            holdings_collection.update_one(
               {"strategy": strategy.__name__},
               {"$inc": {"neutral_trades": 1}}
            )
            
         else:   
            
            holdings_collection.update_one(
               {"strategy": strategy.__name__},
               {"$inc": {"failed_trades": 1}},
               upsert=True
            )
         
         if price_change_ratio > 0.975:
            points = -time_delta * 1
         elif price_change_ratio > 0.95:
            points = -time_delta * 1.5
         else:
            points = -time_delta * 2
         
      # Update the points tally
      points_collection.update_one(
         {"strategy": strategy.__name__},
         {"$inc": {"points": points}},
         upsert=True
      )
      if holdings_doc[ticker]["quantity"] == 0:      
         del holdings_doc[ticker]
      # Update cash after selling
      holdings_collection.update_one(
         {"strategy": strategy.__name__},
         {
            "$set": {
               "holdings": holdings_doc,
               "amount_cash": strategy_doc["amount_cash"] + sell_qty * current_price,
               "last_updated": datetime.now()
            },
            "$inc": {"total_trades": 1}
         },
         upsert=True
      )

        
      # Remove the ticker if quantity reaches zero
      if holdings_doc[ticker]["quantity"] == 0:      
         del holdings_doc[ticker]
        
   else:
      logging.info(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
   print(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
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
          
          # Get the current price of the ticker from the Polygon API
          current_price = None
          while current_price is None:
            try:
               current_price = get_latest_price(ticker)
            except:
               print(f"Error fetching price for {ticker}. Retrying...")
          print(f"Current price of {ticker}: {current_price}")
          # Calculate the value of the holding
          holding_value = holding["quantity"] * current_price
          # Add the holding value to the portfolio value
          portfolio_value += holding_value
          
      # Update the portfolio value in the strategy document
      holdings_collection.update_one({"strategy": strategy_doc["strategy"]}, {"$set": {"portfolio_value": portfolio_value}}, upsert=True)

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
           ndaq_tickers = get_ndaq_tickers(mongo_url, FINANCIAL_PREP_API_KEY) 
        for strategy in strategies:  
            strategy_doc = holdings_collection.find_one({"strategy": strategy.__name__})  
            if not strategy_doc:
               logging.warning(f"Strategy {strategy.__name__} not found in database. Skipping.")  
               continue  
  
            account_cash = strategy_doc["amount_cash"]  
            total_portfolio_value = strategy_doc["portfolio_value"] 
           
            for ticker in ndaq_tickers:  
               try:  
                  current_price = None
                  while current_price is None:
                     try:
                        current_price = get_latest_price(ticker)
                     except:
                        print(f"Error fetching price for {ticker}. Retrying...")
                  print(f"Current price of {ticker}: {current_price}") 
                  if current_price is None:  
                     logging.warning(f"Could not fetch price for {ticker}. Skipping.")  
                     continue  
  
                  historical_data = trading_strategies.get_historical_data(ticker, data_client)  
                  portfolio_qty = strategy_doc["holdings"].get(ticker, 0)
                  if portfolio_qty:
                     portfolio_qty = portfolio_qty["quantity"]
                  
                  
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
           
           ndaq_tickers = get_ndaq_tickers(mongo_url, FINANCIAL_PREP_API_KEY)  
           early_hour_first_iteration = False  
           post_market_hour_first_iteration = True
        logging.info("Market is in early hours. Waiting for 60 seconds.")  
        time.sleep(60)  
  
      elif status == "closed":  
         
        early_hour_first_iteration = True
        if post_market_hour_first_iteration:
            logging.info("Market is closed. Performing post-market analysis.") 
            post_market_hour_first_iteration = False
            #increment time_Delta in database by 0.01
            mongo_client = MongoClient(mongo_url)
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
   find_nans_within_rank_holding()