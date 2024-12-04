import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { Helmet } from 'react-helmet';

const API_URL = "https://ampyfin-api-app.onrender.com";

function App() {
  const [activeTab, setActiveTab] = useState('how-it-works');
  const [holdings, setHoldings] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [portfolioPercentage, setPortfolioPercentage] = useState(null);
  const [ndaqPercentage, setNdaqPercentage] = useState(null);
  const [spyPercentage, setSpyPercentage] = useState(null);
  const [lastUpdated, setLastUpdated] = useState('');
  const [ticker, setTicker] = useState('');
  const [ampyfinResult, setAmpyfinResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false); // Add state for loading

  // Fetch Data from API
  const fetchPortfolioPercentage = async () => {
    try {
      const response = await axios.get(`${API_URL}/portfolio_percentage`);
      setPortfolioPercentage(response.data.portfolio_percentage);
      setNdaqPercentage(response.data.ndaq_percentage);
      setSpyPercentage(response.data.spy_percentage);
      setLastUpdated(new Date().toLocaleString());
    } catch (error) {
      console.error('Error fetching portfolio percentage:', error);
    }
  };

  const fetchHoldings = async () => {
    try {
      const response = await axios.get(`${API_URL}/holdings`);
      setHoldings(response.data);
    } catch (error) {
      console.error('Error fetching holdings:', error);
    }
  };

  const fetchRankings = async () => {
    try {
      const response = await axios.get(`${API_URL}/rankings`);
      setRankings(response.data);
    } catch (error) {
      console.error('Error fetching rankings:', error);
    }
  };

  
  

  const fetchAmpyfinRecommendation = async (ticker) => {
    setIsLoading(true);  // Set loading to true when starting the request
    try {
      const response = await axios.get(`${API_URL}/ticker/${ticker}`);
      setAmpyfinResult(response.data);
    } catch (error) {
      console.error('Error fetching AmpyFin recommendation:', error);
      setAmpyfinResult(null);
    } finally {
      setIsLoading(false);  // Set loading to false once the request finishes
    }
  };


  useEffect(() => {
    fetchPortfolioPercentage();
    fetchHoldings();
    fetchRankings();
    const interval = setInterval(() => {
      fetchPortfolioPercentage();
      fetchHoldings();
      fetchRankings();
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'how-it-works':
        return (
          <div className="content-section">
            <h2>How AmpyFin Works</h2>
            <p>
              AmpyFin is a cutting-edge, <strong>AI-powered trading bot</strong> designed specifically for navigating the complexities of the <strong>NASDAQ-100</strong>. By utilizing a machine learning strategy called <strong>Supervised Ensembled Learning</strong>, AmpyFin leverages a range of diverse trading strategies, dynamically ranking each algorithm based on performance and current market conditions. 
              This allows the bot to intelligently allocate its resources and optimize trades, ensuring both high efficiency and adaptability in real-time.
            </p>
            <p>
              At the heart of AmpyFin is its <strong>dynamic ranking system</strong>, which adjusts the influence of each algorithm according to its recent success rates. This dynamic system ensures that AmpyFin consistently prioritizes the most effective strategies while minimizing risk exposure. All algorithms are rigorously tested in simulated environments to ensure that only the best-performing models contribute to real-time trading decisions.
            </p>
            <p>
              With an ever-adapting approach to market conditions, AmpyFin ensures optimal risk management, continually evaluating and adjusting its strategies to remain ahead in a volatile market environment. The system seamlessly combines fundamental trading strategies like <strong>Mean Reversion</strong> and <strong> Momentum</strong> with more advanced AI-driven methods like <strong>Entropy Flow Strategy</strong>, ensuring that every trade is backed by the most robust analysis available.
            </p>
          </div>
        );
      case 'portfolio':
        return (
          <div className="content-section">
            <h2>Live Portfolio</h2>
            <HoldingsTable holdings={holdings} />
            <h2>Live Rankings</h2>
            <RankingsTable rankings={rankings} />
          </div>
        );
      case 'benchmark':
        return (
          <div className="content-section">
            <h2>Live Performance Benchmarked Against Major ETFs</h2>
            <BenchmarkSection 
              portfolioPercentage={portfolioPercentage} 
              ndaqPercentage={ndaqPercentage} 
              spyPercentage={spyPercentage} 
            />
          </div>
        );
        case 'test-ampyfin':
          return (
            <div className="content-section">
              <h2>Test AmpyFin</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  fetchAmpyfinRecommendation(ticker);
                }}
              >
                <input 
                  type="text" 
                  value={ticker} 
                  onChange={(e) => setTicker(e.target.value)} 
                  placeholder="Enter Ticker" 
                  required 
                />
                <button type="submit">Process</button>
              </form>
        
              {isLoading ? (
                <div className="loading-message">
                  <p>Processing...</p>
                  {/* You can also use a spinner here */}
                  <div className="spinner"></div>
                </div>
              ) : ampyfinResult ? (
                <div className="ampyfin-result">
                  <h3>{ampyfinResult.ticker}</h3>
                  <p 
                    className={`decision ${ampyfinResult.decision}`}
                  >
                    Decision: <strong>{ampyfinResult.decision}</strong> @ current price of {ampyfinResult.current_price}
                  </p>
                  
                  <p>Buy Weight: {ampyfinResult.buy_weight}</p>
                  <p>Sell Weight: {ampyfinResult.sell_weight}</p>
                  <p>Hold Weight: {ampyfinResult.hold_weight}</p>
                </div>
              ) : (
                <p>No data available. Please enter a valid ticker.</p>
              )}
            </div>
          );
        
      default:
        return null;
    }
  };

  return (
    <div className="App">
      <Helmet>
        <title>AmpyFin</title>
      </Helmet>
      <header className="App-header">
        <h1>AmpyFin</h1>
        <nav>
          <ul>
            <li onClick={() => setActiveTab('how-it-works')}>How It Works</li>
            <li onClick={() => setActiveTab('portfolio')}>Portfolio & Results</li>
            <li onClick={() => setActiveTab('benchmark')}>Benchmark</li>
            <li onClick={() => setActiveTab('test-ampyfin')}>Test AmpyFin</li>
          </ul>
        </nav>
        <div className="live-status">
          <span className="live-dot"></span>
          <span>LIVE</span>
        </div>
      </header>
      <main>{renderTabContent()}</main>
      <footer className="App-footer">
        <p className="last-updated">Last Updated: {lastUpdated}</p>
        <p>&copy; 2024 AmpyFin Trading Bot</p>
      </footer>
    </div>
  );
}

