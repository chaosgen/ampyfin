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
import strategies.new_trading_strategies as trading_strategies
import math
import yfinance as yf
import logging
from collections import Counter
from trader_client import market_status
from helper_files.client_helper import get_ndaq_tickers

# Connect to MongoDB  
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"

def insert_rank_to_coefficient(i):
    """
    currently i is at 50
    next i is at 51
    """
    client = MongoClient(mongo_url)  
    db = client.trading_simulator 
    collections  = db.rank_to_coefficient
    e = math.e
    rate = (e**e)/(e**2) - 1
    coefficient = rate**(2 * i)
    collections.insert_one(
        {f'{i}' : coefficient

        }
    )
    client.close()


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
                    historical_data = trading_strategies.get_historical_data(ticker, data_client)
                    ticker_yahoo = yf.Ticker(ticker)
                    data = ticker_yahoo.history()
                    current_price = data['Close'].iloc[-1]

                    asset_info = asset_collection.find_one({'symbol': ticker})
                    portfolio_qty = asset_info['qty'] if asset_info else 0.0

                    for strategy in [trading_strategies.mean_reversion_strategy, trading_strategies.momentum_strategy,
                                     trading_strategies.bollinger_bands_strategy, trading_strategies.rsi_strategy, 
                                     trading_strategies.macd_strategy]:
                        decision, quantity, _ = strategy(ticker, current_price, historical_data,
                                                      buying_power, portfolio_qty, portfolio_value)
                        decisions_and_quantities.append((decision, quantity))

                    

                    """
                    insert logic here
                    """

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