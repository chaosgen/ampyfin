from config import API_KEY, API_SECRET, POLYGON_API_KEY, RANK_POLYGON_API_KEY, MONGO_DB_USER, MONGO_DB_PASS, mongo_url
from client_helper import strategies
from pymongo import MongoClient
import datetime
import math

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

if __name__ == "__main__":
   insert_rank_to_coefficient(100)
   initialize_rank()