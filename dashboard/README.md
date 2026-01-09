# Crypto Prediction Monitor Dashboard

A web-based dashboard for viewing real-time prediction market data from multiple sources.

## Features

- **Real-time Market Data**: View markets from Manifold, Kalshi, Metaculus, Polymarket, and Limitless
- **Interactive UI**: Modern, responsive interface with filtering and search
- **Live Updates**: Auto-refreshes every 30 seconds
- **Price Quotes**: YES/NO prices with bid/ask spreads
- **Source Filtering**: View markets by source or all at once
- **Statistics**: Track total markets, outcomes, and active sources

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r dashboard/requirements.txt
   ```

2. **Run the Dashboard**:
   ```bash
   python run_dashboard.py
   ```

3. **Access the Dashboard**:
   Open your browser to `http://localhost:5000`

## API Endpoints

### GET `/api/markets`
Returns all market data from all enabled sources.

**Response**:
```json
{
  "markets": {
    "manifold": [...],
    "kalshi": [...],
    "metaculus": [...]
  },
  "last_update": {...},
  "total_markets": 42
}
```

### GET `/api/markets/<source>`
Returns market data from a specific source.

**Example**: `/api/markets/manifold`

### GET `/api/refresh`
Forces a refresh of all market data.

### GET `/api/stats`
Returns statistics about the markets.

## Configuration

The dashboard uses the same configuration as the main bot (`config.yaml`). Make sure your adapters are enabled in the configuration:

```yaml
adapters:
  manifold:
    enabled: true
    base_url: "https://api.manifold.markets"
    markets_limit: 50
  
  kalshi:
    enabled: true
    base_url: "https://api.elections.kalshi.com/trade-api/v2"
    markets_limit: 50
  
  metaculus:
    enabled: true
    base_url: "https://www.metaculus.com/api2"
    questions_limit: 50
```

## Architecture

- **Backend**: Flask web application with async adapter integration
- **Frontend**: HTML5 with Tailwind CSS, Chart.js, and Axios
- **Data Flow**: Adapters → Flask API → JavaScript Frontend
- **Rate Limiting**: Respects the same rate limits as the main bot

## Development

### Adding New Features

1. **Backend**: Add new endpoints in `dashboard/app.py`
2. **Frontend**: Update `dashboard/templates/index.html`
3. **Styling**: Use Tailwind CSS classes for consistent design

### Testing

```bash
# Test the API directly
curl http://localhost:5000/api/markets
curl http://localhost:5000/api/stats
```

## Production Deployment

For production use, consider:

1. **WSGI Server**: Use Gunicorn or uWSGI instead of Flask development server
2. **Reverse Proxy**: Nginx or Apache for SSL termination and load balancing
3. **Process Manager**: Supervisor or systemd to keep the service running
4. **Monitoring**: Add health checks and logging

Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 dashboard.app:app
```

## Troubleshooting

### Dashboard Not Loading Data
- Check that adapters are enabled in `config.yaml`
- Verify API keys and network connectivity
- Check the Flask logs for error messages

### CORS Errors
- The dashboard includes CORS support for development
- For production, configure your reverse proxy to handle CORS

### Performance Issues
- The dashboard limits to 10 markets per adapter by default
- Adjust the `markets_limit` in configuration as needed
- Consider caching for high-traffic deployments

## Security Notes

- The dashboard is read-only and doesn't expose trading functionality
- API endpoints are not authenticated (internal use only)
- For production, consider adding authentication
- Use HTTPS in production environments
