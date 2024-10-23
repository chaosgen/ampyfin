import pandas as pd  
from datetime import datetime, timedelta  
from alpaca.data.historical import StockHistoricalDataClient  
from alpaca.data.requests import StockBarsRequest  
from alpaca.data.timeframe import TimeFrame  
from config import API_KEY, API_SECRET  
import trading_strategies  

def get_historical_data(ticker, client, days=100):  
   """  
   Fetch historical bar data for a given stock ticker.  
    
   :param ticker: The stock ticker symbol.  
   :param client: An instance of StockHistoricalDataClient.  
   :param days: Number of days of historical data to fetch.  
   :return: DataFrame with historical stock bar data.  
   """  
   start_time = datetime.now() - timedelta(days=days)  
   request_params = StockBarsRequest(  
      symbol_or_symbols=ticker,  
      timeframe=TimeFrame.Day,  
      start=start_time  
   )  
    
   bars = client.get_stock_bars(request_params)  
   data = bars.df  
   return data  

def test_strategies():  
   # Initialize the StockHistoricalDataClient  
   client = StockHistoricalDataClient(API_KEY, API_SECRET)  
  
   # Define test parameters  
   ticker = "REGN"  
   account_cash = 10000  
   portfolio_qty = 100  
   total_portfolio_value = 100000  
  
   historical_data = get_historical_data(ticker, client) 
   current_price = historical_data['close'].iloc[-1]
   # Test each strategy  
   strategies = [  
      trading_strategies.rsi_strategy,  
      trading_strategies.momentum_strategy,  
      trading_strategies.mean_reversion_strategy,  
      trading_strategies.bollinger_bands_strategy,
      trading_strategies.macd_strategy,
      trading_strategies.triple_moving_average_strategy,
      trading_strategies.volume_price_trend_strategy,
      trading_strategies.keltner_channel_strategy,
      trading_strategies.dual_thrust_strategy,
      trading_strategies.adaptive_momentum_strategy,
      trading_strategies.hull_moving_average_strategy,
      trading_strategies.elder_ray_strategy,
      trading_strategies.chande_momentum_strategy  
   ]  
  
   for strategy in strategies:  
      decision, quantity, ticker = strategy(  
        ticker,  
        current_price,  
        historical_data,  
        account_cash,  
        portfolio_qty,  
        total_portfolio_value  
      )  
       
      print(f"{strategy.__name__}:")  
      print(f"  Decision: {decision}")  
      print(f"  Ticker: {ticker}")  
      print(f"  Quantity: {quantity}")  
      print("__________________________________________________")  
  
if __name__ == "__main__":  
   test_strategies()