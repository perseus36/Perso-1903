#!/usr/bin/env python3
"""
Competition Rules Manager
Yeni Recall yarışması kurallarını yönetir ve günlük minimum işlem kontrolü yapar
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from perso_1903_client import get_competition_rules, get_competition_status, get_trade_history

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/competition_rules.jsonl'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompetitionRulesManager:
    """Yarışma kuralları yöneticisi"""
    
    def __init__(self):
        self.rules_file = "competition_rules.json"
        self.daily_trades_file = "daily_trades.json"
        self.current_rules = {}
        self.daily_trades = {}
        
        # Yarışma kurallarını yükle
        self.load_competition_rules()
        
        # Günlük işlemleri yükle
        self.load_daily_trades()
        
        logger.info("🏆 Competition Rules Manager başlatıldı")
    
    def load_competition_rules(self) -> None:
        """Yarışma kurallarını yükle"""
        try:
            # API'den güncel kuralları çek
            rules_response = get_competition_rules()
            if rules_response.get("success"):
                self.current_rules = rules_response
                logger.info("✅ Yarışma kuralları API'den yüklendi")
            else:
                logger.warning("⚠️ API'den kurallar alınamadı, varsayılan kurallar kullanılıyor")
                self.current_rules = self.get_default_rules()
            
            # Dosyaya kaydet
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_rules, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"❌ Kurallar yüklenirken hata: {e}")
            self.current_rules = self.get_default_rules()
    
    def get_default_rules(self) -> Dict[str, Any]:
        """Varsayılan yarışma kuralları"""
        return {
            "competition_period": {
                "start": "2024-09-22T09:00:00-04:00",  # 9 am ET Monday
                "end": "2024-09-26T09:00:00-04:00"     # 9 am ET Friday
            },
            "daily_requirements": {
                "min_trades_per_day": 3,
                "day_start_hour": 9,  # ET
                "day_end_hour": 9     # ET next day
            },
            "token_criteria": {
                "min_token_age_hours": 4380,
                "min_24h_volume": 500000,
                "min_liquidity": 500000,
                "min_fdv": 1000000
            },
            "starting_balances": {
                "ethereum": 5000,  # USDC
                "polygon": 5000,   # USDC
                "base": 5000,      # USDC
                "arbitrum": 5000,  # USDC
                "optimism": 5000,  # USDC
                "solana": 5000     # USDC
            }
        }
    
    def load_daily_trades(self) -> None:
        """Günlük işlemleri yükle"""
        try:
            if os.path.exists(self.daily_trades_file):
                with open(self.daily_trades_file, 'r', encoding='utf-8') as f:
                    self.daily_trades = json.load(f)
                logger.info(f"✅ Günlük işlemler yüklendi: {len(self.daily_trades)} gün")
            else:
                self.daily_trades = {}
                logger.info("📝 Yeni günlük işlem dosyası oluşturuldu")
        except Exception as e:
            logger.error(f"❌ Günlük işlemler yüklenirken hata: {e}")
            self.daily_trades = {}
    
    def save_daily_trades(self) -> None:
        """Günlük işlemleri kaydet"""
        try:
            with open(self.daily_trades_file, 'w', encoding='utf-8') as f:
                json.dump(self.daily_trades, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Günlük işlemler kaydedilirken hata: {e}")
    
    def get_current_day_key(self) -> str:
        """Mevcut günün anahtarını döndür (ET saatine göre)"""
        # ET saatini hesapla (UTC-4 veya UTC-5)
        now_utc = datetime.utcnow()
        # Basit ET hesaplama (yaz saati için UTC-4)
        et_offset = timedelta(hours=4)
        now_et = now_utc - et_offset
        
        # Günlük periyod: 9 AM ET'den 9 AM ET'ye kadar
        day_start_hour = 9
        if now_et.hour < day_start_hour:
            # Henüz yeni gün başlamamış, önceki gün
            day_date = (now_et - timedelta(days=1)).date()
        else:
            # Yeni gün başlamış
            day_date = now_et.date()
        
        return day_date.strftime("%Y-%m-%d")
    
    def record_trade(self, trade_data: Dict[str, Any]) -> None:
        """İşlemi kaydet"""
        day_key = self.get_current_day_key()
        
        if day_key not in self.daily_trades:
            self.daily_trades[day_key] = {
                "trades": [],
                "trade_count": 0,
                "total_volume": 0.0,
                "last_trade_time": None
            }
        
        # İşlemi ekle
        self.daily_trades[day_key]["trades"].append(trade_data)
        self.daily_trades[day_key]["trade_count"] += 1
        self.daily_trades[day_key]["total_volume"] += float(trade_data.get("amount_usd", 0))
        self.daily_trades[day_key]["last_trade_time"] = datetime.now().isoformat()
        
        # Dosyaya kaydet
        self.save_daily_trades()
        
        logger.info(f"[TRADE] İşlem kaydedildi: {day_key} - Toplam: {self.daily_trades[day_key]['trade_count']}")
    
    def get_daily_trade_count(self, day_key: Optional[str] = None) -> int:
        """Belirli bir günün işlem sayısını döndür"""
        if day_key is None:
            day_key = self.get_current_day_key()
        
        return self.daily_trades.get(day_key, {}).get("trade_count", 0)
    
    def check_daily_requirement(self, day_key: Optional[str] = None) -> Dict[str, Any]:
        """Günlük minimum işlem gereksinimini kontrol et"""
        if day_key is None:
            day_key = self.get_current_day_key()
        
        current_count = self.get_daily_trade_count(day_key)
        min_required = self.current_rules.get("daily_requirements", {}).get("min_trades_per_day", 3)
        
        remaining_trades = max(0, min_required - current_count)
        
        return {
            "day": day_key,
            "current_trades": current_count,
            "min_required": min_required,
            "remaining_trades": remaining_trades,
            "requirement_met": current_count >= min_required,
            "status": "✅ Tamamlandı" if current_count >= min_required else f"⚠️ {remaining_trades} işlem eksik"
        }
    
    def get_competition_status(self) -> Dict[str, Any]:
        """Yarışma durumunu kontrol et"""
        try:
            # API'den durumu çek
            status_response = get_competition_status()
            if status_response.get("success"):
                return status_response
            
            # API başarısızsa yerel kontrol
            return self.check_local_competition_status()
            
        except Exception as e:
            logger.error(f"❌ Yarışma durumu kontrol edilirken hata: {e}")
            return {"success": False, "error": str(e)}
    
    def check_local_competition_status(self) -> Dict[str, Any]:
        """Yerel yarışma durumu kontrolü"""
        try:
            now = datetime.now()
            
            # Yarışma tarihlerini kontrol et
            start_str = self.current_rules.get("competition_period", {}).get("start", "")
            end_str = self.current_rules.get("competition_period", {}).get("end", "")
            
            if start_str and end_str:
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                
                is_active = start_time <= now <= end_time
                
                return {
                    "success": True,
                    "active": is_active,
                    "start_time": start_str,
                    "end_time": end_str,
                    "current_time": now.isoformat(),
                    "days_remaining": (end_time - now).days if is_active else 0
                }
            
            return {"success": False, "error": "Yarışma tarihleri bulunamadı"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_trade_history_from_api(self, limit: int = 100) -> List[Dict[str, Any]]:
        """API'den işlem geçmişini çek"""
        try:
            history_response = get_trade_history(limit)
            if history_response.get("success"):
                return history_response.get("trades", [])
            else:
                logger.warning(f"⚠️ API'den işlem geçmişi alınamadı: {history_response.get('error')}")
                return []
        except Exception as e:
            logger.error(f"❌ İşlem geçmişi alınırken hata: {e}")
            return []
    
    def sync_daily_trades_with_api(self) -> None:
        """Günlük işlemleri API ile senkronize et"""
        try:
            logger.info("🔄 Günlük işlemler API ile senkronize ediliyor...")
            
            # API'den son işlemleri çek
            api_trades = self.get_trade_history_from_api(100)
            
            if not api_trades:
                logger.warning("⚠️ API'den işlem geçmişi alınamadı")
                return
            
            # Her işlemi günlük dosyaya ekle
            for trade in api_trades:
                trade_time = trade.get("timestamp", "")
                if trade_time:
                    try:
                        # Timestamp'i parse et ve gün anahtarını bul
                        trade_datetime = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
                        # ET'ye çevir
                        et_offset = timedelta(hours=4)
                        trade_et = trade_datetime - et_offset
                        
                        # Günlük periyod kontrolü
                        day_start_hour = 9
                        if trade_et.hour < day_start_hour:
                            day_date = (trade_et - timedelta(days=1)).date()
                        else:
                            day_date = trade_et.date()
                        
                        day_key = day_date.strftime("%Y-%m-%d")
                        
                        # İşlemi kaydet
                        self.record_trade({
                            "timestamp": trade_time,
                            "amount_usd": trade.get("amount", 0),
                            "token_symbol": trade.get("symbol", "UNKNOWN"),
                            "trade_type": trade.get("type", "unknown"),
                            "source": "api_sync"
                        })
                        
                    except Exception as e:
                        logger.warning(f"⚠️ İşlem parse edilemedi: {e}")
                        continue
            
            logger.info("[SYNC] Günlük işlemler API ile senkronize edildi")
            
        except Exception as e:
            logger.error(f"❌ API senkronizasyon hatası: {e}")
    
    def generate_daily_report(self, day_key: Optional[str] = None) -> str:
        """Günlük rapor oluştur"""
        if day_key is None:
            day_key = self.get_current_day_key()
        
        requirement_check = self.check_daily_requirement(day_key)
        day_data = self.daily_trades.get(day_key, {})
        
        report = f"""
🏆 GÜNLÜK YARIŞMA RAPORU - {day_key}
{'=' * 50}

📊 İşlem Durumu:
   • Mevcut İşlemler: {requirement_check['current_trades']}
   • Minimum Gereksinim: {requirement_check['min_required']}
   • Kalan İşlemler: {requirement_check['remaining_trades']}
   • Durum: {requirement_check['status']}

💰 İşlem Detayları:
   • Toplam Hacim: ${day_data.get('total_volume', 0):,.2f}
   • Son İşlem: {day_data.get('last_trade_time', 'Yok')}
   • İşlem Sayısı: {day_data.get('trade_count', 0)}

📋 Son İşlemler:
"""
        
        trades = day_data.get("trades", [])
        if trades:
            for i, trade in enumerate(trades[-5:], 1):  # Son 5 işlem
                report += f"   {i}. {trade.get('token_symbol', 'UNKNOWN')} - ${trade.get('amount_usd', 0):,.2f}\n"
        else:
            report += "   Henüz işlem yapılmamış\n"
        
        return report
    
    def get_competition_summary(self) -> Dict[str, Any]:
        """Yarışma özeti"""
        status = self.get_competition_status()
        current_day_check = self.check_daily_requirement()
        
        return {
            "competition_status": status,
            "daily_requirement": current_day_check,
            "rules": self.current_rules,
            "total_days_tracked": len(self.daily_trades),
            "last_updated": datetime.now().isoformat()
        }


