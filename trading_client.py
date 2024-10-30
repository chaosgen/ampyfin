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
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net"

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


def weighted_majority_decision_and_median_quantity(decisions_and_quantities):  
    """  
    Determines the majority decision (buy, sell, or hold) and returns the weighted median quantity for the chosen action.  
    Groups 'strong buy' with 'buy' and 'strong sell' with 'sell'.
    Applies weights to quantities based on strategy coefficients.  
    """  
    buy_decisions = ['buy', 'strong buy']  
    sell_decisions = ['sell', 'strong sell']  

    weighted_buy_quantities = []
    weighted_sell_quantities = []
    buy_weight = 0
    sell_weight = 0
    hold_weight = 0
  
    # Process decisions with weights
    for decision, quantity, weight in decisions_and_quantities:
        if decision in buy_decisions:
            weighted_buy_quantities.extend([quantity * weight])
            buy_weight += weight
        elif decision in sell_decisions:
            weighted_sell_quantities.extend([quantity * weight])
            sell_weight += weight
        elif decision == 'hold':
            hold_weight += weight
  
    # Determine the majority decision based on the highest accumulated weight
    if buy_weight > sell_weight and buy_weight > hold_weight:
        return 'buy', median(weighted_buy_quantities) if weighted_buy_quantities else 0
    elif sell_weight > buy_weight and sell_weight > hold_weight:
        return 'sell', median(weighted_sell_quantities) if weighted_sell_quantities else 0
    else:
        return 'hold', 0

def main():
    """
    Main function to control the workflow based on the market's status.
    """
    ndaq_tickers = []
    early_hour_first_iteration = True
    post_hour_first_iteration = True
    client = RESTClient(api_key=POLYGON_API_KEY)
    trading_client = TradingClient(API_KEY, API_SECRET)
    data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
    mongo_client = MongoClient(mongo_url)
    db = mongo_client.assets
    asset_collection = db.asset_quantities
    strategy_to_coefficient = {}
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
                    """
                    use weight from each strategy to determine how much each decision will be weighed. weights will be in decimal
                    """
                    
                    for strategy in strategies:
                        
                        decision, quantity, _ = strategy(ticker, current_price, historical_data,
                                                      buying_power, portfolio_qty, portfolio_value)
                        weight = strategy_to_coefficient[strategy.__name__]
                        decisions_and_quantities.append((decision, quantity, weight))
                    decision, quantity = weighted_majority_decision_and_median_quantity(decisions_and_quantities)
                    
                    
                    """
                    later we should implement buying_power regulator depending on vix strategy
                    for now in bull: 15000
                    for bear: 5000
                    """
                    if decision == "buy" and buying_power > 15000:
                        order = place_order(trading_client, ticker, OrderSide.BUY, qty=quantity, mongo_url=mongo_url)  # Place order using helper
                        if asset_collection.find_one({'symbol': ticker}):
                            asset_collection.update_one({'symbol': ticker}, {'$set': {'qty': portfolio_qty + quantity}})
                        else:
                            asset_collection.insert_one({'symbol': ticker, 'qty': quantity})
                        
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
            if early_hour_first_iteration:
                ndaq_tickers = get_ndaq_tickers(mongo_url)
                ndaq_tickers = get_ndaq_tickers(mongo_url)
                sim_db = mongo_client.trading_simulator
                rank_collection = sim_db.rank
                r_t_c_collection = sim_db.rank_to_coefficient
                for strategy in strategies:
                    rank = rank_collection.find_one({'strategy': strategy.__name__})['rank']
                    coefficient = r_t_c_collection.find_one({'rank': rank})['coefficient']
                    strategy_to_coefficient[strategy.__name__] = coefficient
                    early_hour_first_iteration = False
                    post_hour_first_iteration = True
            logging.info("Market is in early hours. Waiting for 60 seconds.")
            time.sleep(60)

        elif status == "closed":
            if post_hour_first_iteration:
                early_hour_first_iteration = True
                post_hour_first_iteration = False
            logging.info("Market is closed. Performing post-market operations.")
            time.sleep(60)
        else:
            logging.error("An error occurred while checking market status.")
            time.sleep(60)

if __name__ == "__main__":
    main()