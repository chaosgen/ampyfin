from polygon import RESTClient
from config import POLYGON_API_KEY, FINANCIAL_PREP_API_KEY, MONGO_DB_USER, MONGO_DB_PASS, API_KEY, API_SECRET, BASE_URL
import json
import certifi
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from pymongo import MongoClient
import time
from datetime import datetime, timedelta
from helper_files.client_helper import place_order, get_ndaq_tickers, market_status, strategies  # Import helper functions
from alpaca.trading.client import TradingClient
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from strategies.trading_strategies_v1 import get_historical_data
import yfinance as yf
import logging
from collections import Counter
from statistics import median, mode
import statistics

# MongoDB connection string
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('system.log'),  # Log messages to a file
        logging.StreamHandler()             # Log messages to the console
    ]
)

def majority_decision_and_median_quantity(decisions_and_quantities):  
   """  
   Determines the majority decision (buy, sell, or hold) and returns the median quantity for the chosen action.  
   Groups 'strong buy' with 'buy' and 'strong sell' with 'sell'.  
   """  
   buy_decisions = ['buy', 'strong buy']  
   sell_decisions = ['sell', 'strong sell']  
    
   buy_count = sum(1 for d, _ in decisions_and_quantities if d in buy_decisions)  
   sell_count = sum(1 for d, _ in decisions_and_quantities if d in sell_decisions)  
   hold_count = sum(1 for d, _ in decisions_and_quantities if d == 'hold')  
  
   if buy_count > sell_count and buy_count > hold_count:  
      quantities = [q for d, q in decisions_and_quantities if d in buy_decisions]  
      return 'buy', median(quantities)  
   elif sell_count > buy_count and sell_count > hold_count:  
      quantities = [q for d, q in decisions_and_quantities if d in sell_decisions]  
      return 'sell', median(quantities)  
   else:  
      return 'hold', 0

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
    db = mongo_client.assets
    asset_collection = db.asset_quantities

    while True:
        status = market_status(client)  # Use the helper function for market status

        if status == "open":
            logging.info("Market is open. Waiting for 60 seconds.")
            if not ndaq_tickers:
                ndaq_tickers = get_ndaq_tickers(mongo_url)  # Fetch tickers using the helper function
            account = trading_client.get_account()

            for ticker in ndaq_tickers:
                decisions_and_quantities = []
                buying_power = float(account.cash)
                portfolio_value = float(account.portfolio_value)
                cash_to_portfolio_ratio = buying_power / portfolio_value

                try:
                    historical_data = get_historical_data(ticker, data_client)
                    ticker_yahoo = yf.Ticker(ticker)
                    data = ticker_yahoo.history()
                    current_price = data['Close'].iloc[-1]

                    asset_info = asset_collection.find_one({'symbol': ticker})
                    portfolio_qty = asset_info['qty'] if asset_info else 0.0
                    print(type(historical_data))
                    print(type(ticker))
                    print(type(data))
                    print(type(current_price))
                    
                    for strategy in strategies:
                        
                        decision, quantity, _ = strategy(ticker, current_price, historical_data,
                                                      buying_power, portfolio_qty, portfolio_value)
                        decisions_and_quantities.append((decision, quantity))
                    decision, quantity = majority_decision_and_median_quantity(decisions_and_quantities)
                    print(f"Ticker: {ticker}, Decision: {decision}, Quantity: {quantity}")
                    
                    """
                    later we should implement buying_power regulator depending on vix strategy
                    for now in bull: 15000
                    for bear: 0.0
                    """
                    if decision == "buy" and cash_to_portfolio_ratio >= 0.4 and buying_power > 15000:
                        order = place_order(trading_client, ticker, OrderSide.BUY, qty=quantity, mongo_url=mongo_url)  # Place order using helper
                        asset_collection.update_one({'symbol': ticker}, {'$set': {'qty': portfolio_qty + quantity}})
                        logging.info(f"Executed BUY order for {ticker}: {order}")
                    elif decision == "sell" and portfolio_qty > 0:
                        order = place_order(trading_client, ticker, OrderSide.SELL, qty=quantity, mongo_url=mongo_url)  # Place order using helper
                        if portfolio_qty - quantity == 0:
                            asset_collection.delete_one({'symbol': ticker})
                        else:
                            asset_collection.update_one({'symbol': ticker}, {'$set': {'qty': portfolio_qty - quantity}})
                        logging.info(f"Executed SELL order for {ticker}: {order}")
                    else:
                        logging.info(f"Holding for {ticker}, no action taken.")
                    

                except Exception as e:
                    logging.error(f"Error processing {ticker}: {e}")

            time.sleep(60)

        elif status == "early_hours":
            if not early_hour_first_iteration:
                ndaq_tickers = get_ndaq_tickers(mongo_url)
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