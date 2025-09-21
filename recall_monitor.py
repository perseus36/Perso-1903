#!/usr/bin/env python3
"""
Perso-1903 Agent - Recall API Sürekli İzleme Sistemi
"""

import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List
from perso_1903_client import get_portfolio, get_balances, get_health, get_price
from perso_1903_agent import Perso1903Agent

# Logging ayarla
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.jsonl', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RecallAPIMonitor:
    """Recall API sürekli izleme sistemi"""
    
    def __init__(self):
        self.agent = Perso1903Agent()
        self.running = False
        self.last_portfolio_value = 0
        self.last_token_count = 0
        self.monitoring_thread = None
        
        logger.info("Recall API Monitor baslatildi")
    
    def check_api_health(self) -> bool:
        """API sağlık kontrolü"""
        try:
            health = get_health()
            if health.get('success'):
                logger.info("Recall API saglikli")
                return True
            else:
                logger.warning(f"API saglik sorunu: {health.get('error')}")
                return False
        except Exception as e:
            logger.error(f"API saglik kontrolu hatasi: {e}")
            return False
    
    def get_portfolio_data(self) -> Dict[str, Any]:
        """Portföy verilerini çek"""
        try:
            portfolio = get_portfolio()
            if portfolio.get('success'):
                return portfolio
            else:
                logger.error(f"Portfolio alinamadi: {portfolio.get('error')}")
                return {"success": False, "error": portfolio.get('error')}
        except Exception as e:
            logger.error(f"Portfolio cekme hatasi: {e}")
            return {"success": False, "error": str(e)}
    
    def analyze_portfolio_changes(self, current_portfolio: Dict[str, Any]):
        """Portföy değişikliklerini analiz et"""
        if not current_portfolio.get('success'):
            return
        
        current_value = current_portfolio.get('totalValue', 0)
        current_token_count = len(current_portfolio.get('tokens', []))
        
        # Değer değişikliği kontrolü
        if self.last_portfolio_value > 0:
            value_change = current_value - self.last_portfolio_value
            value_change_pct = (value_change / self.last_portfolio_value * 100) if self.last_portfolio_value > 0 else 0
            
            if abs(value_change) > 100:  # $100'dan fazla değişiklik
                logger.info(f"Portfolio deger degisikligi: ${value_change:+,.2f} ({value_change_pct:+.2f}%)")
                logger.info(f"  Onceki: ${self.last_portfolio_value:,.2f}")
                logger.info(f"  Simdiki: ${current_value:,.2f}")
        
        # Token sayısı değişikliği kontrolü
        if self.last_token_count > 0 and current_token_count != self.last_token_count:
            logger.info(f"Token sayisi degisti: {self.last_token_count} -> {current_token_count}")
        
        # En büyük pozisyonları logla
        tokens = current_portfolio.get('tokens', [])
        if tokens:
            sorted_tokens = sorted(tokens, key=lambda x: float(x.get('value', 0)), reverse=True)
            top_3 = sorted_tokens[:3]
            
            logger.info("En buyuk 3 pozisyon:")
            for i, token in enumerate(top_3, 1):
                symbol = token.get('symbol', 'N/A')
                chain = token.get('specificChain', 'N/A')
                value = float(token.get('value', 0))
                pct = (value / current_value * 100) if current_value > 0 else 0
                logger.info(f"  {i}. {symbol} ({chain}): ${value:,.2f} ({pct:.1f}%)")
        
        # Güncelle
        self.last_portfolio_value = current_value
        self.last_token_count = current_token_count
    
    def monitor_portfolio(self):
        """Portföyü sürekli izle"""
        logger.info("Portfolio izleme baslatildi")
        
        while self.running:
            try:
                # API sağlık kontrolü
                if not self.check_api_health():
                    logger.warning("API saglik sorunu - 30 saniye bekleniyor")
                    time.sleep(30)
                    continue
                
                # Portföy verilerini çek
                portfolio = self.get_portfolio_data()
                
                if portfolio.get('success'):
                    # Değişiklikleri analiz et
                    self.analyze_portfolio_changes(portfolio)
                    
                    # Genel durum logla (her 10 dakikada bir)
                    if int(time.time()) % 600 == 0:  # Her 10 dakikada
                        total_value = portfolio.get('totalValue', 0)
                        token_count = len(portfolio.get('tokens', []))
                        logger.info(f"Portfolio durumu: ${total_value:,.2f}, {token_count} token")
                
                # 60 saniye bekle
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Portfolio izleme durduruldu")
                break
            except Exception as e:
                logger.error(f"Portfolio izleme hatasi: {e}")
                time.sleep(30)  # Hata durumunda 30 saniye bekle
    
    def start_monitoring(self):
        """İzlemeyi başlat"""
        if self.running:
            logger.warning("İzleme zaten çalışıyor")
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self.monitor_portfolio, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Recall API izleme sistemi başlatıldı")
        logger.info("Portfolio her 60 saniyede bir kontrol edilecek")
    
    def stop_monitoring(self):
        """İzlemeyi durdur"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Recall API izleme sistemi durduruldu")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Mevcut durumu al"""
        portfolio = self.get_portfolio_data()
        health = get_health()
        
        return {
            "api_health": health.get('success', False),
            "portfolio": portfolio,
            "monitoring_active": self.running,
            "last_check": datetime.now().isoformat()
        }

def main():
    """Ana fonksiyon"""
    print("🚀 Perso-1903 Agent - Recall API İzleme Sistemi")
    print("=" * 60)
    
    # Monitor oluştur
    monitor = RecallAPIMonitor()
    
    # İlk durum kontrolü
    print("\n🔍 İlk Durum Kontrolü:")
    status = monitor.get_current_status()
    
    if status["api_health"]:
        print("✅ Recall API sağlıklı")
    else:
        print("❌ Recall API sağlık sorunu")
        return
    
    portfolio = status["portfolio"]
    if portfolio.get("success"):
        total_value = portfolio.get("totalValue", 0)
        token_count = len(portfolio.get("tokens", []))
        print(f"💰 Portfolio: ${total_value:,.2f}")
        print(f"🪙 Token Sayısı: {token_count}")
    else:
        print("❌ Portfolio alınamadı")
        return
    
    # İzlemeyi başlat
    print("\n🔄 İzleme Başlatılıyor...")
    monitor.start_monitoring()
    
    try:
        print("\n📊 İzleme Aktif - Çıkmak için Ctrl+C")
        print("Portfolio her 60 saniyede kontrol edilecek")
        print("Değişiklikler otomatik olarak loglanacak")
        
        # Ana döngü
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 İzleme durduruluyor...")
        monitor.stop_monitoring()
        print("✅ İzleme sistemi kapatıldı")

if __name__ == "__main__":
    main()
