#!/usr/bin/env python3
"""
Dynamic Token Scanner
DexScreener ve CoinGecko API'lerini kullanarak sürekli token çekip bug inflation analizi yapar
"""

import os
import requests
import json
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# ===== API CONFIGURATION =====
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

# External API endpoints
DEXSCREENER_API = "https://api.dexscreener.com/latest"
COINGECKO_API = "https://api.coingecko.com/api/v3"

def _headers():
    """Generate headers for Recall API requests"""
    return {
        "Authorization": f"Bearer {RECALL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Perso-1903/dynamic-scanner"
    }

def get_trending_tokens_dexscreener(limit: int = 50) -> List[Dict[str, Any]]:
    """DexScreener'dan trending tokenleri çek"""
    try:
        print(f"🔍 DexScreener'dan {limit} trending token çekiliyor...")
        
        # DexScreener'ın doğru endpoint'i
        response = requests.get(f"{DEXSCREENER_API}/dex/search/?q=ethereum", timeout=15)
        
        if response.status_code != 200:
            print(f"❌ DexScreener API Error: {response.status_code}")
            return []
        
        data = response.json()
        if not data:
            print(f"❌ DexScreener API returned empty data")
            return []
            
        tokens = data.get('pairs', [])[:limit]
        
        print(f"✅ {len(tokens)} token DexScreener'dan çekildi")
        return tokens
        
    except Exception as e:
        print(f"❌ DexScreener API Error: {e}")
        return []

def get_trending_tokens_coingecko(limit: int = 50) -> List[Dict[str, Any]]:
    """CoinGecko'dan trending tokenleri çek"""
    try:
        print(f"🔍 CoinGecko'dan {limit} trending token çekiliyor...")
        
        # CoinGecko trending endpoint'i
        response = requests.get(f"{COINGECKO_API}/search/trending", timeout=15)
        
        if response.status_code != 200:
            print(f"❌ CoinGecko API Error: {response.status_code}")
            return []
        
        data = response.json()
        trending_coins = data.get('coins', [])[:limit]
        
        # CoinGecko formatını standartlaştır
        tokens = []
        for coin in trending_coins:
            item = coin.get('item', {})
            tokens.append({
                'symbol': item.get('symbol', '').upper(),
                'name': item.get('name', ''),
                'id': item.get('id', ''),
                'market_cap_rank': item.get('market_cap_rank', 0),
                'price_change_percentage_24h': item.get('price_change_percentage_24h', 0)
            })
        
        print(f"✅ {len(tokens)} token CoinGecko'dan çekildi")
        return tokens
        
    except Exception as e:
        print(f"❌ CoinGecko API Error: {e}")
        return []

def get_new_tokens_dexscreener(limit: int = 30) -> List[Dict[str, Any]]:
    """DexScreener'dan yeni tokenleri çek"""
    try:
        print(f"🔍 DexScreener'dan {limit} yeni token çekiliyor...")
        
        # DexScreener'da yeni tokenler için farklı endpoint'ler deneyebiliriz
        # Şimdilik trending kullanıyoruz ama gelecekte yeni token endpoint'i eklenebilir
        response = requests.get(f"{DEXSCREENER_API}/dex/search/?q=new", timeout=15)
        
        if response.status_code != 200:
            print(f"❌ DexScreener New Tokens API Error: {response.status_code}")
            return []
        
        data = response.json()
        tokens = data.get('pairs', [])[:limit]
        
        print(f"✅ {len(tokens)} yeni token DexScreener'dan çekildi")
        return tokens
        
    except Exception as e:
        print(f"❌ DexScreener New Tokens API Error: {e}")
        return []

def filter_tokens_by_criteria(tokens: List[Dict[str, Any]], 
                            min_volume: float = 100,
                            min_liquidity: float = 1000) -> List[Dict[str, Any]]:
    """Tokenleri kriterlere göre filtrele"""
    filtered_tokens = []
    
    print(f"🔍 Token filtreleme başlatılıyor...")
    print(f"📊 Kriterler: Min Hacim=${min_volume:,}, Min Likidite=${min_liquidity:,}")
    
    for i, token in enumerate(tokens):
        try:
            # DexScreener formatı için
            if 'volume' in token and 'liquidity' in token:
                volume_usd = float(token.get('volume', {}).get('h24', 0))
                liquidity_usd = float(token.get('liquidity', {}).get('usd', 0))
                
                # Debug bilgisi
                if i < 5:  # İlk 5 token için debug
                    print(f"   Token {i+1}: Volume=${volume_usd:,.0f}, Liquidity=${liquidity_usd:,.0f}")
                
                # Sadece hacim ve likidite kontrolü
                if volume_usd >= min_volume and liquidity_usd >= min_liquidity:
                    filtered_tokens.append(token)
                    print(f"   ✅ Token {i+1} kriterlere uygun!")
            
            # CoinGecko formatı için (farklı kriterler)
            elif 'market_cap_rank' in token:
                # CoinGecko tokenleri için farklı filtreleme
                if token.get('market_cap_rank', 0) <= 1000:  # Top 1000
                    filtered_tokens.append(token)
                    
        except Exception as e:
            print(f"⚠️ Token {i+1} filtreleme hatası: {e}")
            continue
    
    print(f"🔍 {len(tokens)} token'den {len(filtered_tokens)} tanesi kriterlere uygun")
    return filtered_tokens

