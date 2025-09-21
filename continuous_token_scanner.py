#!/usr/bin/env python3
"""
Continuous Dynamic Token Scanner
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

# Global variables for tracking
SCAN_COUNT = 0
TOTAL_TOKENS_FOUND = 0
TOTAL_ANALYZED = 0
ANOMALIES_FOUND = 0
SCANNED_TOKENS = set()  # Taranan tokenleri takip etmek için

def _headers():
    """Generate headers for Recall API requests"""
    return {
        "Authorization": f"Bearer {RECALL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Perso-1903/continuous-scanner"
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

def filter_tokens_by_criteria(tokens: List[Dict[str, Any]], 
                            min_volume: float = 100,
                            min_liquidity: float = 1000) -> List[Dict[str, Any]]:
    """Tokenleri kriterlere göre filtrele ve daha önce tarananları hariç tut"""
    global SCANNED_TOKENS
    filtered_tokens = []
    new_tokens = []
    
    print(f"🔍 Token filtreleme başlatılıyor...")
    print(f"📊 Kriterler: Min Hacim=${min_volume:,}, Min Likidite=${min_liquidity:,}")
    print(f"📋 Çekilen tokenler:")
    
    for i, token in enumerate(tokens):
        try:
            # Token adresini çıkar
            address = None
            if 'baseToken' in token:  # DexScreener formatı
                address = token.get('baseToken', {}).get('address', '')
            elif 'id' in token:  # CoinGecko formatı
                # CoinGecko için adres çıkarma daha karmaşık, şimdilik id kullan
                address = token.get('id', '')
            
            # Token bilgilerini göster
            symbol = token.get('baseToken', {}).get('symbol', token.get('symbol', 'UNKNOWN'))
            name = token.get('baseToken', {}).get('name', token.get('name', 'Unknown'))
            
            if i < 10:  # İlk 10 token için detay göster
                print(f"   {i+1:2d}. {symbol:<8} | {name[:20]:<20} | {address[:20] if address else 'N/A':<20}")
            
            # DexScreener formatı için
            if 'volume' in token and 'liquidity' in token:
                volume_usd = float(token.get('volume', {}).get('h24', 0))
                liquidity_usd = float(token.get('liquidity', {}).get('usd', 0))
                
                # Sadece hacim ve likidite kontrolü
                if volume_usd >= min_volume and liquidity_usd >= min_liquidity:
                    # Daha önce taranmış mı kontrol et
                    if address and address not in SCANNED_TOKENS:
                        filtered_tokens.append(token)
                        new_tokens.append(token)
                        SCANNED_TOKENS.add(address)
                    elif address in SCANNED_TOKENS:
                        print(f"   ⏭️  {symbol} zaten taranmış, atlanıyor")
            
            # CoinGecko formatı için (farklı kriterler)
            elif 'market_cap_rank' in token:
                # CoinGecko tokenleri için farklı filtreleme
                if token.get('market_cap_rank', 0) <= 1000:  # Top 1000
                    if address and address not in SCANNED_TOKENS:
                        filtered_tokens.append(token)
                        new_tokens.append(token)
                        SCANNED_TOKENS.add(address)
                    
        except Exception as e:
            continue
    
    print(f"✅ {len(tokens)} token'den {len(filtered_tokens)} tanesi kriterlere uygun")
    print(f"🆕 {len(new_tokens)} yeni token (daha önce taranmamış)")
    print(f"📊 Toplam taranan token sayısı: {len(SCANNED_TOKENS)}")
    
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
                       limit: int = 5,
                       min_volume: float = 100,
                       min_liquidity: float = 1000) -> List[Dict[str, Any]]:
    """Dinamik token taraması yap"""
    global SCAN_COUNT, TOTAL_TOKENS_FOUND, TOTAL_ANALYZED, ANOMALIES_FOUND
    
    SCAN_COUNT += 1
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n🚀 TARAMA #{SCAN_COUNT} - {current_time}")
    print(f"📊 Kaynak: {source.upper()}")
    print(f"🔢 Limit: {limit}")
    print(f"💰 Min Hacim: ${min_volume:,}")
    print(f"💧 Min Likidite: ${min_liquidity:,}")
    print(f"📊 Toplam Taranan Token: {len(SCANNED_TOKENS)}")
    print("-" * 60)
    
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
    
    print(f"✅ {len(filtered_tokens)} token kriterlere uygun")
    
    # Recall API'de kontrol et ve analiz yap
    results = []
    print(f"🔍 Recall API'de kontrol ediliyor...")
    
    for i, token in enumerate(filtered_tokens[:limit], 1):
        # Adres çıkar
        if source.lower() == "dexscreener":
            address = get_token_address_from_dexscreener(token)
        else:
            address = get_token_address_from_coingecko(token)
        
        if not address:
            continue
        
        # Recall API'de kontrol et
        recall_check = check_token_in_recall_api(address)
        if recall_check["found"]:
            TOTAL_TOKENS_FOUND += 1
            print(f"   ✅ Token {i} bulundu: {recall_check['data'].get('symbol', 'UNKNOWN')}")
            
            # Bug inflation analizi yap
            analysis = run_bug_inflation_analysis(address)
            if analysis["success"]:
                results.append(analysis)
                TOTAL_ANALYZED += 1
                
                # Anomali kontrolü
                if analysis["ratio"] != 1.00:
                    ANOMALIES_FOUND += 1
                    print(f"   🚨 ANOMALİ TESPİT EDİLDİ! Ratio: {analysis['ratio']:.2f}x")
        
        # Rate limit için bekleme
        time.sleep(0.3)
    
    return results

def print_continuous_results(results: List[Dict[str, Any]]):
    """Sürekli tarama sonuçlarını yazdır"""
    global SCAN_COUNT, TOTAL_TOKENS_FOUND, TOTAL_ANALYZED, ANOMALIES_FOUND
    
    print(f"\n📊 TARAMA #{SCAN_COUNT} SONUÇLARI")
    print("-" * 60)
    
    successful_results = [r for r in results if r.get("success", False)]
    
    if successful_results:
        print(f"✅ Bu taramada {len(successful_results)} token analiz edildi:")
        for r in successful_results:
            print(f"   • {r['symbol']} ({r['address'][:20]}...) - ${r['price']:.6f}")
    
    # Genel istatistikler
    print(f"\n📈 GENEL İSTATİSTİKLER:")
    print(f"   🔄 Toplam Tarama: {SCAN_COUNT}")
    print(f"   🎯 Bulunan Token: {TOTAL_TOKENS_FOUND}")
    print(f"   📊 Analiz Edilen: {TOTAL_ANALYZED}")
    print(f"   🚨 Anomali: {ANOMALIES_FOUND}")
    
    if TOTAL_TOKENS_FOUND > 0:
        success_rate = (TOTAL_ANALYZED / TOTAL_TOKENS_FOUND) * 100
        print(f"   📈 Başarı Oranı: {success_rate:.1f}%")

def continuous_scan():
    """Sürekli tarama döngüsü"""
    print("🔄 SÜREKLİ TOKEN TARAMASI BAŞLATILIYOR")
    print("=" * 60)
    print("⏰ Her 3 saniyede bir yeni tokenler taranacak")
    print("🛑 Durdurmak için Ctrl+C tuşlarına basın")
    print("=" * 60)
    
    try:
        while True:
            # DexScreener'dan tokenleri çek ve analiz et
            results = scan_dynamic_tokens(
                source="dexscreener",
                limit=5,
                min_volume=100,
                min_liquidity=1000
            )
            
            # Sonuçları yazdır
            print_continuous_results(results)
            
            # 3 saniye bekle
            print(f"\n⏰ Sonraki tarama için 3 saniye bekleniyor...")
            print(f"🕐 Sonraki tarama: {(datetime.now() + timedelta(seconds=3)).strftime('%H:%M:%S')}")
            print("=" * 60)
            
            time.sleep(3)  # 3 saniye
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Tarama durduruldu!")
        print(f"📊 Final İstatistikler:")
        print(f"   🔄 Toplam Tarama: {SCAN_COUNT}")
        print(f"   🎯 Bulunan Token: {TOTAL_TOKENS_FOUND}")
        print(f"   📊 Analiz Edilen: {TOTAL_ANALYZED}")
        print(f"   🚨 Anomali: {ANOMALIES_FOUND}")
        print("👋 Görüşürüz!")

def main():
    """Ana fonksiyon"""
    print("🔍 SÜREKLİ DİNAMİK TOKEN SCANNER")
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
    
    # Sürekli taramayı başlat
    continuous_scan()

if __name__ == "__main__":
    main()
