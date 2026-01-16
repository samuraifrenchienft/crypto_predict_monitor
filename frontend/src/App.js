import React, { useState } from 'react';
import './App.css';
import PnLCard from './components/PnLCard';

function App() {
  const [userId, setUserId] = useState('test_user');

  return (
    <div className="App">
      <header className="App-header">
        <h1>Prediction Monitor</h1>
        <p>Backend Status: <span id="backend-status">Checking...</span></p>
        <button onClick={checkBackend}>Check Backend</button>
        
        <div style={{ marginTop: '20px' }}>
          <input 
            type="text" 
            value={userId} 
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter user ID"
            style={{ padding: '8px', marginRight: '8px' }}
          />
        </div>
      </header>
      
      <main className="App-main">
        <PnLCard userId={userId} />
      </main>
    </div>
  );

  function checkBackend() {
    fetch('http://localhost:5000/health')
      .then(response => response.json())
      .then(data => {
        document.getElementById('backend-status').textContent = '✅ Connected';
        document.getElementById('backend-status').style.color = 'green';
      })
      .catch(error => {
        document.getElementById('backend-status').textContent = '❌ Disconnected';
        document.getElementById('backend-status').style.color = 'red';
      });
  }
}

export default App;
