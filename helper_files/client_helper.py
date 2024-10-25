# client_helper.py

from pymongo import MongoClient
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import logging

# MongoDB connection helper
def connect_to_mongo(mongo_url):
    """Connect to MongoDB and return the client."""
    return MongoClient(mongo_url)

# Helper to place an order
def place_order(trading_client, symbol, side, qty, mongo_url):
    """
    Place a market order and log the order to MongoDB.

    :param trading_client: The Alpaca trading client instance
    :param symbol: The stock symbol to trade
    :param side: Order side (OrderSide.BUY or OrderSide.SELL)
    :param qty: Quantity to trade
    :param mongo_url: MongoDB connection URL
    :return: Order result from Alpaca API
    """
    market_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    order = trading_client.submit_order(market_order_data)
    qty = round(qty, 3)

    # Log trade details to MongoDB
    mongo_client = connect_to_mongo(mongo_url)
    db = mongo_client.trades
    db.paper.insert_one({
        'symbol': symbol,
        'qty': qty,
        'side': side.name,
        'time_in_force': TimeInForce.DAY.name,
        'time': datetime.now()
    })
    mongo_client.close()
    
    return order

# Helper to retrieve NASDAQ-100 tickers from MongoDB
def get_ndaq_tickers(mongo_url):
    """
    Connects to MongoDB and retrieves NASDAQ-100 tickers.

    :param mongo_url: MongoDB connection URL
    :return: List of NASDAQ-100 ticker symbols.
    """
    mongo_client = connect_to_mongo(mongo_url)
    tickers = [stock['symbol'] for stock in mongo_client.stock_list.ndaq100_tickers.find()]
    mongo_client.close()
    return tickers

# Market status checker helper
def market_status(polygon_client):
    """
    Check market status using the Polygon API.

    :param polygon_client: An instance of the Polygon RESTClient
    :return: Current market status ('open', 'early_hours', 'closed')
    """
    try:
        status = polygon_client.get_market_status()
        if status.exchanges.nasdaq == "open" and status.exchanges.nyse == "open":
            return "open"
        elif status.early_hours:
            return "early_hours"
        else:
            return "closed"
    except Exception as e:
        logging.error(f"Error retrieving market status: {e}")
        return "error"
