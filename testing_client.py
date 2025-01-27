from alpaca.data.historical import StockHistoricalDataClient  
from config import API_KEY, API_SECRET, FINANCIAL_PREP_API_KEY, POLYGON_API_KEY
from pymongo import MongoClient
from helper_files.client_helper import get_ndaq_tickers
from config import MONGO_DB_USER, MONGO_DB_PASS
from helper_files.client_helper import strategies, get_latest_price, dynamic_period_selector
from strategies.talib_indicators import get_data, simulate_strategy
import threading
import random
from config import mongo_url
import time
def test_strategies():
   
   # Initialize the StockHistoricalDataClient  
   mongo_client = MongoClient() 
   tickers = get_ndaq_tickers(mongo_url, FINANCIAL_PREP_API_KEY)
   mongo_client.close()
   
   periods = ['1d', '5d','1mo', '3mo', '6mo', '1y', '2y', '5y', 'ytd', 'max']
   account_cash = 50000
   portfolio_qty = 10
   total_portfolio_value = 500000
   # Define test parameters  
   for ticker in tickers: 
      current_price = get_latest_price(ticker)   
      historical_data = get_data(ticker)
      for strategy in strategies: 
         
         
         try:
            decision = simulate_strategy(strategy, ticker, current_price, historical_data, account_cash, portfolio_qty, total_portfolio_value)

            print(f"{strategy.__name__} : {decision} :{ticker}")
         except Exception as e:
            print(f"ERROR processing {ticker} for {strategy.__name__}: {e}")
      time.sleep(5)
   
   for ticker in tickers:
      print(f"{ticker} : {dynamic_period_selector(ticker)}")
   
   

if __name__ == "__main__":  
   print(get_latest_price('VRTX'))
   """
   test_strategies()
   """