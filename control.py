# This file is simply to fine tune parameters and switch modes

# general parameters
"""
mode is switched between 'train', 'test', 'live'
'train' means running ranking_client.py and getting updated trading_simulator. 
There will be an option to:
 - update your database if this is the data you want to insert into the database given better results during test
 - save this model to run testing before you decide to update your database
 - delete this model to start with a new model
'test' means running running your trained bot.
'live' means running your bot in live trading mode.
The default for both rank_mode and trade_mode is 'live'
"""

# helper_files/client_helper.py
"""
stop loss is the percentage of loss you are willing to take before you sell your asset
take profit is the percentage of profit you are willing to take before you sell your asset
these parameters are useful to fine tune your bot
0.03 stop loss means after 3% loss, you will sell your asset
0.05 take profit means after 5% profit, you will sell your asset
"""
stop_loss = 0.03
take_profit = 0.05


# ranking_client.py parameters

rank_mode = 'live'

"""
time_delta_mode can be multiplicative, additive, or balanced. Additive results in less overfitting but could result in underfitting as time goes on
Multiplicative results in more overfitting but less underfitting as time goes on. Balanced results in a mix of both where time_delta is going to be a fifth of what the current timestamp is
and added to time_Delta so it is less overfitting and less underfitting as time goes on.
time_delta_increment is used for additive purpose
time_delta_multiplicative is used for multiplicative purpose
time_delta_balanced is used for balanced purpose - 0.2 means 0.8 is data influence and 0.2 is current influence
"""
time_delta_mode = 'additive'
time_delta_increment = 0.01
time_delta_multiplicative = 1.01
time_delta_balanced = 0.2

"""
rank_liquidity_limit is the amount of money you are telling the bot to reserve during ranking. 
All bots start with a default of 50000 as liquidity with limit as specified here. This is for the ranking client. 
"""
rank_liquidity_limit = 15000

"""
rank_asset_limit to portfolio is how much asset you are allowed to hold in comparison to portfolio value for the ranking client
The lower this number, the more diversification you will have in your portfolio. The higher the number, 
the less diversification you will have but it will be buying more selective assets.
"""
rank_asset_limit = 0.1

"""
profit_price_change_ratio_(d1 - d2) is at what price ratio you should reward each strategy
profit_profit_time_(d1 - d2) is how much reward you should give to the strategy.
For example profit_price_change_ratio_d1 = 1.01 and profit_profit_time_d1 = 1.1 means that if 
the price of the asset goes up but less than by 1% in the trade during sell, 
you should reward the strategy by multiple of time_delta * 1.1
profit_price_delta_else is the reward you should give to the strategy is it exceeds profit_price_change_ratio_d2
"""
profit_price_change_ratio_d1 = 1.05
profit_profit_time_d1 = 1
profit_price_change_ratio_d2 = 1.1
profit_profit_time_d2 = 1.5
profit_profit_time_else = 1.2

"""
loss_price_change_ratio_(d1 - d2) defines at what price ratio you should penalize each strategy.  
loss_profit_time_(d1 - d2) determines how much penalty you should give to the strategy.  
For example, loss_price_change_ratio_d1 = 0.99 and loss_profit_time_d1 = 1 means that if  
the price of the asset goes down but by less than 1% in the trade during sell,  
you should penalize the strategy by a multiple of time_delta * 1.  
loss_price_delta_else is the penalty you should apply if the loss exceeds loss_price_change_ratio_d2.
"""
loss_price_change_ratio_d1 = 0.975  
loss_profit_time_d1 = 1   
loss_price_change_ratio_d2 = 0.95  
loss_profit_time_d2 = 1.5  
loss_profit_time_else = 2  


"""
training parameters - run purely on ranking_client.py
period_start and period_end are the start and end date of the period you want to train 
tickers are the tickers you want to train on. please make sure that during the periods you train, the tickers exist
at current moment and during the period you train
otherwise, the bot will not be able to train on the data. 
also, please make sure the period_start date is at least 2 years after the IPO date of the ticker
please keep in mind training takes quite a long time. Our team trained it on a 1m tick, but even on a 1d tick, it takes a really long time
so please understand the time it takes to train.
"""
period_start = "2012-01-01"
period_end = "2021-12-31"
train_tickers = ["MSFT", "TSLA", "AMZN", "AAPL", "GOOGL", "GOOG", "NFLX", "AVGO", "AMD", "NVDA"]

# trading_client.py parameters
trade_mode = 'live'

"""
trade_liquidity_limit is the amount of money you are telling the bot to reserve during ranking. 
All bots start with a default of 50000. This is for the trading client. Please try not to change this.
If you do, the suggestion for bottom limit is 20% of the portfolio value. 
"""
trade_liquidity_limit = 15000

"""
trade_asset_limit to portfolio is how much asset you are allowed to hold in comparison to portfolio value for the trading client
The lower this number, the more diversification you will have in your portfolio. The higher the number, 
the less diversification you will have but it will be buying more selective assets.
Thsi will also be reflected in Ta-Lib for suggestion and could also affect ranking as well in terms of asset_limit
"""
trade_asset_limit = 0.1

"""
suggestion heap is used in case of when the trading system becomes overpragmatic. This is at what buy_weight limit should the ticker be considered for suggestion
to buy if the system is pragmatic on all other tickers.
"""
suggestion_heap_limit = 1000000

"""
when we train, it will be running ranking_client.py

when we backtest, it will be running training_client.pt and ranking_client.py simultaenously
"""