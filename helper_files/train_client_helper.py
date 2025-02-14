from datetime import timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def get_historical_data(ticker, current_date, period, ticker_price_history):
        period_start_date = {
            "1mo": current_date - timedelta(days=30),
            "3mo": current_date - timedelta(days=90),
            "6mo": current_date - timedelta(days=180),
            "1y": current_date - timedelta(days=365),
            "2y": current_date - timedelta(days=730)
        }
        start_date = period_start_date[period]
        
        return ticker_price_history[ticker].loc[start_date.strftime('%Y-%m-%d'):current_date.strftime('%Y-%m-%d')]
    
def local_update_portfolio_values(current_date, strategies, trading_simulator, ticker_price_history):
    active_count = 0
    for strategy in strategies:
        trading_simulator[strategy.__name__]["portfolio_value"] = trading_simulator[strategy.__name__]["amount_cash"]
        """
        update portfolio value here
        """
        amount = 0
        for ticker in trading_simulator[strategy.__name__]["holdings"]:
            qty = trading_simulator[strategy.__name__]["holdings"][ticker]["quantity"]
            current_price = ticker_price_history[ticker].loc[current_date.strftime('%Y-%m-%d')]["Close"]
            amount += qty * current_price
        cash = trading_simulator[strategy.__name__]["amount_cash"]
        trading_simulator[strategy.__name__]["portfolio_value"] = amount + cash
        if trading_simulator[strategy.__name__]["portfolio_value"] != 50000:
            active_count += 1
    return active_count, trading_simulator

def calculate_metrics(account_values):
    # Fill non-leading NA values with the previous value using 'ffill' (forward fill)
    account_values_filled = account_values.fillna(method='ffill')
    returns = account_values_filled.pct_change().dropna()
    # Sharpe Ratio
    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
    
    # Sortino Ratio
    downside_returns = returns[returns < 0]
    sortino_ratio = returns.mean() / downside_returns.std() * np.sqrt(252)
    
    # Max Drawdown
    cumulative = (1 + returns).cumprod()
    max_drawdown = (cumulative.cummax() - cumulative).max()
    
    # R Ratio
    r_ratio = returns.mean() / returns.std()
    
    return {
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'r_ratio': r_ratio
    }

def plot_cash_growth(account_values):
    account_values = account_values.interpolate(method='linear')  # Fill missing values by linear interpolation
    plt.figure(figsize=(10, 6))
    plt.plot(account_values.index, account_values.values, label='Account Cash Growth')
    plt.xlabel('Date')
    plt.ylabel('Account Value')
    plt.title('Account Cash Growth Over Time')
    plt.legend()
    plt.grid(True)
    plt.show()

def generate_tear_sheet(account_values, metrics):
    account_values = account_values.interpolate(method='linear')  # Fill missing values by linear interpolation
    fig, ax = plt.subplots(2, 1, figsize=(10, 12))
    
    # Plot account cash growth
    ax[0].plot(account_values.index, account_values.values, label='Account Portfolio Value')
    ax[0].set_xlabel('Date')
    ax[0].set_ylabel('Account Value')
    ax[0].set_title('Portfolio Value')
    ax[0].legend()
    ax[0].grid(True)
    
    # Display metrics
    metrics_text = '\n'.join([f'{k}: {v:.4f}' for k, v in metrics.items()])
    ax[1].text(0.5, 0.5, metrics_text, fontsize=12, ha='center', va='center', transform=ax[1].transAxes)
    ax[1].axis('off')
    
    plt.tight_layout()
    plt.show()