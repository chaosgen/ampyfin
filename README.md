# AmpyFin Trading Bot
![](logo.png)

## Overview

AmpyFin Trading Bot is a high-performance NASDAQ-100 trading bot that uses a ranked ensemble learning system with 50 trading algorithms. Each algorithm's rank dynamically adjusts based on the profitability of hypothetical buy/sell decisions, optimizing final trading decisions. The bot is configured for paper trading by default, allowing for safe testing and refinement of strategies. Transitioning to live trading is as simple as updating API keys and adjusting configuration settings.

## Features

- **NASDAQ-100 Ticker Retrieval**: Fetches tickers using the Financial Modeling Prep API during early market hours.
- **Market Status Monitoring**: Checks market status in real-time (open, closed, premarket) with the Polygon API.
- **Algorithm Ranking System**: Adjusts algorithm rankings based on performance to optimize trading decisions.
- **Paper Trading**: Safe testing environment, with live trading option available via configuration.
- **Data Storage**: Utilizes MongoDB for secure storage of ticker data and trading activity logs.
- **Customizable**: Allows for the extension of trading strategies and configurations.

## Algorithm Ranking System

Each trading algorithm starts with a base score of 0. Rankings are updated dynamically based on the algorithm’s profitability, using a coefficient calculated as:

$$
\left( \frac{e^e}{e^2 - 1} \right)^{2i}
$$

where \(i\) is the inverse of the algorithm’s ranking. This creates a system where the highest-ranked algorithms contribute more heavily to the bot’s decisions, adapting to changing market conditions.

## File Structure and Objectives

### `client.py`
- **Objective**: Orchestrates both trading and ranking clients.
- **Features**:
  - Initiates trading and ranking clients at appropriate times.
  - Ensures trading operations during premarket and market hours.
  - Includes error handling and logs system performance.

### `trading_client.py`
- **Objective**: Executes trading based on algorithmic decisions.
- **Features**:
  - Executes trading algorithms every 60 seconds.
  - Manages a minimum balance of $15,000 and maintains 30% liquidity.
  - Logs all trades with timestamps, stock details, price, and reasons.
  - Includes checks for sufficient balance, unauthorized selling, and automatic sell-off conditions.

### `ranking_client.py`
- **Objective**: Runs the ranking algorithm to evaluate and rank trading strategies.
- **Features**:
  - Downloads and stores NASDAQ-100 tickers in MongoDB.
  - Executes strategies on each ticker.
  - Updates algorithm scores based on trade success.
  - Includes a 30-second interval between ranking updates.

### `trading_strategies#.py`
- **Objective**: Defines multiple trading strategies with a standardized interface.
- **Features**:
  - Includes strategies like mean reversion, momentum, and arbitrage.
  - Ensures consistent decision-making across all strategies.

### Helper Files
- **`client_helper.py`**: Common functions for client operations (MongoDB setup, error handling).
- **`ranking_helper.py`**: Functions for updating rankings based on performance.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [API Setup](#api-setup)
- [Usage](#usage)
- [Logging](#logging)
- [Notes](#notes)
- [Contributing](#contributing)
- [License](#license)

## Installation

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/yeonholee50/polygon-trading-bot.git
    cd polygon-trading-bot
    ```

2. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set Up MongoDB**:
   - Sign up for a MongoDB cluster (e.g., via [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)).
   - Get your MongoDB connection string and create a database for stock data storage.

## Configuration

1. **Create `config.py`**:
   - Copy `config_template.py` to `config.py` and enter your API keys and MongoDB credentials.
    ```python
    POLYGON_API_KEY = "your_polygon_api_key"
    FINANCIAL_PREP_API_KEY = "your_fmp_api_key"
    MONGO_DB_USER = "your_mongo_user"
    MONGO_DB_PASS = "your_mongo_password"
    API_KEY = "your_alpaca_api_key"
    API_SECRET = "your_alpaca_secret_key"
    BASE_URL = "https://paper-api.alpaca.markets"
    ```

## API Setup

### Polygon API
1. Sign up at [Polygon.io](https://polygon.io/) and get an API key.
2. Add it to `config.py` as `POLYGON_API_KEY`.

### Financial Modeling Prep API
1. Sign up at [Financial Modeling Prep](https://financialmodelingprep.com/) and get an API key.
2. Add it to `config.py` as `FINANCIAL_PREP_API_KEY`.

### Alpaca API
1. Sign up at [Alpaca](https://alpaca.markets/) and get API keys.
2. Add them to `config.py` as `API_KEY` and `API_SECRET`.

## Usage

To start the bot, execute on two separate terminals:
```python
python ranking_client.py
python trading_client.py
```


## Logging

The bot logs all major events and errors to a `system.log` file, including API errors, MongoDB operations, and market status checks. You can access the log file to review the bot's activities and diagnose potential issues. The bot will also log rank events to a separate `rank.log` file.

## Notes

- The bot is limited to 250 API calls per day (as per the Polygon API free tier).
- Future enhancements can include adding custom trading strategies or integrating with a brokerage API for live trading.

## Contributing

Contributions are welcome! Feel free to open a pull request or submit issues for bugs or feature requests. Future improvements may focus on optimizing the ranking system or expanding the bot's capabilities for more advanced trading strategies.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
