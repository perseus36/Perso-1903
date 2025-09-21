#!/usr/bin/env python3
"""
Perso-1903 Trading Client
Clean implementation based on Recall Network API documentation
"""

import os
import requests
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== CLIENT: match agent env resolution =====
RECALL_ENV = os.getenv("RECALL_ENV", "production").strip().lower()
IS_PROD = RECALL_ENV == "production"

RECALL_API_BASE = (
    os.getenv("RECALL_API_BASE_PROD", "").strip() if IS_PROD 
    else os.getenv("RECALL_API_BASE_SANDBOX", "").strip()
)
RECALL_API_KEY = (
    os.getenv("RECALL_API_KEY_PROD", "").strip() if IS_PROD 
    else os.getenv("RECALL_API_KEY_SANDBOX", "").strip()
)

# Fallback to hardcoded values if env vars are not set
if not RECALL_API_BASE:
    RECALL_API_BASE = "https://api.competitions.recall.network"
if not RECALL_API_KEY:
    RECALL_API_KEY = os.getenv("RECALL_API_KEY_PRODUCTION", "")

if not RECALL_API_KEY:
    raise RuntimeError(f"Client missing Recall API config for {RECALL_ENV}")

def _headers():
    """Generate headers for API requests"""
    return {
        "Authorization": f"Bearer {RECALL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Perso-1903/client (prod-first)"
    }

def get_balances() -> Dict[str, Any]:
    """Get agent balances"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/agent/balances", 
            headers=_headers(), 
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching balances: {e}")
        return {"success": False, "error": str(e)}

def get_portfolio() -> Dict[str, Any]:
    """Get agent portfolio (using balances endpoint) - RECALL API ONLY"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/agent/balances", 
            headers=_headers(), 
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            balances = data.get("balances", [])
            total_value = 0
            tokens = []
            
            for balance in balances:
                # Use actual value from API
                value = balance.get("value", 0)
                price = balance.get("price", 0)
                
                token_data = {
                    "tokenAddress": balance.get("tokenAddress"),
                    "symbol": balance.get("symbol"),
                    "chain": balance.get("chain"),
                    "specificChain": balance.get("specificChain"),
                    "amount": balance.get("amount", 0),
                    "value": value,
                    "price": price
                }
                tokens.append(token_data)
                total_value += value
            
            return {
                "success": True,
                "totalValue": total_value,
                "tokens": tokens,
                "agentId": data.get("agentId"),
                "snapshotTime": data.get("snapshotTime")
            }
        return data
    except Exception as e:
        print(f"❌ Error fetching portfolio: {e}")
        return {"success": False, "error": str(e)}

def get_profile() -> Dict[str, Any]:
    """Get agent profile"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/agent/profile", 
            headers=_headers(), 
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching profile: {e}")
        return {"success": False, "error": str(e)}

def get_price(token_address: str, chain: str = "evm", specific_chain: str = "eth") -> Dict[str, Any]:
    """Get token price"""
    try:
        params = {
            "token": token_address,
            "chain": chain,
            "specificChain": specific_chain
        }
        response = requests.get(
            f"{RECALL_API_BASE}/api/price", 
            params=params,
            headers=_headers(), 
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching price: {e}")
        return {"success": False, "error": str(e)}

def execute_trade(from_token: str, to_token: str, amount: str, 
                 from_chain: str = "evm", to_chain: str = "evm",
                 from_specific_chain: str = "eth", to_specific_chain: str = "eth",
                 reason: str = "Trading strategy execution") -> Dict[str, Any]:
    """Execute a trade"""
    try:
        payload = {
            "fromToken": from_token,
            "toToken": to_token,
            "amount": amount,
            "fromChain": from_chain,
            "toChain": to_chain,
            "fromSpecificChain": from_specific_chain,
            "toSpecificChain": to_specific_chain,
            "reason": reason
        }
        
        print(f"🔍 DEBUG - Trade Payload:")
        print(json.dumps(payload, indent=2))
        
        response = requests.post(
            f"{RECALL_API_BASE}/api/trade/execute", 
            json=payload,
            headers=_headers(),
            timeout=30
        )
        
        print(f"🔍 DEBUG - Response Status: {response.status_code}")
        print(f"🔍 DEBUG - Response Headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"🔍 DEBUG - Response Text: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error executing trade: {e}")
        return {"success": False, "error": str(e)}

def get_health() -> Dict[str, Any]:
    """Get API health status"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/health", 
            headers=_headers(), 
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        # API returns {"status": "ok"} not {"success": true}
        return {"success": data.get("status") == "ok", "data": data}
    except Exception as e:
        print(f"❌ Error fetching health: {e}")
        return {"success": False, "error": str(e)}

