import unittest
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from trading_strategies import (
    random_forest_strategy,
    momentum_strategy,
    mean_reversion_strategy,
    neural_network_strategy,
    rsi_strategy,
)
from pymongo import MongoClient
from config import MONGO_DB_USER, MONGO_DB_PASS

# MongoDB connection string
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"

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

class TestTradingStrategies(unittest.TestCase):

    def setUp(self):
        self.tickers = get_ndaq_tickers()
        self.account_cash = 10000
        self.portfolio_qty = {}
        self.results = pd.DataFrame(columns=['Ticker', 'Strategy', 'Action', 'Quantity', 'Price', 'Date'])

    def test_trading_strategies(self):
        for ticker in self.tickers:
            try:
                # Fetch historical data
                historical_data = self.get_historical_data(ticker)

                # Check if we have valid historical data
                if historical_data.empty:
                    print(f"No historical data found for {ticker}. Skipping.")
                    continue

                current_price = historical_data['Close'].iloc[-1]  # Latest closing price
                total_portfolio_value = self.account_cash + sum(
                    qty * current_price for qty in self.portfolio_qty.values()
                )  # Calculate total portfolio value

                # Apply different strategies
                for strategy in [
                    random_forest_strategy,
                    momentum_strategy,
                    mean_reversion_strategy,
                    neural_network_strategy,
                    rsi_strategy,
                ]:
                    # Pass parameters in the correct order
                    action, quantity, price = strategy(ticker, current_price, historical_data, self.account_cash, self.portfolio_qty, total_portfolio_value)

                    # Log the results
                    if action in ['buy', 'sell']:
                        self.log_trade(ticker, strategy.__name__, action, quantity, price)

            except Exception as e:
                print(f"Error processing {ticker}: {e}")

    def get_historical_data(self, ticker, days=730):  # Fetch 2 years of data (365 days * 2)
        try:
            # Fetch historical data for the specified number of days
            data = yf.download(ticker, period='2y', interval='1d')  # Use '2y' for two years
            data.reset_index(inplace=True)  # Reset index to have a column for dates
            return data
        except Exception as e:
            print(f"Failed to fetch data for {ticker}: {e}")
            return pd.DataFrame()  # Return an empty DataFrame on failure

    def log_trade(self, ticker, strategy_name, action, quantity, price):
        trade_date = pd.Timestamp.now().date()
        self.results = self.results.append({
            'Ticker': ticker,
            'Strategy': strategy_name,
            'Action': action,
            'Quantity': quantity,
            'Price': price,
            'Date': trade_date
        }, ignore_index=True)

    def plot_results(self):
        # Group results by ticker
        for ticker in self.results['Ticker'].unique():
            ticker_results = self.results[self.results['Ticker'] == ticker]
            plt.figure(figsize=(10, 5))
            plt.title(f'Trading Results for {ticker}')
            plt.plot(ticker_results['Date'], ticker_results['Price'], marker='o', linestyle='-', label='Price')
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()
            plt.show()

if __name__ == '__main__':
    unittest.main()