def get_token_address_from_dexscreener(token: Dict[str, Any]) -> Optional[str]:
    """DexScreener token'ından adres çıkar"""
    try:
        # DexScreener'da token adresi baseToken içinde
        base_token = token.get('baseToken', {})
        address = base_token.get('address', '')
        
        if address and len(address) >= 40:  # Ethereum/Solana adres formatı
            return address
        return None
        
    except Exception as e:
        print(f"⚠️ Adres çıkarma hatası: {e}")
        return None

def get_token_address_from_coingecko(token: Dict[str, Any]) -> Optional[str]:
    """CoinGecko token'ından adres çıkar (daha karmaşık)"""
    try:
        # CoinGecko'da doğrudan adres yok, contract_address endpoint'i kullanılabilir
        coin_id = token.get('id', '')
        if not coin_id:
            return None
            
        # CoinGecko'dan token detaylarını çek
        response = requests.get(f"{COINGECKO_API}/coins/{coin_id}", timeout=15)
        if response.status_code == 200:
            data = response.json()
            platforms = data.get('platforms', {})
            
            # Ethereum adresini öncelikle ara
            if 'ethereum' in platforms:
                return platforms['ethereum']
            # Solana adresini ara
            elif 'solana' in platforms:
                return platforms['solana']
            # Diğer platformları ara
            elif platforms:
                return list(platforms.values())[0]
        
        return None
        
    except Exception as e:
        print(f"⚠️ CoinGecko adres çıkarma hatası: {e}")
        return None

