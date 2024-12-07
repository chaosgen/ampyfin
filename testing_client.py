from alpaca.data.historical import StockHistoricalDataClient  
from config import API_KEY, API_SECRET, FINANCIAL_PREP_API_KEY, POLYGON_API_KEY
from pymongo import MongoClient
from helper_files.client_helper import get_ndaq_tickers
from config import MONGO_DB_USER, MONGO_DB_PASS
from helper_files.client_helper import strategies
from strategies.talib_indicators import get_data
import threading
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net"

def test_strategies():
   
   # Initialize the StockHistoricalDataClient  
   client = StockHistoricalDataClient(API_KEY, API_SECRET)  
   mongo_client = MongoClient() 
   tickers = get_ndaq_tickers(mongo_url, FINANCIAL_PREP_API_KEY)
   mongo_client.close()

   
   # Define test parameters  
   for ticker in tickers: 
      data = get_data(ticker)
      for strategy in strategies: 
         
         try:
            decision = strategy(ticker, data)
            print(f"{strategy.__name__} : {decision} :{ticker}")
         except Exception as e:
            print(f"ERROR processing {ticker} for {strategy.__name__}: {e}")
   
   

if __name__ == "__main__":  
   test_strategies()