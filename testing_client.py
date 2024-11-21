import pandas as pd  
from datetime import datetime, timedelta  
from alpaca.data.historical import StockHistoricalDataClient  
from alpaca.data.requests import StockBarsRequest  
from alpaca.data.timeframe import TimeFrame  
from config import API_KEY, API_SECRET, FINANCIAL_PREP_API_KEY
import strategies.trading_strategies_v2 as trading_strategies_v2
import helper_files.client_helper
from pymongo import MongoClient
from helper_files.client_helper import get_ndaq_tickers, get_latest_price
from config import MONGO_DB_USER, MONGO_DB_PASS
from helper_files.client_helper import strategies
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net"

def get_historical_data(ticker, client, days=100):  
   """  
   Fetch historical bar data for a given stock ticker.  
    
   :param ticker: The stock ticker symbol.  
   :param client: An instance of StockHistoricalDataClient.  
   :param days: Number of days of historical data to fetch.  
   :return: DataFrame with historical stock bar data. test all data for all tickers - try to follow trading client specification  
   """  
   start_time = datetime.now() - timedelta(days=days)  
   request_params = StockBarsRequest(  
      symbol_or_symbols=ticker,  
      timeframe=TimeFrame.Day,  
      start=start_time  
   )  
    
   bars = client.get_stock_bars(request_params)  
   data = bars.df  
   return data  

def test_strategies():
   """
   # Initialize the StockHistoricalDataClient  
   client = StockHistoricalDataClient(API_KEY, API_SECRET)  
   mongo_client = MongoClient() 
   tickers = get_ndaq_tickers(mongo_url, FINANCIAL_PREP_API_KEY)
   mongo_client.close()

   
   # Define test parameters  
   for ticker in tickers:  
      account_cash = 17980  
      portfolio_qty = 95
      total_portfolio_value = 50000
    
      historical_data = get_historical_data(ticker, client) 
      current_price = historical_data['close'].iloc[-1]
      # Test each strategy  
      
      strategies = [trading_strategies_v2.rsi_strategy]
      for strategy in strategies:  
         try:
            decision, quantity, ticker = strategy(  
                  ticker,  
                  current_price,  
                  historical_data,  
                  account_cash,  
                  portfolio_qty,  
                  total_portfolio_value  
            )
            
            print(f"Strategy {strategy.__name__} recommends {ticker} and {decision} and {quantity}")

         except Exception as e:
            print(f"ERROR processing {ticker} for {strategy.__name__}: {e}")
   """
   
   
   def simulate_trade(ticker, strategy, historical_data, current_price, account_cash, portfolio_qty, total_portfolio_value, mongo_url):
      """
      Simulates a trade based on the given strategy and updates MongoDB.
      """
      
      
      action = "sell"
      quantity = 1
      
      # MongoDB setup
      client = MongoClient(mongo_url)
      db = client.trading_simulator
      holdings_collection = db.algorithm_holdings
      points_collection = db.points_tally
      
      # Find the strategy document in MongoDB
      
      strategy_doc = holdings_collection.find_one({"strategy": "test"})
      holdings_doc = strategy_doc.get("holdings", {})
      time_delta = db.time_delta.find_one({})["time_delta"]
      
      
      # Update holdings and cash based on trade action
      if action in ["buy", "strong buy"] and strategy_doc["amount_cash"] - quantity * current_price > 15000 and quantity > 0:
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
            {"strategy": "test"},
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
         current_qty = holdings_doc[ticker]["quantity"]
         
         # Ensure we do not sell more than we have
         sell_qty = min(quantity, current_qty)
         holdings_doc[ticker]["quantity"] = current_qty - sell_qty
         if holdings_doc[ticker]["quantity"] == 0:      
            del holdings_doc[ticker]
         price_change_ratio = current_price / holdings_doc[ticker]["price"] if ticker in holdings_doc else 1
         
         

         if current_price > holdings_doc[ticker]["price"]:
            #increment successful trades
            holdings_collection.update_one(
               {"strategy": "test"},
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
                  {"strategy": "test"},
                  {"$inc": {"neutral_trades": 1}}
               )
               
            else:   
               
               holdings_collection.update_one(
                  {"strategy": "test"},
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
            {"strategy": "test"},
            {"$inc": {"points": points}},
            upsert=True
         )
         # Update cash after selling
         holdings_collection.update_one(
            {"strategy": "test"},
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
         
      else:
         print(f"Action: {action} | Ticker: {ticker} | Quantity: {quantity} | Price: {current_price}")
      
      client.close()

   
   
      
   simulate_trade("AAPL", None, None, get_latest_price("AAPL"), 50000, 0, 50000, mongo_url)
def test_helper():
   print(helper_files.client_helper.get_latest_price("AAPL"))
if __name__ == "__main__":  
   test_strategies()