def main():
    """Ana fonksiyon"""
    print("🏆 COMPETITION RULES MANAGER")
    print("=" * 50)
    
    # Manager oluştur
    manager = CompetitionRulesManager()
    
    # Yarışma durumu
    print("\n🔍 Yarışma Durumu:")
    status = manager.get_competition_status()
    if status.get("success"):
        print(f"   Aktif: {'✅ Evet' if status.get('active') else '❌ Hayır'}")
        if status.get("active"):
            print(f"   Kalan Günler: {status.get('days_remaining', 0)}")
    else:
        print(f"   ❌ Durum alınamadı: {status.get('error')}")
    
    # Günlük gereksinim kontrolü
    print("\n📊 Günlük İşlem Kontrolü:")
    daily_check = manager.check_daily_requirement()
    print(f"   Gün: {daily_check['day']}")
    print(f"   Mevcut İşlemler: {daily_check['current_trades']}")
    print(f"   Minimum Gereksinim: {daily_check['min_required']}")
    print(f"   Durum: {daily_check['status']}")
    
    # Günlük rapor
    print("\n📋 Günlük Rapor:")
    report = manager.generate_daily_report()
    print(report)
    
    # API senkronizasyonu
    print("\n🔄 API Senkronizasyonu:")
    manager.sync_daily_trades_with_api()
    
    print("\n✅ Competition Rules Manager test tamamlandı!")


if __name__ == "__main__":
    main()
