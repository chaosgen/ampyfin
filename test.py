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

# MongoDB connection string
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"

# Function to place a market order
def place_order(trading_client, symbol, side, qty=1):
    market_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    order = trading_client.submit_order(market_order_data)

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
            pass  # Error for selling without quantity
    else:
        # If record exists, update the quantity and most recent trade information
        current_qty = symbol_quantities['qty']
        if side == OrderSide.BUY:
            new_qty = current_qty + qty
        elif side == OrderSide.SELL:
            new_qty = current_qty - qty
            if new_qty < 0:
                return None  # Error for attempting to sell more than owned

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
    except Exception:
        return

    try:
        # MongoDB connection details
        mongo_client = MongoClient(mongo_url)
        db = mongo_client.stock_list
        ndaq100_tickers = db.ndaq100_tickers

        ndaq100_tickers.delete_many({})  # Clear existing data
        ndaq100_tickers.insert_many(ndaq_stocks)  # Insert new data
    except Exception:
        pass
    finally:
        mongo_client.close()


# Function to check the current market status (open, closed, early hours)
def market_status(client):
    """
    Checks the current market status by querying the Polygon API.

    :param client: An instance of the Polygon RESTClient.
    :return: A string indicating the current market status ('open', 'early_hours', 'closed').
    """
    try:
        status = client.get_market_status()  # Get market status
        if status.exchanges.nasdaq == "open" and status.exchanges.nyse == "open":
            return "open"
        elif status.early_hours:
            return "early_hours"
        else:
            return "closed"
    except Exception:
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

    # MongoDB connection setup
    mongo_client = MongoClient(mongo_url)
    db = mongo_client.assets
    asset_collection = db.asset_quantities

    while True:
        status = market_status(client)

        if status == "open":
            """
            insert time.sleep for 30 minutes before trading to avoid volatility in morning
            """
            # Fetch NASDAQ 100 tickers if not initialized
            if not ndaq_tickers:
                call_ndaq_100()
                ndaq_tickers = get_ndaq_tickers()
            account = trading_client.get_account()
            buying_power = float(account.cash)
            portfolio_value = float(account.portfolio_value)
            
            time.sleep(60)  # Pause for a minute before the next check

        elif status == "early_hours":
            if not early_hour_first_iteration:
                early_hour_first_iteration = True
                call_ndaq_100()
                ndaq_tickers = get_ndaq_tickers()
            time.sleep(60)  # Sleep during early hours

        elif status == "closed":
            time.sleep(60)  # Sleep when the market is closed

        else:
            time.sleep(60)  # Sleep in case of error

if __name__ == "__main__":
    ticker_yahoo = yf.Ticker("AAPL")
    data = ticker_yahoo.history()
    last_quote = data['Close'].iloc[-1]
    print(last_quote)
