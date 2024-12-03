import pandas as pd  
from datetime import datetime, timedelta  
from alpaca.data.historical import StockHistoricalDataClient  
from alpaca.data.requests import StockBarsRequest  
from alpaca.data.timeframe import TimeFrame  
from config import API_KEY, API_SECRET, FINANCIAL_PREP_API_KEY, POLYGON_API_KEY
import strategies.trading_strategies_v2_1 as ts
import helper_files.client_helper
from pymongo import MongoClient
import yfinance as yf
from helper_files.client_helper import get_ndaq_tickers, get_latest_price
from config import MONGO_DB_USER, MONGO_DB_PASS
from helper_files.client_helper import get_latest_price
import requests
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
   
   # Initialize the StockHistoricalDataClient  
   client = StockHistoricalDataClient(API_KEY, API_SECRET)  
   mongo_client = MongoClient() 
   tickers = get_ndaq_tickers(mongo_url, FINANCIAL_PREP_API_KEY)
   mongo_client.close()

   
   # Define test parameters  
   for ticker in tickers:  
      account_cash = 50000 
      portfolio_qty = 100
      total_portfolio_value = 2000
    
      historical_data = get_historical_data(ticker, client) 
      current_price = historical_data['close'].iloc[-1]
      # Test each strategy  
      
      strategies = [ts.levy_distribution_strategy, ts.regime_switching_strategy]
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
   
   
   
   

   
   
      
   
def test_helper():
   ticker = 'SPY'  # Replace with your desired ticker

   
   print(get_latest_price(ticker))
if __name__ == "__main__":  
   test_helper()