function HoldingsTable({ holdings }) {
  return (
    <div className="scrollable-table-container">
      <table className="styled-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Quantity</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <tr key={holding.id}>
              <td>{holding.symbol}</td>
              <td>{holding.quantity}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RankingsTable({ rankings }) {
  return (
    <div className="scrollable-table-container">
      <table className="styled-table">
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Rank</th>
          </tr>
        </thead>
        <tbody>
          {rankings.map((ranking) => (
            <tr key={ranking.id}>
              <td>{ranking.strategy}</td>
              <td>{ranking.rank}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BenchmarkSection({ portfolioPercentage, ndaqPercentage, spyPercentage }) {
  const formatPercentage = (value) => `${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;

  return (
    <div className="benchmark-section">
      <div className={`portfolio-percentage ${portfolioPercentage > 0 ? 'green' : 'red'}`}>
        AmpyFin: {formatPercentage(portfolioPercentage)}
        <p className="live-since">Total Percentage since November 20, 2024, at 8:00 AM</p>
      </div>
      <div className={`portfolio-percentage ${ndaqPercentage > 0 ? 'green' : 'red'}`}>
        NDAQ: {formatPercentage(ndaqPercentage)}
        <p className="live-since">Total Percentage since November 20, 2024, at 8:00 AM</p>
      </div>
      <div className={`portfolio-percentage ${spyPercentage > 0 ? 'green' : 'red'}`}>
        SPY: {formatPercentage(spyPercentage)}
        <p className="live-since">Total Percentage since November 20, 2024, at 8:00 AM</p>
      </div>
    </div>
  );
}

export default App;
