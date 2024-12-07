from alpaca.data.historical import StockHistoricalDataClient  
from config import API_KEY, API_SECRET, FINANCIAL_PREP_API_KEY, POLYGON_API_KEY
from pymongo import MongoClient
from helper_files.client_helper import get_ndaq_tickers
from config import MONGO_DB_USER, MONGO_DB_PASS
from helper_files.client_helper import strategies
from strategies.talib_indicators import get_data
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
   # Define test parameters  
   for ticker in tickers: 
      
      for strategy in strategies: 
         for period in periods:
            data = get_data(ticker, period)
            try:
               decision = strategy(ticker, data)
               print(f"{strategy.__name__} : {decision} :{ticker}")
            except Exception as e:
               print(f"ERROR processing {ticker} for {strategy.__name__}: {e}")
         time.sleep(5)
   
   

if __name__ == "__main__":  
   test_strategies()