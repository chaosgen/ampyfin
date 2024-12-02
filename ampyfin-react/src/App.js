import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = "https://ampyfin-api-app.onrender.com";

function App() {
  const [holdings, setHoldings] = useState([]);
  const [rankings, setRankings] = useState([]);

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

  // Fetch data initially and every minute
  useEffect(() => {
    fetchHoldings();
    fetchRankings();
    const interval = setInterval(() => {
      fetchHoldings();
      fetchRankings();
    }, 60000); // 1 minute

    return () => clearInterval(interval); // Cleanup on component unmount
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>AmpyFin Portfolio</h1>
        <div className="live-status">
          <span className="live-dot"></span>
          <span>LIVE</span>
        </div>
      </header>
      <main>
        <section>
          <h2>Current Holdings</h2>
          <HoldingsTable holdings={holdings} />
        </section>
        <section>
          <h2>Algorithm Rankings</h2>
          <RankingsTable rankings={rankings} />
        </section>
      </main>
    </div>
  );
}

function HoldingsTable({ holdings }) {
  return (
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
