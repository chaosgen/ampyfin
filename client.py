from polygon import RESTClient
from config import POLYGON_API_KEY, FINANCIAL_PREP_API_KEY, MONGO_DB_USER, MONGO_DB_PASS, API_KEY, API_SECRET, BASE_URL
import json
import certifi
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from pymongo import MongoClient
import time
from datetime import datetime, timedelta
import alpaca
from alpaca.trading.client import TradingClient
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.stream import TradingStream
from alpaca.data.live.stock import StockDataStream
from alpaca.data.requests import (
    StockBarsRequest,
    StockTradesRequest,
    StockQuotesRequest
)
from alpaca.trading.requests import (
    GetAssetsRequest, 
    MarketOrderRequest, 
    LimitOrderRequest, 
    StopOrderRequest, 
    StopLimitOrderRequest, 
    TakeProfitRequest, 
    StopLossRequest, 
    TrailingStopOrderRequest, 
    GetOrdersRequest, 
    ClosePositionRequest
)
from alpaca.trading.enums import ( 
    AssetStatus, 
    AssetExchange, 
    OrderSide, 
    OrderType, 
    TimeInForce, 
    OrderClass, 
    QueryOrderStatus
)
from alpaca.common.exceptions import APIError
import trading_strategies
import yfinance as yf
import logging
from collections import Counter

# MongoDB connection string
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"

# Set up logging configuration
# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('system.log'),  # Log messages to a file
        logging.StreamHandler()               # Log messages to the console
    ]
)


# Function to place a market order
def place_order(trading_client, symbol, side, qty=1.0):
    market_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    order = trading_client.submit_order(market_order_data)
    qty = round(qty, 3)
    # MongoDB connection
    mongo_client = MongoClient(mongo_url)
    db = mongo_client.trades
    paper_trades = db.paper
    paper_trades.insert_one({
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'time_in_force': TimeInForce.DAY,
        'time': datetime.now()  # Store the current timestamp of the trade
    })

    db = mongo_client.assets
    asset_quantities = db.asset_quantities
    symbol_quantities = asset_quantities.find_one({'symbol': symbol})

    if symbol_quantities is None:
        # If no record for this symbol exists, insert a new one
        if side == OrderSide.BUY:
            asset_quantities.insert_one({
                'symbol': symbol,
                'qty': qty,
                'most_recent_trade': side.name,  # Store "BUY" or "SELL"
                'most_recent_time': datetime.now()  # Store the current time
            })
        else:
            logging.error(f"Attempting to sell {symbol}, but no quantity exists in the database.")
    else:
        # If record exists, update the quantity and most recent trade information
        current_qty = symbol_quantities['qty']
        if side == OrderSide.BUY:
            new_qty = current_qty + qty
        elif side == OrderSide.SELL:
            new_qty = current_qty - qty
            if new_qty < 0:
                logging.error(f"Attempting to sell more {symbol} than owned. Current qty: {current_qty}, trying to sell: {qty}.")
                mongo_client.close()
                return None

        # Update the database with the new quantity, most recent trade, and trade time
        asset_quantities.update_one(
            {'symbol': symbol},
            {
                '$set': {
                    'qty': new_qty,
                    'most_recent_trade': side.name,  # Update to "BUY" or "SELL"
                    'most_recent_time': datetime.now()  # Update the trade time
                }
            }
        )

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



