import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Helmet } from 'react-helmet';
import './App.css';

const API_URL = "https://ampyfin-api-app.onrender.com";

function App() {
  const [holdings, setHoldings] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [portfolioData, setPortfolioData] = useState({
    portfolio_percentage: null,
    ndaq_percentage: null,
    spy_percentage: null,
  });

  // Fetch Holdings
  const fetchHoldings = async () => {
    try {
      const response = await axios.get(`${API_URL}/holdings`);
      setHoldings(response.data);
    } catch (error) {
      console.error('Error fetching holdings:', error);
    }
  };

  // Fetch Rankings
  const fetchRankings = async () => {
    try {
      const response = await axios.get(`${API_URL}/rankings`);
      setRankings(response.data);
    } catch (error) {
      console.error('Error fetching rankings:', error);
    }
  };

  // Fetch Portfolio Percentages
  const fetchPortfolioData = async () => {
    try {
      const response = await axios.get(`${API_URL}/portfolio_percentage`);
      setPortfolioData(response.data);
    } catch (error) {
      console.error('Error fetching portfolio data:', error);
    }
  };

  // Fetch data initially and every minute
  useEffect(() => {
    fetchHoldings();
    fetchRankings();
    fetchPortfolioData();

    const interval = setInterval(() => {
      fetchHoldings();
      fetchRankings();
      fetchPortfolioData();
    }, 60000); // Update every 1 minute

    return () => clearInterval(interval); // Cleanup on component unmount
  }, []);

  const formatPercentage = (percentage) => {
    const formatted = (percentage * 100).toFixed(2); // Convert to percentage and round to 2 decimal places
    const sign = formatted >= 0 ? '+' : ''; // Add '+' for positive numbers
    const color = formatted >= 0 ? 'green' : 'red'; // Determine the color based on the value
    return { formatted, sign, color };
  };

  const portfolio = portfolioData.portfolio_percentage !== null 
    ? formatPercentage(portfolioData.portfolio_percentage) 
    : { formatted: '0.00', sign: '', color: 'gray' };

  const ndaq = portfolioData.ndaq_percentage !== null 
    ? formatPercentage(portfolioData.ndaq_percentage) 
    : { formatted: '0.00', sign: '', color: 'gray' };

  const spy = portfolioData.spy_percentage !== null 
    ? formatPercentage(portfolioData.spy_percentage) 
    : { formatted: '0.00', sign: '', color: 'gray' };

  return (
    <div className="App">
      <Helmet>
        <title>AmpyFin Dashboard</title>
      </Helmet>

      <header className="App-header">
        <h1>AmpyFin Portfolio</h1>
        <div className="live-status">
          <span className="live-dot"></span>
          <span>LIVE</span>
        </div>
      </header>

      <main className="main-content">
        <section className="portfolio-section">
          <h3>Total Ampyfin Percentage since November 20, 2024</h3>
          <p className={`portfolio-percentage ${portfolio.color}`}>
            {portfolio.sign}{portfolio.formatted}%
          </p>
          <h3>Total NASDAQ Percentage since November 20, 2024</h3>
          <p className={`portfolio-percentage ${ndaq.color}`}>
            {ndaq.sign}{ndaq.formatted}%
          </p>
          <h3>Total S&P 500 Percentage since November 20, 2024</h3>
          <p className={`portfolio-percentage ${spy.color}`}>
            {spy.sign}{spy.formatted}%
          </p>
          <p className="live-since">Live since November 20, 2024 at 8:00 AM</p>
        </section>

        <section className="right-sections">
          <div>
            <h2>Current Holdings</h2>
            <HoldingsTable holdings={holdings} />
          </div>
          <div>
            <h2>Algorithm Rankings</h2>
            <RankingsTable rankings={rankings} />
          </div>
        </section>
      </main>

      <footer className="App-footer">
        <p>Last updated: {new Date().toLocaleString()}</p>
        <p>&copy; 2024 AmpyFin. All rights reserved.</p>
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

export default App;