def get_competition_rules() -> Dict[str, Any]:
    """Get competition rules"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/competitions/rules", 
            headers=_headers(), 
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching competition rules: {e}")
        return {"success": False, "error": str(e)}

def get_competition_status() -> Dict[str, Any]:
    """Get competition status"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/competitions/status", 
            headers=_headers(), 
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching competition status: {e}")
        return {"success": False, "error": str(e)}

def get_competition_leaderboard() -> Dict[str, Any]:
    """Get competition leaderboard"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/competitions/leaderboard", 
            headers=_headers(), 
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching competition leaderboard: {e}")
        return {"success": False, "error": str(e)}

def get_competitions() -> Dict[str, Any]:
    """Get all competitions"""
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/competitions", 
            headers=_headers(), 
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching competitions: {e}")
        return {"success": False, "error": str(e)}

def get_trade_history(limit: int = 50) -> Dict[str, Any]:
    """Get agent trade history from Recall API"""
    try:
        params = {"limit": limit} if limit else {}
        response = requests.get(
            f"{RECALL_API_BASE}/api/agent/trades", 
            params=params,
            headers=_headers(), 
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching trade history: {e}")
        return {"success": False, "error": str(e)}

def get_agent_transactions(limit: int = 50) -> Dict[str, Any]:
    """Get agent transactions from Recall API"""
    try:
        params = {"limit": limit} if limit else {}
        response = requests.get(
            f"{RECALL_API_BASE}/api/agent/transactions", 
            params=params,
            headers=_headers(), 
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching transactions: {e}")
        return {"success": False, "error": str(e)}

# ===== MAIN EXECUTION =====
def main():
    """Main execution function for testing"""
    print("🚀 Starting Perso-1903 Trading Client")
    print(f"🌐 Environment: {RECALL_ENV}")
    print(f"🔗 API Base: {RECALL_API_BASE}")
    
    # Test health
    print("\n🔍 Testing API Health...")
    health = get_health()
    if health.get("success"):
        print("✅ API Health: OK")
    else:
        print("❌ API Health: FAILED")
        return
    
    # Test portfolio
    print("\n📊 Testing Portfolio...")
    portfolio = get_portfolio()
    if portfolio.get("success"):
        total_value = portfolio.get("totalValue", 0)
        tokens = portfolio.get("tokens", [])
        print(f"✅ Portfolio Value: ${total_value:,.2f}")
        print(f"✅ Token Count: {len(tokens)}")
    else:
        print("❌ Portfolio fetch failed")
    
    # Test balances
    print("\n💰 Testing Balances...")
    balances = get_balances()
    if balances.get("success"):
        print("✅ Balances fetched successfully")
    else:
        print("❌ Balances fetch failed")
    
    # Test competition rules
    print("\n📋 Testing Competition Rules...")
    rules = get_competition_rules()
    if rules.get("success"):
        print("✅ Competition rules fetched successfully")
    else:
        print("❌ Competition rules fetch failed")
    
    # Test competition status
    print("\n🏆 Testing Competition Status...")
    status = get_competition_status()
    if status.get("success"):
        active = status.get("active", False)
        print(f"✅ Competition status: {'Active' if active else 'Inactive'}")
    else:
        print("❌ Competition status fetch failed")
    
    # Test leaderboard
    print("\n🏅 Testing Leaderboard...")
    leaderboard = get_competition_leaderboard()
    if leaderboard.get("success"):
        leaderboard_data = leaderboard.get("leaderboard", [])
        print(f"✅ Leaderboard fetched: {len(leaderboard_data)} agents")
    else:
        print("❌ Leaderboard fetch failed")
    
    print("\n🎯 Client testing completed")

if __name__ == "__main__":
    main()