def majority_decision_and_min_quantity(decisions_and_quantities):
    """
    Given a list of tuples with decisions ('buy', 'sell', 'hold') and corresponding quantities,
    this function returns a buy decision if there are 2 or more buys, a sell decision if there are 2 or more sells,
    and a hold decision otherwise. It also returns the minimum quantity among strategies that agree on the decision.

    :param decisions_and_quantities: List of tuples [(decision, quantity), ...]
    :return: Tuple of decision and corresponding minimum quantity
    """
    # Extract decisions and quantities
    decisions = [dq[0] for dq in decisions_and_quantities]
    
    # Count occurrences of each decision (buy, sell, hold)
    decision_count = Counter(decisions)
    
    # Check for buy decision (2 or more buys)
    if decision_count['buy'] >= 2:
        min_quantity = min(q for d, q in decisions_and_quantities if d == 'buy')
        return 'buy', min_quantity
    
    # Check for sell decision (2 or more sells)
    elif decision_count['sell'] >= 2:
        min_quantity = min(q for d, q in decisions_and_quantities if d == 'sell')
        return 'sell', min_quantity
    
    # If neither buy nor sell has 2 or more votes, hold
    else:
        return 'hold', 0


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
    
    # MongoDB connection setup
    mongo_client = MongoClient(mongo_url)
    db = mongo_client.assets
    asset_collection = db.asset_quantities
    
    while True:
        status = market_status(client)

        if status == "open":
            logging.info("Market is open. Waiting for 60 seconds.")
            # Fetch NASDAQ 100 tickers if not initialized
            if not ndaq_tickers:
                call_ndaq_100()
                ndaq_tickers = get_ndaq_tickers()
            account = trading_client.get_account()
            
            for ticker in ndaq_tickers:
                decisions_and_quantities = []
                buying_power = float(account.cash)
                portfolio_value = float(account.portfolio_value)
                cash_to_portfolio_ratio = buying_power / portfolio_value
                
                
                
                try:
                    # Fetch historical data for the ticker
                    historical_data = trading_strategies.get_historical_data(ticker, data_client)

                    # Get the latest price
                    ticker_yahoo = yf.Ticker(ticker)
                    data = ticker_yahoo.history()
                    current_price = data['Close'].iloc[-1]

                    # Fetch last trade time from MongoDB
                    asset_info = asset_collection.find_one({'symbol': ticker})
                    portfolio_qty = asset_info['qty'] if asset_info else 0.0

                    # Apply 5 trading strategies and collect their decisions and quantities
                    for strategy in [trading_strategies.mean_reversion_strategy, trading_strategies.momentum_strategy,
                                     trading_strategies.bollinger_bands_strategy, trading_strategies.rsi_strategy, 
                                     trading_strategies.macd_strategy]:
                        decision, quantity, _ = strategy(ticker, current_price, historical_data, 
                                                      buying_power, portfolio_qty, portfolio_value)
                        
                        decisions_and_quantities.append((decision, quantity))

                    # Determine the majority decision and minimum quantity
                    decision, quantity = majority_decision_and_min_quantity(decisions_and_quantities)

                    # Execute the trade based on the decision and quantity
                    if decision == "buy":
                        if cash_to_portfolio_ratio < 0.4 or buying_power <= 0:
                            logging.warning("Cash to portfolio ratio is below 0.4, delaying trades.")
                        else:
                            order = place_order(trading_client, ticker, OrderSide.BUY, qty=quantity)
                            logging.info(f"Executed BUY order for {ticker}: {order}")
                    
                    elif decision == "sell":
                        if portfolio_qty > 0:  # Only sell if holding shares
                            order = place_order(trading_client, ticker, OrderSide.SELL, qty=quantity)
                            logging.info(f"Executed SELL order for {ticker}: {order}")
                        else:
                            logging.warning(f"No shares to sell for {ticker}. Skipping sell.")
                    else:
                        logging.info(f"Holding for {ticker}, no action taken.")
                
                except Exception as e:
                    logging.error(f"Error processing {ticker}: {e}")

            time.sleep(60)  # Sleep for 1 minute after trading

        elif status == "early_hours":
            if not early_hour_first_iteration:
                logging.info("Fetching NASDAQ 100 tickers.")
                call_ndaq_100()
                ndaq_tickers = get_ndaq_tickers()
                early_hour_first_iteration = True
            logging.info("Market is in early hours. Waiting for 60 seconds.")
            time.sleep(60)

        elif status == "closed":
            logging.info("Market is closed. Performing post-market analysis.")
            time.sleep(60)
        else:
            logging.error("An error occurred while checking market status.")
            time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    main()