import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = "https://ampyfin-api-app.onrender.com";

function App() {
  const [holdings, setHoldings] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [portfolioPercentage, setPortfolioPercentage] = useState(null);

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

  // Fetch Portfolio Percentage
  const fetchPortfolioPercentage = async () => {
    try {
      const response = await axios.get(`${API_URL}/portfolio_percentage`);
      const percentage = response.data.portfolio_percentage;
      setPortfolioPercentage(percentage);
    } catch (error) {
      console.error('Error fetching portfolio percentage:', error);
    }
  };

  // Fetch data initially and every minute
  useEffect(() => {
    fetchHoldings();
    fetchRankings();
    fetchPortfolioPercentage();

    const interval = setInterval(() => {
      fetchHoldings();
      fetchRankings();
      fetchPortfolioPercentage();
    }, 60000); // Update every 1 minute

    return () => clearInterval(interval); // Cleanup on component unmount
  }, []);

  const formatPercentage = (percentage) => {
    const formatted = (percentage * 100).toFixed(2); // Convert to percentage and round to 2 decimal places
    const sign = formatted >= 0 ? '+' : ''; // Add '+' for positive numbers
    const color = formatted >= 0 ? 'green' : 'red'; // Determine the color based on the value
    return { formatted, sign, color };
  };

  const { formatted, sign, color } = portfolioPercentage !== null ? formatPercentage(portfolioPercentage) : { formatted: '0.00', sign: '', color: 'gray' };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AmpyFin Portfolio</h1>
        <div className="live-status">
          <span className="live-dot"></span>
          <span>LIVE</span>
        </div>
      </header>
      <main className="main-content">
        {/* Portfolio Percentage on the Left */}
        <section className="portfolio-section">
          <h2>Total Percentage Profit/Loss</h2>
          <p className={`portfolio-percentage ${color}`}>
            {sign}{formatted}%
          </p>
          <p className="live-since">Live since November 15, 2024 at 8:00 AM</p> {/* Live since date */}
        </section>

        {/* Holdings and Rankings on the Right */}
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

