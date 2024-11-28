# AmpyFin Trading Bot
![](logo.png)

## Introduction
Picture this: A trading system so advanced, it's like having 60 expert traders working for you around the clock. Sounds too good to be true?

Meet **AmpyFin**, the AI-powered bot that's turning this fantasy into reality for NASDAQ-100 traders. Curious about how it works? You're in the right place.

## AmpyFin's Data Collection Power
AmpyFin starts its day by tapping into the **Financial Modeling Prep API** to fetch NASDAQ-100 ticker data, giving it a sneak peek into the market. 

AmpyFin doesn't stop there—it's constantly checking market status in real-time using the **Polygon API**. This helps AmpyFin stay ahead of the game and make decisions based on the most current market conditions.

All of this data is stored securely in **MongoDB**, ensuring quick access to market information and trading activity logs, giving AmpyFin a real edge over the competition.

## Algorithms at Work
Imagine having numerous trading strategies but not knowing which is the best to use for the current market. That’s what AmpyFin aims to solve with its diverse collection of algorithms.

These algorithms range from basic strategies like **mean reversion** to more complex, **AI-driven** approaches. Each algorithm runs simulated trades during market hours, logging every success and failure. This constant testing helps AmpyFin refine its strategies and learn from every move, all while minimizing risk in the process.

In practice, AmpyFin uses simple strategies such as:
- **Mean Reversion**: Asset prices return to their historical averages.
- **Momentum**: Capitalizing on current market trends.
- **Arbitrage**: Looking for price discrepancies between related assets.
to more complex ones that utilize its own AI libraries to recommend trades.

Each algorithm contributes its unique strength to the overall strategy, and the best-performing ones are given greater influence in the final trading decisions.

## How Dynamic Ranking Works
Managing 60 algorithms would be chaos if it weren’t for AmpyFin’s dynamic ranking system. Each algorithm starts with a base score of 50000 and is ranked based on its performance—both real and simulated.

AmpyFin uses a specific generating function to calculate a coefficient for each algorithm to determine how much weight it should have in the final decision-making process. The function looks like this:

$$
\left( \frac{e^e}{e^2 - 1} \right)^{2i}
$$

Where \(i\) is the inverse of the algorithm's ranking. This ranking system adjusts the influence each algorithm has on the bot’s decisions, ensuring that the highest-ranked algorithms are given more weight during trading. The ranking system is dynamic, meaning it can change based on the performance of each algorithm. If an algorithm performs well, it gains more influence in the final trading decisions. Conversely, if an algorithm underperforms, its influence decreases. This ensures that the bot remains agile and responsive to market changes. A time delta coefficient is utilized so that the ranking system is biased towards the most recent trades, but not too heavily biased.


The dynamic ranking system helps AmpyFin:
- Adapt to changing market conditions.
- Balance risk and reward.
- Prioritize high-performing strategies automatically.

## Features
- **NASDAQ-100 Ticker Retrieval**: Fetches tickers using the Financial Modeling Prep API during early market hours.
- **Market Status Monitoring**: Monitors market status (open, closed, premarket) in real-time with the Polygon API.
- **Algorithm Ranking System**: Dynamically adjusts algorithm rankings based on profitability.
- **Paper Trading**: Simulated trading environment for safe strategy testing, with an option for live trading.
- **Data Storage**: MongoDB for storing ticker data and trading activity logs.
- **Customizable**: Easily extend trading strategies and configurations.

## File Structure and Objectives

### `client.py`
- **Objective**: Orchestrates both trading and ranking clients.
- **Features**:
  - Initiates trading and ranking clients at appropriate times.
  - Manages trading operations during market hours.
  - Includes error handling and logs system performance.

### `trading_client.py`
- **Objective**: Executes trading based on algorithmic decisions.
- **Features**:
  - Executes trading algorithms every 60 seconds.
  - Ensures a minimum balance of $15,000 and maintains 30% liquidity.
  - Logs trades with timestamps, stock details, and reasons.
  - Validates balance and prevents unauthorized selling.

### `ranking_client.py`
- **Objective**: Runs the ranking algorithm to evaluate and rank trading strategies.
- **Features**:
  - Downloads and stores NASDAQ-100 tickers in MongoDB.
  - Executes strategies on each ticker.
  - Updates algorithm scores based on trade performance.
  - Refreshes rankings every 30 seconds.

### `trading_strategies.py`
- **Objective**: Defines various trading strategies.
- **Features**:
  - Includes strategies like mean reversion, momentum, and arbitrage.
  - Ensures consistency across strategy decision-making.

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
```bash
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
