# Perso-1903 Recall Trading Agent
# Advanced Trading Client for Recall Competitions

import requests
import json
import time
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Perso1903TradingClient:
    """Advanced trading client for Perso-1903 agent"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        # Use provided values or get from environment
        self.api_key = api_key or os.getenv('RECALL_API_KEY_SANDBOX')
        self.base_url = base_url or os.getenv('RECALL_SANDBOX_URL', 'https://api.sandbox.competitions.recall.network')
        
        if not self.api_key:
            raise ValueError("API key is required. Set RECALL_API_KEY_SANDBOX in your .env file or pass it to the constructor.")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })
    
    def get_portfolio(self) -> Dict:
        """Get agent portfolio information"""
        try:
            response = self.session.get(f"{self.base_url}/api/agent/balances")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Portfolio fetch error: {e}")
            return {}
    
    def get_agent_profile(self) -> Dict:
        """Get authenticated agent profile"""
        try:
            response = self.session.get(f"{self.base_url}/api/agent/profile")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Profile fetch error: {e}")
            return {}
    
    def get_trade_history(self) -> Dict:
        """Get agent trade history"""
        try:
            response = self.session.get(f"{self.base_url}/api/agent/trades")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Trade history fetch error: {e}")
            return {}
    
    def get_token_price(self, token_address: str, chain: str = "evm", specific_chain: str = "eth") -> Optional[float]:
        """Get current token price"""
        try:
            params = {
                "token": token_address,
                "chain": chain,
                "specificChain": specific_chain
            }
            response = self.session.get(f"{self.base_url}/api/price", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("price")
        except Exception as e:
            print(f"Price fetch error: {e}")
            return None
    
    def execute_trade(self, from_token: str, to_token: str, amount: str, reason: str = "Perso-1903 trade") -> Dict:
        """Execute a trade"""
        try:
            payload = {
                "fromToken": from_token,
                "toToken": to_token,
                "amount": amount,
                "reason": reason
            }
            response = self.session.post(f"{self.base_url}/api/trade/execute", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Trade execution error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_leaderboard(self) -> Dict:
        """Get competition leaderboard"""
        try:
            response = self.session.get(f"{self.base_url}/api/competition/leaderboard")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Leaderboard fetch error: {e}")
            return {}

# Usage example
if __name__ == "__main__":
    try:
        # Initialize client with environment variables
        client = Perso1903TradingClient()
        
        # Test portfolio fetch
        portfolio = client.get_portfolio()
        print("Portfolio:", json.dumps(portfolio, indent=2))
        
        # Test profile fetch
        profile = client.get_agent_profile()
        print("Profile:", json.dumps(profile, indent=2))
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please create a .env file with your API keys (see env.example)")
    except Exception as e:
        print(f"Error: {e}")
