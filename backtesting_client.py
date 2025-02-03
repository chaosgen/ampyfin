import yfinance as yf
import pandas as pd
from pymongo import MongoClient
import certifi
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
from config import mongo_url
from strategies.talib_indicators import *
from trading_client import weighted_majority_decision_and_median_quantity
from setup import indicator_periods  # Importing indicator_periods from setup.py
from helper_files.client_helper import strategies

# Define the tickers for FAANG stocks, Microsoft, and TSLA
tickers = ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL', 'MSFT', 'TSLA']

# Define the start and end dates for the price history
start_date = '2020-01-01'
end_date = '2022-01-01'

# Dictionary to store the price history
price_history = {}

# Download historical data for each ticker
for ticker in tickers:
    data = yf.download(ticker, start=start_date, end=end_date, interval='1d')
    price_history[ticker] = data

# Connect to MongoDB
ca = certifi.where()
client = MongoClient(mongo_url, tlsCAFile=ca)

# Define the database and collections
db = client.trading_simulator
holdings_collection = db.algorithm_holdings
points_collection = db.points_tally
time_delta_collection = db.time_delta
rank_to_coefficient_collection = db.rank_to_coefficient
rank_collection = db.rank
indicator_collection = db.IndicatorsDatabase.Indicators

# Fetch data from MongoDB and store in dictionaries
holdings_data = {}
points_data = {}
time_delta_data = {}
rank_to_coefficient_data = {}
rank_data = {}

# Fetch algorithm holdings
for strategy_doc in holdings_collection.find({}):
    strategy_name = strategy_doc["strategy"]
    holdings_data[strategy_name] = {
        "amount_cash": strategy_doc["amount_cash"],
        "portfolio_value": strategy_doc["portfolio_value"],
        "holdings": strategy_doc["holdings"]
    }

# Fetch points tally
for points_doc in points_collection.find({}):
    strategy_name = points_doc["strategy"]
    points_data[strategy_name] = {
        "total_points": points_doc["total_points"],
        "successful_trades": points_doc.get("successful_trades", 0),
        "failed_trades": points_doc.get("failed_trades", 0),
        "neutral_trades": points_doc.get("neutral_trades", 0)
    }

# Fetch time delta
time_delta_doc = time_delta_collection.find_one({})
if time_delta_doc:
    time_delta_data = {
        "time_delta": time_delta_doc["time_delta"]
    }

# Fetch rank to coefficient
for rank_to_coefficient_doc in rank_to_coefficient_collection.find({}):
    rank = rank_to_coefficient_doc["rank"]
    rank_to_coefficient_data[rank] = {
        "coefficient": rank_to_coefficient_doc["coefficient"]
    }

# Fetch rank
for rank_doc in rank_collection.find({}):
    strategy_name = rank_doc["strategy"]
    rank_data[strategy_name] = {
        "rank": rank_doc["rank"]
    }

# Function to simulate a trading strategy


# Function to fetch historical data and simulate strategy
def simulate_strategy_for_day(strategy, ticker, current_price, date, holdings, buying_power, portfolio_qty, portfolio_value):
    historical_data = None
    while historical_data is None:
        try:
            # Get the ideal period for the indicator
            period = indicator_periods[strategy.__name__]
            
            historical_data = get_data(ticker, client, period=period)
        except Exception as e:
            print(f"Error fetching data for {ticker} with strategy {strategy.__name__}: {e}. Retrying...")
    
    decision, quantity = simulate_strategy(strategy, ticker, current_price, historical_data, buying_power, portfolio_qty, portfolio_value)
    print(f"Strategy: {strategy.__name__}, Ticker: {ticker}, Date: {date}, Decision: {decision}, Quantity: {quantity}")
    return decision, quantity

