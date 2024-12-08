from config import API_KEY, API_SECRET, POLYGON_API_KEY, RANK_POLYGON_API_KEY, MONGO_DB_USER, MONGO_DB_PASS, mongo_url
from helper_files.client_helper import strategies
from pymongo import MongoClient
from datetime import datetime
import math
import yfinance as yf
from helper_files.client_helper import get_latest_price
from alpaca.trading.client import TradingClient

def insert_rank_to_coefficient(i):
   try:
      client = MongoClient(mongo_url)  
      db = client.trading_simulator 
      collections  = db.rank_to_coefficient
      """
      clear all collections entry first and then insert from 1 to i
      """
      collections.delete_many({})
      for i in range(1, i + 1):
      
         e = math.e
         rate = ((e**e)/(e**2) - 1)
         coefficient = rate**(2 * i)
         collections.insert_one(
            {"rank": i, 
            "coefficient": coefficient
            }
         )
      client.close()
      print("Successfully inserted rank to coefficient")
   except Exception as exception:
      print(exception)
   
  
def initialize_rank():  
   try:
      client = MongoClient(mongo_url)  
      db = client.trading_simulator  
      collections = db.algorithm_holdings  
         
      initialization_date = datetime.now()  


      for strategy in strategies:
         strategy_name = strategy.__name__


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
      print("Successfully initialized rank")
   except Exception as exception:
      print(exception)

def initialize_time_delta():
   try:
      client = MongoClient(mongo_url)
      db = client.trading_simulator
      collection = db.time_delta
      collection.insert_one({"time_delta": 0.01})
      client.close()
      print("Successfully initialized time delta")
   except Exception as exception:
      print(exception)

def initialize_market_setup():
   try:
      client = MongoClient(mongo_url)
      db = client.market_data
      collection = db.market_status
      collection.insert_one({"market_status": "closed"})
      client.close()
      print("Successfully initialized market setup")
   except Exception as exception:
      print(exception)

def initialize_portfolio_percentages():
   try:
      client = MongoClient(mongo_url)
      trading_client = TradingClient(API_KEY, API_SECRET)
      account = trading_client.get_account()
      db = client.trades
      collection = db.portfolio_values
      portfolio_value = float(account.portfolio_value)
      collection.insert_one({
         "name" : "portfolio_percentage",
         "portfolio_value": (portfolio_value-50000)/50000,
      })
      collection.insert_one({
         "name" : "ndaq_percentage",
         "portfolio_value": (get_latest_price('QQQ')-503.17)/503.17,
      })
      collection.insert_one({
         "name" : "spy_percentage",
         "portfolio_value": (get_latest_price('SPY')-590.50)/590.50,
      })
      client.close()
      print("Successfully initialized portfolio percentages")
   except Exception as exception:
      print(exception)


if __name__ == "__main__":
   
   insert_rank_to_coefficient(200)
   
   initialize_rank()
   
   initialize_time_delta()
   
   initialize_market_setup()
   
   initialize_portfolio_percentages()
   