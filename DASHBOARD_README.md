# 🚀 Perso-1903 Trading Dashboard

Real-time monitoring interface for the Perso-1903 AI trading agent.

## 📊 Features

- **Real-time Position Tracking**: Monitor active trading positions
- **Scalping Strategy Monitoring**: Track partial sells, stop losses, and rebuys
- **Double Down Strategy**: Monitor double down positions and opportunities
- **Trade History**: View recent trades and performance metrics
- **P&L Tracking**: Real-time profit/loss calculations
- **System Status**: Monitor agent health and data sources
- **Auto Refresh**: Automatic data updates every 5 seconds

## 🛠️ Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the agent is running and generating logs

## 🚀 Usage

1. Start the dashboard:
```bash
python dashboard.py
```

2. Open your browser and navigate to:
```
http://localhost:8080
```

3. The dashboard will automatically refresh every 5 seconds

## 📈 Dashboard Sections

### Performance Metrics
- Total trades executed
- Success rate percentage
- Total P&L
- Average trade size

### Active Positions
- Regular trading positions
- Entry price and current price
- Position size and P&L

### Scalping Positions
- Partial sell tracking
- Stop loss levels
- Remaining position amounts

### Double Down Positions
- Double down entries
- No stop loss positions
- Rebuy opportunities

### Recent Trades
- Last 10 trades executed
- Trade success/failure status
- Timestamps and amounts

### System Status
- Risk Manager availability
- Log file status
- Data source health

## 🔧 Configuration

The dashboard reads data from:
- `logs/agent.jsonl` - Trade history logs
- `risk_state.json` - Risk management state
- RiskManager instance - Live position data

## 🛡️ Security

- Dashboard runs on localhost only (127.0.0.1:8080)
- Read-only access to agent data
- No trading capabilities
- No API key exposure

## 📱 Mobile Support

The dashboard is fully responsive and works on mobile devices.

## 🔄 Auto Refresh

- Toggle auto-refresh on/off
- Manual refresh button
- 5-second update interval
- Real-time status indicators

## 🎯 Competition Ready

The dashboard is designed to work seamlessly during the Recall Network competition without interfering with trading operations.

---

**Note**: This dashboard is read-only and will not affect the agent's trading performance.