# Function to simulate trade for a given day
def simulate_trade_for_day(date):
    for ticker in tickers:
        price = price_history[ticker].loc[date, 'Close']
        if price is not np.nan:
            decisions_and_quantities = []
            for strategy in strategies:
                decision, quantity = simulate_strategy_for_day(strategy, ticker, price, date, holdings_data[strategy], holdings_data[strategy]['amount_cash'], holdings_data[strategy]['holdings'].get(ticker, {}).get('quantity', 0), holdings_data[strategy]['portfolio_value'])
                
                weight = rank_to_coefficient_data[rank_data[strategy.__name__]]['coefficient']
                decisions_and_quantities.append((decision, quantity, weight))
            
            decision, quantity, buy_weight, sell_weight, hold_weight = weighted_majority_decision_and_median_quantity(decisions_and_quantities)
            
            if decision == 'buy':
                total_cash = sum(holdings_data[strategy]['amount_cash'] for strategy in holdings_data.keys())
                total_portfolio_value = sum(holdings_data[strategy]['portfolio_value'] for strategy in holdings_data.keys())
                if quantity * price <= total_cash:
                    for strategy in holdings_data.keys():
                        strategy_cash = holdings_data[strategy]['amount_cash']
                        strategy_investment = (strategy_cash / total_cash) * (quantity * price)
                        holdings_data[strategy]['amount_cash'] -= strategy_investment
                        if ticker in holdings_data[strategy]['holdings']:
                            holdings_data[strategy]['holdings'][ticker]['quantity'] += int(strategy_investment // price)
                        else:
                            holdings_data[strategy]['holdings'][ticker] = {'quantity': int(strategy_investment // price), 'price': price}
                        holdings_data[strategy]['portfolio_value'] = holdings_data[strategy]['amount_cash'] + sum(holding['quantity'] * price for holding in holdings_data[strategy]['holdings'].values())
            
            elif decision == 'sell':
                total_qty = sum(holdings_data[strategy]['holdings'].get(ticker, {}).get('quantity', 0) for strategy in holdings_data.keys())
                if quantity <= total_qty:
                    for strategy in holdings_data.keys():
                        strategy_qty = holdings_data[strategy]['holdings'].get(ticker, {}).get('quantity', 0)
                        strategy_sale_qty = (strategy_qty / total_qty) * quantity
                        holdings_data[strategy]['amount_cash'] += strategy_sale_qty * price
                        holdings_data[strategy]['holdings'][ticker]['quantity'] -= strategy_sale_qty
                        if holdings_data[strategy]['holdings'][ticker]['quantity'] <= 0:
                            del holdings_data[strategy]['holdings'][ticker]
                        holdings_data[strategy]['portfolio_value'] = holdings_data[strategy]['amount_cash'] + sum(holding['quantity'] * price for holding in holdings_data[strategy]['holdings'].values())

    # Simulate ranking for the day
    daily_rank_data = {}
    for strategy, points in points_data.items():
        daily_rank_data[strategy] = points['total_points'] + holdings_data[strategy]['portfolio_value']

    sorted_rank_data = sorted(daily_rank_data.items(), key=lambda x: x[1], reverse=True)
    for rank, (strategy, _) in enumerate(sorted_rank_data, start=1):
        rank_data[strategy] = rank

    # Update time delta
    time_delta_data["time_delta"] += 0.01

# Initialize a dictionary to store portfolio values over time
portfolio_values_over_time = {strategy: [] for strategy in holdings_data.keys()}

# Simulate trading for each day
for date in price_history[tickers[0]].index:
    simulate_trade_for_day(date)
    for strategy in holdings_data.keys():
        portfolio_values_over_time[strategy].append(holdings_data[strategy]['portfolio_value'])

# Function to calculate performance metrics
def calculate_metrics(portfolio_values):
    returns = np.diff(portfolio_values) / portfolio_values[:-1]
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
    sortino_ratio = np.mean(returns) / np.std(returns[returns < 0]) * np.sqrt(252)
    max_drawdown = np.min(portfolio_values) / np.max(portfolio_values) - 1
    r_ratio = np.mean(returns) / np.mean(np.abs(returns))
    return sharpe_ratio, sortino_ratio, max_drawdown, r_ratio

# Calculate and print final metrics
print("\nFinal Metrics:")
for strategy in holdings_data.keys():
    portfolio_values = portfolio_values_over_time[strategy]
    sharpe_ratio, sortino_ratio, max_drawdown, r_ratio = calculate_metrics(portfolio_values)
    percentage_profit = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0] * 100
    print(f"Strategy: {strategy}")
    print(f"  Percentage Profit: {percentage_profit:.2f}%")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"  Sortino Ratio: {sortino_ratio:.2f}")
    print(f"  R Ratio: {r_ratio:.2f}")
    print(f"  Maximum Drawdown: {max_drawdown:.2f}")
    print()

# Plot the portfolio values over time
plt.figure(figsize=(12, 6))
for strategy in holdings_data.keys():
    plt.plot(price_history[tickers[0]].index, portfolio_values_over_time[strategy], label=strategy)
plt.title('Portfolio Value Over Time')
plt.xlabel('Date')
plt.ylabel('Portfolio Value')
plt.legend()
plt.show()