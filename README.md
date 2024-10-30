# AmpyFin Trading Bot
![](logo.png)
## Overview

This trading bot retrieves and stores NASDAQ-100 tickers, monitors market status, and prepares for trading operations during premarket and regular trading hours using the Polygon API. The bot implements a ranked ensemble learning system for 50 known trading algorithms, each initialized with a base rating of 0. These rankings dynamically adjust based on each algorithm's hypothetical buy/sell decisions and resulting profitability, allowing for optimized trading strategies to have more influence in the final buying & selling decisions.

The bot is configured for paper trading by default, allowing you to test and refine your strategies without risking real capital. To transition to live trading, simply update your API keys and adjust the trading parameters in the configuration file.

## Features

- Fetches NASDAQ-100 tickers during early market hours using Financial Modeling Prep API.
- Stores tickers in a MongoDB database.
- Monitors market status (open, closed, early hours) using Polygon API.
- Implements a ranking system for 95 trading algorithms based on performance.
- Logs events and errors for easy debugging.
- Can be extended to execute custom trading strategies.

### Algorithm Ranking System

The bot incorporates a ranking system for 95 trading algorithms, each starting with a base score of 1000. These rankings are updated based on the profitability of the algorithms’ hypothetical trades. The system uses a coefficient calculated as:

$$
\left( \frac{e^e}{e^2 - 1} \right)^{2i}
$$

where \(i\) is the inverse of the algorithm's ranking, with the highest-ranked algorithm having \(i = 95\). The coefficients influence the decision weights of each algorithm, creating a dynamic system where the most profitable algorithms contribute more heavily to the bot's overall trading decisions. This ranking system is key to optimizing trades as market conditions change.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Polygon API Setup](#polygon-api-setup)
- [Financial Modeling Prep API Setup](#financial-modeling-prep-api-setup)
- [Usage](#usage)
- [Logging](#logging)
- [Notes](#notes)
- [Contributing](#contributing)
- [License](#license)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yeonholee50/polygon-trading-bot.git
    cd polygon-trading-bot
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Set up MongoDB:
   - You will need a MongoDB cluster. If you don’t have one, sign up at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and set up your cluster.
   - Ensure you have the MongoDB connection string and create a database for storing the stock data.

## Configuration

1. Rename `config_template.py` to `config.py` and provide your API keys and MongoDB credentials:

    ```python
    POLYGON_API_KEY = "your_polygon_api_key"
    FINANCIAL_PREP_API_KEY = "your_fmp_api_key"
    MONGO_DB_USER = "your_mongo_user"
    MONGO_DB_PASS = "your_mongo_password"
    API_KEY = "your_alpaca_api_key"
    API_SECRET = "your_alpaca_secret_key"
    BASE_URL = "https://paper-api.alpaca.markets"
    ```

## Polygon API Setup

To use the Polygon API for market data, you need to sign up and obtain an API key. Follow these steps:

1. Visit [Polygon.io](https://polygon.io/).
2. Click on **Get Started for Free** and create an account.
3. After signing up, navigate to the **API Keys** section in your Polygon account dashboard.
4. Copy your API key and add it to the `config.py` file as `POLYGON_API_KEY`.

For more information on how to use the Polygon API, refer to their [official documentation](https://polygon.io/docs).

## Financial Modeling Prep API Setup

The Financial Modeling Prep API is used to fetch NASDAQ-100 tickers. Follow these steps to set it up:

1. Visit [Financial Modeling Prep](https://financialmodelingprep.com/).
2. Sign up for a free account.
3. Once registered, log in to your account and navigate to the **API Key** section.
4. Copy your API key and add it to the `config.py` file as `FINANCIAL_PREP_API_KEY`.

For further details on using the Financial Modeling Prep API, check their [API documentation](https://financialmodelingprep.com/developer/docs).

## Alpaca Setup

To execute trades, you can integrate Alpaca into the bot. Follow these steps to set up your Alpaca account:

1. Sign up for a free account at [Alpaca](https://alpaca.markets/).
2. Once registered, navigate to the **API** section in your Alpaca dashboard.
3. Copy your API key and secret, and add them to the `config.py` file:

    ```python
    API_KEY = "your_alpaca_api_key"
    API_SECRET = "your_alpaca_secret_key"
    BASE_URL = "https://paper-api.alpaca.markets"
    ```

4. Refer to the [Alpaca API documentation](https://alpaca.markets/docs/api-documentation/) for more details on how to use the Alpaca API for trading.

## Usage

To run the bot, simply execute:

```bash
python client.py

## Logging

The bot logs all major events and errors to a `system.log` file, including API errors, MongoDB operations, and market status checks. You can access the log file to review the bot's activities and diagnose potential issues.

## Notes

- The bot is limited to 250 API calls per day (as per the Polygon API free tier).
- Future enhancements can include adding custom trading strategies or integrating with a brokerage API for live trading.

## Contributing

Contributions are welcome! Feel free to open a pull request or submit issues for bugs or feature requests. Future improvements may focus on optimizing the ranking system or expanding the bot's capabilities for more advanced trading strategies.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
