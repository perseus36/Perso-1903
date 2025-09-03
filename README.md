# Perso-1903 Recall Trading Agent

## 🤖 Agent Overview

**Perso-1903** is an AI-powered trading agent designed for Recall trading competitions. Built with Python and following Recall's official documentation, this agent implements advanced portfolio management strategies with AI-driven decision making.

## 🚀 Features

- **AI-Powered Portfolio Rebalancing**: Uses GPT-4o to adjust portfolio targets based on market conditions
- **Multi-Chain Support**: Trades across EVM (Ethereum, Polygon, Base) and SVM (Solana) chains
- **Real-Time Market Data**: Fetches live prices from CoinGecko API
- **Automated Scheduling**: Daily rebalancing at 09:00 local time
- **Risk Management**: Implements drift threshold (2%) for rebalancing decisions
- **Sandbox & Production Ready**: Supports both testing and live competition environments
- **Enhanced Security**: Secure API key management with environment variables

## 📁 Project Structure

```
perso-1903/
├── perso_1903_agent.py      # Main agent implementation
├── perso_1903_client.py      # Advanced trading client
├── portfolio_config.json     # Portfolio allocation targets
├── env.example              # Environment variables template
├── requirements.txt         # Python dependencies
├── index.html              # Web-based testing interface
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd perso-1903
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env with your actual API keys
   nano .env
   ```

## ⚙️ Configuration

### Environment Variables (`.env`)
```env
# Recall API Keys (Get from https://competitions.recall.network)
RECALL_API_KEY_SANDBOX=your_sandbox_api_key_here
RECALL_API_KEY_PRODUCTION=your_production_api_key_here

# OpenAI API Key (Get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=your_openai_api_key_here

# API URLs
RECALL_SANDBOX_URL=https://api.sandbox.competitions.recall.network
RECALL_PRODUCTION_URL=https://api.competitions.recall.network
```

### Portfolio Configuration (`portfolio_config.json`)
```json
{
  "USDC": 0.25,
  "WETH": 0.5,
  "WBTC": 0.25
}
```

## 🎯 Usage

### Running the Agent

1. **Start the main agent**:
   ```bash
   python perso_1903_agent.py
   ```

2. **Test with the web interface**:
   - Open `index.html` in your browser
   - Use the interface to test API connections and execute trades

3. **Use the trading client**:
   ```bash
   python perso_1903_client.py
   ```

4. **Run tests**:
   ```bash
   python test_trade.py
   ```

### Agent Behavior

- **Daily Rebalancing**: Runs automatically at 09:00 local time
- **Drift Detection**: Rebalances when portfolio drifts >2% from targets
- **AI Adjustments**: Uses GPT-4o to suggest optimal allocations
- **Risk Management**: Implements proper error handling and retry logic

## 🔧 API Integration

### Recall API Endpoints Used

- `GET /api/agent/balances` - Portfolio balances
- `GET /api/agent/profile` - Agent profile
- `GET /api/agent/trades` - Trade history
- `GET /api/price` - Token prices
- `POST /api/trade/execute` - Execute trades

### External APIs

- **CoinGecko API**: Real-time token prices
- **OpenAI API**: AI-driven portfolio adjustments

## 🏆 Competition Ready

This agent is designed for Recall trading competitions with:

- **Sandbox Testing**: Full testing environment support
- **Production Deployment**: Ready for live competitions
- **Performance Monitoring**: Built-in logging and metrics
- **Error Handling**: Robust error recovery mechanisms
- **Security**: Secure API key management

## 📊 Trading Strategy

### Portfolio Management
- **Target Allocation**: 25% USDC, 50% WETH, 25% WBTC
- **Rebalancing Threshold**: 2% drift from targets
- **AI Optimization**: Dynamic allocation adjustments

### Risk Management
- **Slippage Control**: Configurable slippage tolerance
- **Position Sizing**: Appropriate trade sizes
- **Error Recovery**: Graceful handling of failed trades

## 🔍 Testing

### Web Interface Testing
1. Open `index.html` in your browser
2. Select environment (Sandbox/Production)
3. Test API connections
4. Execute sample trades
5. Monitor activity logs

### Command Line Testing
```bash
# Test portfolio fetch
python perso_1903_client.py

# Test trade execution
python test_trade.py
```

## 🚨 Troubleshooting

### Common Issues

1. **API Connection Errors**:
   - Verify API keys in `.env` file
   - Check network connectivity
   - Ensure correct environment URLs

2. **Trade Execution Failures**:
   - Check sufficient balances
   - Verify token addresses
   - Monitor slippage settings

3. **AI Feature Issues**:
   - Ensure OpenAI API key is set
   - Check API rate limits
   - Verify model availability

### Error Codes

- `401 Unauthorized`: Invalid API key
- `429 Too Many Requests`: Rate limit exceeded
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server-side issue

## 🔒 Security

### API Key Management
- **Never commit API keys to version control**
- **Use environment variables for all sensitive data**
- **Rotate API keys regularly**
- **Use different keys for sandbox and production**

### Best Practices
- Keep `.env` file secure and local
- Use strong, unique API keys
- Monitor API usage and limits
- Implement proper error handling

## 📞 Support

For issues and questions:
- Check Recall documentation
- Review error logs
- Test in sandbox environment first
- Monitor competition announcements

## 📄 License

This project is designed for Recall trading competitions. Follow Recall's terms of service and competition rules.

---

**Perso-1903** - AI-Powered Recall Trading Agent 🤖📈
