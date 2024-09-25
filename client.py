from polygon import RESTClient
from config import POLYGON_API_KEY, FINANCIAL_PREP_API_KEY, MONGO_DB_USER, MONGO_DB_PASS, API_KEY, API_SECRET, BASE_URL
import json
import certifi
from urllib.request import urlopen
from pymongo import MongoClient
import time
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
import logging

# MongoDB connection string
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net?retryWrites=true&writeConcern=majority"

# Set up logging configuration
logging.basicConfig(
    filename='system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Function to place a market order
def place_order(trading_client, symbol, side, qty=1):
    market_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    order = trading_client.submit_order(market_order_data)
    mongo_client = MongoClient(mongo_url)
    db = mongo_client.trades
    paper_trades = db.paper
    paper_trades.insert_one({'symbol': symbol, 'qty': qty, 'side': side, 'time_in_force':TimeInForce.DAY})
    db = mongo_client.assets
    asset_quantities = db.asset_quantities
    symbol_quantities = asset_quantities.find_one({'symbol': symbol})
    
    if symbol_quantities is None:
        # If no record for this symbol exists, insert a new one
        if side == OrderSide.BUY:
            asset_quantities.insert_one({'symbol': symbol, 'qty': qty})
        else:
            logging.error(f"Attempting to sell {symbol}, but no quantity exists in the database.")
    else:
        # If record exists, update the quantity
        current_qty = symbol_quantities['qty']
        if side == OrderSide.BUY:
            new_qty = current_qty + qty
        elif side == OrderSide.SELL:
            new_qty = current_qty - qty
            if new_qty < 0:
                logging.error(f"Attempting to sell more {symbol} than owned. Current qty: {current_qty}, trying to sell: {qty}.")
                mongo_client.close()
                return None
        
        # Update the database with the new quantity
        asset_quantities.update_one({'symbol': symbol}, {'$set': {'qty': new_qty}})
    
    mongo_client.close()
    return order


# DRY Helper function to connect to MongoDB and retrieve NASDAQ-100 tickers
def get_ndaq_tickers():
    """
    Connects to MongoDB, retrieves and returns NASDAQ-100 tickers.

    :return: List of NASDAQ-100 ticker symbols.
    """
    mongo_client = MongoClient(mongo_url)
    db = mongo_client.stock_list
    ndaq100_tickers = db.ndaq100_tickers
    cursor = ndaq100_tickers.find()
    tickers = [stock['symbol'] for stock in cursor]
    mongo_client.close()  # Ensure MongoDB connection is closed
    return tickers

# Function to retrieve and store the list of NASDAQ-100 tickers in MongoDB
def call_ndaq_100():
    """
    Fetches the list of NASDAQ 100 tickers using the Financial Modeling Prep API and stores it in a MongoDB collection.
    The MongoDB collection is cleared before inserting the updated list of tickers.
    """
    logging.info("Calling NASDAQ 100 to retrieve tickers.")

    def get_jsonparsed_data(url):
        """
        Parses the JSON response from the provided URL.
        
        :param url: The API endpoint to retrieve data from.
        :return: Parsed JSON data as a dictionary.
        """
        response = urlopen(url, cafile=certifi.where())
        data = response.read().decode("utf-8")
        return json.loads(data)

    try:
        # API URL for fetching NASDAQ 100 tickers
        ndaq_url = f"https://financialmodelingprep.com/api/v3/nasdaq_constituent?apikey={FINANCIAL_PREP_API_KEY}"
        ndaq_stocks = get_jsonparsed_data(ndaq_url)
        logging.info("Successfully retrieved NASDAQ 100 tickers.")
    except Exception as e:
        logging.error(f"Error fetching NASDAQ 100 tickers: {e}")
        return

    try:
        # MongoDB connection details
        mongo_client = MongoClient(mongo_url)
        db = mongo_client.stock_list
        ndaq100_tickers = db.ndaq100_tickers

        ndaq100_tickers.delete_many({})  # Clear existing data
        ndaq100_tickers.insert_many(ndaq_stocks)  # Insert new data
        logging.info("Successfully inserted NASDAQ 100 tickers into MongoDB.")
    except Exception as e:
        logging.error(f"Error inserting tickers into MongoDB: {e}")
    finally:
        mongo_client.close()
        logging.info("MongoDB connection closed.")

# Function to check the current market status (open, closed, early hours)
def market_status(client):
    """
    Checks the current market status by querying the Polygon API.

    :param client: An instance of the Polygon RESTClient.
    :return: A string indicating the current market status ('open', 'early_hours', 'closed').
    """
    logging.info("Checking market status.")
    try:
        status = client.get_market_status()  # Get market status
        if status.exchanges.nasdaq == "open" and status.exchanges.nyse == "open":
            logging.info("Market is open.")
            return "open"
        elif status.early_hours:
            logging.info("Market is in early hours.")
            return "early_hours"
        else:
            logging.info("Market is closed.")
            return "closed"
    except Exception as e:
        logging.error(f"Error retrieving market status: {e}")
        return "error"

# Main function that runs continuously, checking market status and executing trades or calculations
def main():
    """
    Main function to control the workflow based on the market's status.

    - If 'open': Execute trading strategies.
    - If 'early_hours': Fetch NASDAQ 100 tickers and perform premarket operations.
    - If 'closed': Perform post-market analysis or calculations.
    """
    ndaq_tickers = []
    early_hour_first_iteration = False
    client = RESTClient(api_key=POLYGON_API_KEY)
    trading_client = TradingClient(API_KEY, API_SECRET)
    data_client = StockHistoricalDataClient(API_KEY, API_SECRET)

    while True:
        status = market_status(client)

        if status == "open":
            logging.info("Market is open. Waiting for 60 seconds.")
            # Fetch NASDAQ 100 tickers if not initialized
            if not ndaq_tickers:
                call_ndaq_100()
                ndaq_tickers = get_ndaq_tickers()
            account = trading_client.get_account()
            buying_power = float(account.cash)
            portfolio_value = float(account.portfolio_value)

            cash_to_portfolio_ratio = buying_power/portfolio_value

            for ticker in ndaq_tickers:
                buy_order = place_order(trading_client, ticker, OrderSide.BUY, 1)
                logging.info(buy_order)
            

            time.sleep(60)  # Wait for 60 seconds before the next iteration

        elif status == "early_hours":
            if not early_hour_first_iteration:
                logging.info("Early hours detected. Fetching NASDAQ 100 tickers.")
                call_ndaq_100()
                ndaq_tickers = get_ndaq_tickers()
                early_hour_first_iteration = True
            
            time.sleep(60)  # Wait for 60 seconds before the next check

        else:
            # Reset for early hours operations
            early_hour_first_iteration = False
            ndaq_tickers = []
            logging.info("Market is closed or in error state. Waiting for 60 seconds.")
            # Add post-market analysis or AI-driven strategy here

            time.sleep(60)  # Wait for 60 seconds before the next check

if __name__ == "__main__":
    main()  # Entry point for the script