def check_token_in_recall_api(address: str) -> Dict[str, Any]:
    """Token'ı Recall API'de kontrol et"""
    try:
        # Token adresine göre ağ belirleme
        if address.startswith("0x") and len(address) == 42:  # Ethereum
            chain = "evm"
            specific_chain = "eth"
        elif len(address) >= 40 and len(address) <= 50:  # Solana
            chain = "svm"
            specific_chain = "solana"
        else:
            # Varsayılan olarak Ethereum'da dene
            chain = "evm"
            specific_chain = "eth"
        
        params = {
            "token": address,
            "chain": chain,
            "specificChain": specific_chain
        }
        
        response = requests.get(
            f"{RECALL_API_BASE}/api/price", 
            params=params,
            headers=_headers(), 
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return {
                    "found": True,
                    "data": result,
                    "chain": specific_chain
                }
        
        return {"found": False, "error": "Token not found in Recall API"}
        
    except Exception as e:
        return {"found": False, "error": str(e)}

def run_bug_inflation_analysis(address: str, amount: float = 10000) -> Dict[str, Any]:
    """Token için bug inflation analizi yap"""
    try:
        # Token bilgilerini al
        recall_check = check_token_in_recall_api(address)
        if not recall_check["found"]:
            return {
                "address": address,
                "success": False,
                "error": "Token not found in Recall API"
            }
        
        token_data = recall_check["data"]
        symbol = token_data.get('symbol', 'UNKNOWN')
        price = float(token_data.get('price', 0))
        
        # Beklenen çıktı miktarını hesapla
        expected_amount = float(amount) / price if price > 0 else 0
        
        # Şişirme oranını hesapla (şimdilik 1.00x - gerçek quote API'si yok)
        ratio = 1.00
        
        return {
            "symbol": symbol,
            "address": address,
            "price": price,
            "expected": expected_amount,
            "output": expected_amount,  # Şimdilik aynı
            "ratio": ratio,
            "success": True,
            "chain": recall_check["chain"]
        }
        
    except Exception as e:
        return {
            "address": address,
            "success": False,
            "error": str(e)
        }

def scan_dynamic_tokens(source: str = "dexscreener", 
                       limit: int = 20,
                       min_volume: float = 10000,
                       min_liquidity: float = 50000) -> List[Dict[str, Any]]:
    """Dinamik token taraması yap"""
    print(f"🚀 DİNAMİK TOKEN TARAMASI BAŞLATILIYOR")
    print(f"📊 Kaynak: {source.upper()}")
    print(f"🔢 Limit: {limit}")
    print(f"💰 Min Hacim: ${min_volume:,}")
    print(f"💧 Min Likidite: ${min_liquidity:,}")
    print("=" * 80)
    
    # Tokenleri çek
    if source.lower() == "dexscreener":
        tokens = get_trending_tokens_dexscreener(limit * 2)  # Daha fazla çek, filtrele
    elif source.lower() == "coingecko":
        tokens = get_trending_tokens_coingecko(limit * 2)
    else:
        print(f"❌ Bilinmeyen kaynak: {source}")
        return []
    
    if not tokens:
        print("❌ Token çekilemedi")
        return []
    
    # Tokenleri filtrele
    filtered_tokens = filter_tokens_by_criteria(tokens, min_volume, min_liquidity)
    
    if not filtered_tokens:
        print("❌ Kriterlere uygun token bulunamadı")
        return []
    
    # Recall API'de kontrol et ve analiz yap
    results = []
    print(f"\n🔍 {len(filtered_tokens)} token Recall API'de kontrol ediliyor...")
    
    for i, token in enumerate(filtered_tokens[:limit], 1):
        print(f"\n[{i}/{min(limit, len(filtered_tokens))}] Processing token...")
        
        # Adres çıkar
        if source.lower() == "dexscreener":
            address = get_token_address_from_dexscreener(token)
        else:
            address = get_token_address_from_coingecko(token)
        
        if not address:
            print(f"   ❌ Adres çıkarılamadı")
            continue
        
        print(f"   🔍 Address: {address}")
        
        # Recall API'de kontrol et
        recall_check = check_token_in_recall_api(address)
        if recall_check["found"]:
            print(f"   ✅ Recall API'de bulundu!")
            
            # Bug inflation analizi yap
            analysis = run_bug_inflation_analysis(address)
            if analysis["success"]:
                results.append(analysis)
                print(f"   📊 Symbol: {analysis['symbol']}, Price: ${analysis['price']:.8f}")
            else:
                print(f"   ❌ Analiz başarısız: {analysis.get('error', 'Unknown error')}")
        else:
            print(f"   ❌ Recall API'de bulunamadı")
        
        # Rate limit için bekleme
        time.sleep(0.5)
    
    return results

def print_dynamic_results(results: List[Dict[str, Any]]):
    """Dinamik tarama sonuçlarını yazdır"""
    print("\n" + "=" * 80)
    print("🔍 DİNAMİK TOKEN TARAMA SONUÇLARI")
    print("=" * 80)
    
    successful_results = [r for r in results if r.get("success", False)]
    failed_results = [r for r in results if not r.get("success", False)]
    
    if successful_results:
        print(f"\n✅ BAŞARILI ANALİZLER ({len(successful_results)}):")
        print("-" * 80)
        print(f"{'Symbol':<10} | {'Address':<42} | {'Chain':<8} | {'Price':<12} | {'Ratio':<8}")
        print("-" * 80)
        
        for r in successful_results:
            print(f"{r['symbol']:<10} | {r['address']:<42} | "
                  f"{r.get('chain', 'N/A'):<8} | ${r['price']:<11.8f} | {r['ratio']:<7.2f}x")
    
    if failed_results:
        print(f"\n❌ BAŞARISIZ ANALİZLER ({len(failed_results)}):")
        print("-" * 80)
        for r in failed_results:
            print(f"{r['address']} -> Error: {r.get('error', 'Bilinmeyen hata')}")
    
    # En yüksek fiyatlı tokeni bul
    if successful_results:
        max_price = max(successful_results, key=lambda x: x.get("price", 0))
        print(f"\n🎯 EN YÜKSEK FİYATLI TOKEN:")
        print(f"   Token: {max_price['symbol']} ({max_price['address']})")
        print(f"   Fiyat: ${max_price['price']:.8f}")
        print(f"   Ağ: {max_price.get('chain', 'N/A')}")

def main():
    """Ana fonksiyon"""
    print("🔍 DİNAMİK TOKEN SCANNER")
    print("=" * 50)
    print(f"🌐 Environment: {RECALL_ENV}")
    print(f"🔗 Recall API Base: {RECALL_API_BASE}")
    print(f"🔗 DexScreener API: {DEXSCREENER_API}")
    print(f"🔗 CoinGecko API: {COINGECKO_API}")
    
    # API health check
    print(f"\n🔍 Recall API Health Check...")
    try:
        response = requests.get(
            f"{RECALL_API_BASE}/api/health", 
            headers=_headers(), 
            timeout=15
        )
        if response.status_code == 200:
            print("✅ Recall API Health: OK")
        else:
            print(f"❌ Recall API Health: FAILED ({response.status_code})")
            return
    except Exception as e:
        print(f"❌ Recall API Health Check Failed: {e}")
        return
    
    # Dinamik tarama seçenekleri
    print(f"\n📋 Tarama Seçenekleri:")
    print("1. DexScreener Trending Tokens")
    print("2. CoinGecko Trending Tokens")
    print("3. DexScreener New Tokens")
    
    # Şimdilik DexScreener trending ile başla
    source = "dexscreener"
    limit = 5
    min_volume = 100  # $100 minimum hacim
    min_liquidity = 1000  # $1K minimum likidite
    
    print(f"\n🚀 DexScreener Trending Tokens ile tarama başlatılıyor...")
    
    # Dinamik taramayı başlat
    results = scan_dynamic_tokens(
        source=source,
        limit=limit,
        min_volume=min_volume,
        min_liquidity=min_liquidity
    )
    
    # Sonuçları yazdır
    print_dynamic_results(results)
    
    print(f"\n🎉 Dinamik tarama tamamlandı!")
    print(f"📊 Toplam analiz edilen token: {len(results)}")

if __name__ == "__main__":
    main()
