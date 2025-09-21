#!/usr/bin/env python3
"""
Perso-1903 Manuel Emir Sistemi
Recall API odaklı limit ve market emir sistemi
"""

import os
import time
import logging
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from perso_1903_client import (
    get_portfolio, get_price, execute_trade, 
    get_health, get_competition_rules
)
from competition_rules_manager import CompetitionRulesManager

# Environment setup
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.jsonl'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ManualOrderSystem:
    """Manuel emir sistemi - Recall API odaklı"""
    
    def __init__(self):
        self.active_orders = {}  # Aktif emirler
        self.order_counter = 0   # Emir sayaç
        self.order_history = []  # Emir geçmişi
        # Fiyat takip sistemi kaldırıldı
        self.competition_manager = CompetitionRulesManager()  # Yarışma kuralları yöneticisi
        
        # API health check
        self.check_api_health()
        
        logger.info("🚀 Manuel Emir Sistemi başlatıldı")
        logger.info("📡 Recall API odaklı sistem aktif")
        logger.info("💰 Token fiyat takip sistemi aktif")
        logger.info("🏆 Yarışma kuralları yöneticisi aktif")
        
        # Sistem durumu raporu
        self.system_start_time = datetime.now()
        logger.info(f"⏰ Sistem başlatma zamanı: {self.system_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def get_system_uptime(self) -> str:
        """Sistem çalışma süresini döndür"""
        uptime = datetime.now() - self.system_start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumu raporu"""
        return {
            "start_time": self.system_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "uptime": self.get_system_uptime(),
            "active_orders": len(self.active_orders),
            "total_orders": self.order_counter,
            "api_health": self.check_api_health()
        }
    
    def check_api_health(self) -> bool:
        """API sağlık kontrolü"""
        try:
            health = get_health()
            if health.get("status") == "ok":
                logger.info("✅ Recall API sağlıklı")
                return True
            else:
                logger.warning(f"⚠️ API sağlık durumu: {health}")
                return False
        except Exception as e:
            logger.error(f"❌ API sağlık kontrolü başarısız: {e}")
            return False
    
    def create_limit_order(self, 
                          token_address: str, 
                          token_symbol: str,
                          chain: str,
                          specific_chain: str,
                          limit_price: float,
                          amount_usd: float,
                          order_type: str = "buy") -> Dict[str, Any]:
        """Limit emir oluştur"""
        
        self.order_counter += 1
        order_id = f"LIMIT_{self.order_counter:04d}"
        
        order = {
            "id": order_id,
            "type": "limit",
            "order_type": order_type,  # "buy" or "sell"
            "token_address": token_address,
            "token_symbol": token_symbol,
                "chain": chain,
            "specific_chain": specific_chain,
            "limit_price": limit_price,
            "amount_usd": amount_usd,
            "status": "active",
            "created_at": datetime.now(),
            "executed_at": None,
            "execution_price": None,
            "execution_amount": None
        }
        
        self.active_orders[order_id] = order
        self.order_history.append(order.copy())
        
        logger.info(f"📋 Limit emir oluşturuldu: {order_id}")
        logger.info(f"   Token: {token_symbol} ({token_address})")
        logger.info(f"   Ağ: {specific_chain}")
        logger.info(f"   Limit fiyat: ${limit_price:.4f}")
        logger.info(f"   Miktar: ${amount_usd:.2f}")
        logger.info(f"   Tip: {order_type.upper()}")
        
        return order
    
    def create_market_order(self,
                           token_address: str,
                           token_symbol: str,
                           chain: str,
                           specific_chain: str,
                           amount_usd: float,
                           order_type: str = "buy") -> Dict[str, Any]:
        """Market emir oluştur ve hemen çalıştır"""
        
        self.order_counter += 1
        order_id = f"MARKET_{self.order_counter:04d}"
        
        order = {
            "id": order_id,
            "type": "market",
            "order_type": order_type,
            "token_address": token_address,
            "token_symbol": token_symbol,
            "chain": chain,
            "specific_chain": specific_chain,
            "amount_usd": amount_usd,
            "status": "executing",
            "created_at": datetime.now(),
            "executed_at": None,
            "execution_price": None,
            "execution_amount": None
        }
        
        logger.info(f"⚡ Market emir oluşturuldu: {order_id}")
        logger.info(f"   Token: {token_symbol} ({token_address})")
        logger.info(f"   Ağ: {specific_chain}")
        logger.info(f"   Miktar: ${amount_usd:.2f}")
        logger.info(f"   Tip: {order_type.upper()}")
        
        # Market emri hemen çalıştır
        execution_result = self.execute_market_order(order)
        
        if execution_result["success"]:
            order["status"] = "executed"
            order["executed_at"] = datetime.now()
            order["execution_price"] = execution_result.get("price")
            order["execution_amount"] = execution_result.get("amount")
            logger.info(f"✅ Market emir başarıyla gerçekleşti: {order_id}")
        else:
            order["status"] = "failed"
            logger.error(f"❌ Market emir başarısız: {order_id}")
            logger.error(f"   Hata: {execution_result.get('error')}")
        
        self.order_history.append(order)
        
        # Yarışma kurallarına göre işlemi kaydet
        if execution_result["success"]:
            self.competition_manager.record_trade({
                "timestamp": datetime.now().isoformat(),
                "amount_usd": order["amount_usd"],
                "token_symbol": order["token_symbol"],
                "trade_type": f"market_{order['order_type']}",
                "order_id": order_id,
                "execution_price": execution_result.get("price"),
                "chain": order["specific_chain"]
            })
        
        return order
    
    def execute_market_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Market emri çalıştır"""
        
        try:
            # Güncel fiyat al
            price_data = get_price(
                order["token_address"],
                order["chain"],
                order["specific_chain"]
            )
            
            if not price_data.get("success"):
                return {
                    "success": False,
                    "error": f"Fiyat verisi alınamadı: {price_data.get('error')}"
                }
            
            current_price = float(price_data["price"])
            
            # Trade parametreleri
            if order["order_type"] == "buy":
                from_token = self.get_stablecoin_address(order["specific_chain"])
                to_token = order["token_address"]
                amount = str(order["amount_usd"])
            else:  # sell
                from_token = order["token_address"]
                to_token = self.get_stablecoin_address(order["specific_chain"])
                amount = str(order["amount_usd"])
            
            # Trade çalıştır
            trade_result = execute_trade(
                from_token=from_token,
                to_token=to_token,
                amount=amount,
                from_chain=order["chain"],
                to_chain=order["chain"],
                from_specific_chain=order["specific_chain"],
                to_specific_chain=order["specific_chain"],
                reason=f"Market {order['order_type']} - {order['token_symbol']}"
            )
            
            if trade_result.get("success"):
                # Fiyat takip sistemi kaldırıldı
                
                return {
                    "success": True,
                    "price": current_price,
                    "amount": order["amount_usd"],
                    "trade_result": trade_result
                }
            else:
                return {
                    "success": False,
                    "error": trade_result.get("error", "Bilinmeyen hata")
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Market emir hatası: {str(e)}"
            }
    
    def check_limit_orders(self) -> None:
        """Aktif limit emirleri kontrol et"""
        
        if not self.active_orders:
            return
        
        logger.info(f"🔍 {len(self.active_orders)} aktif limit emir kontrol ediliyor...")
        
        for order_id, order in list(self.active_orders.items()):
            try:
                # Güncel fiyat al
                price_data = get_price(
                    order["token_address"],
                    order["chain"],
                    order["specific_chain"]
                )
                
                if not price_data.get("success"):
                    logger.warning(f"⚠️ {order_id} için fiyat alınamadı")
                    continue
                
                current_price = float(price_data["price"])
                
                # Limit koşulu kontrol et
                should_execute = False
                
                if order["order_type"] == "buy":
                    should_execute = current_price <= order["limit_price"]
                else:  # sell
                    should_execute = current_price >= order["limit_price"]
                
                if should_execute:
                    logger.info(f"🎯 Limit emir koşulu sağlandı: {order_id}")
                    logger.info(f"   Güncel fiyat: ${current_price:.4f}")
                    logger.info(f"   Limit fiyat: ${order['limit_price']:.4f}")
                    
                    # Emri çalıştır
                    execution_result = self.execute_limit_order(order, current_price)
                    
                    if execution_result["success"]:
                        order["status"] = "executed"
                        order["executed_at"] = datetime.now()
                        order["execution_price"] = current_price
                        order["execution_amount"] = order["amount_usd"]
                        
                        logger.info(f"✅ Limit emir başarıyla gerçekleşti: {order_id}")
                        
                        # Yarışma kurallarına göre işlemi kaydet
                        self.competition_manager.record_trade({
                            "timestamp": datetime.now().isoformat(),
                            "amount_usd": order["amount_usd"],
                            "token_symbol": order["token_symbol"],
                            "trade_type": f"limit_{order['order_type']}",
                            "order_id": order_id,
                            "execution_price": current_price,
                            "chain": order["specific_chain"]
                        })
                        
                        # Aktif emirlerden kaldır
                        del self.active_orders[order_id]
                    else:
                        logger.error(f"❌ Limit emir başarısız: {order_id}")
                        logger.error(f"   Hata: {execution_result.get('error')}")
                else:
                    logger.debug(f"⏳ {order_id} bekliyor - Fiyat: ${current_price:.4f}, Limit: ${order['limit_price']:.4f}")
                    
            except Exception as e:
                logger.error(f"❌ {order_id} kontrol hatası: {e}")
    
    def execute_limit_order(self, order: Dict[str, Any], execution_price: float) -> Dict[str, Any]:
        """Limit emri çalıştır"""
        
        try:
            # Trade parametreleri
            if order["order_type"] == "buy":
                from_token = self.get_stablecoin_address(order["specific_chain"])
                to_token = order["token_address"]
                amount = str(order["amount_usd"])
            else:  # sell
                from_token = order["token_address"]
                to_token = self.get_stablecoin_address(order["specific_chain"])
                amount = str(order["amount_usd"])
            
            # Trade çalıştır
            trade_result = execute_trade(
                from_token=from_token,
                to_token=to_token,
                amount=amount,
                from_chain=order["chain"],
                to_chain=order["chain"],
                from_specific_chain=order["specific_chain"],
                to_specific_chain=order["specific_chain"],
                reason=f"Limit {order['order_type']} - {order['token_symbol']} @ ${execution_price:.4f}"
            )
            
            if trade_result.get("success"):
                # Fiyat takip sistemi kaldırıldı
                
                return {
                    "success": True,
                    "price": execution_price,
                    "amount": order["amount_usd"],
                    "trade_result": trade_result
                }
            else:
                return {
                    "success": False,
                    "error": trade_result.get("error", "Bilinmeyen hata")
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Limit emir hatası: {str(e)}"
            }
    
    def get_stablecoin_address(self, specific_chain: str) -> str:
        """Ağa göre stablecoin adresi döndür"""
        
        stablecoin_addresses = {
            "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
            "polygon": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",    # USDC
            "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # USDC
            "optimism": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",  # USDC
            "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",      # USDbC
            "bsc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",       # USDC
            "avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", # USDC
            "solana": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"   # USDC
        }
        
        return stablecoin_addresses.get(specific_chain.lower(), stablecoin_addresses["ethereum"])
    
    def cancel_order(self, order_id: str) -> bool:
        """Emri iptal et"""
        
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order["status"] = "cancelled"
            order["executed_at"] = datetime.now()
            
            del self.active_orders[order_id]
            
            logger.info(f"❌ Emir iptal edildi: {order_id}")
            return True
        else:
            logger.warning(f"⚠️ Emir bulunamadı: {order_id}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Emir durumu sorgula"""
        
        # Aktif emirlerde ara
        if order_id in self.active_orders:
            return self.active_orders[order_id]
        
        # Geçmişte ara
        for order in self.order_history:
            if order["id"] == order_id:
                return order
        
        return None
    
    def list_active_orders(self) -> List[Dict[str, Any]]:
        """Aktif emirleri listele"""
        return list(self.active_orders.values())
    
    def list_order_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Emir geçmişini listele"""
        return self.order_history[-limit:] if self.order_history else []
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Portföy özeti al"""
        try:
            portfolio = get_portfolio()
            if portfolio.get("success"):
                return portfolio
            else:
                logger.error(f"Portfolio alınamadı: {portfolio}")
                return {"success": False, "error": "Portfolio alınamadı"}
        except Exception as e:
            logger.error(f"Portfolio hatası: {e}")
            return {"success": False, "error": str(e)}
    
    def run_order_monitor(self, interval_minutes: int = 1) -> None:
        """Emir monitörü çalıştır"""
        
        logger.info(f"🔄 Emir monitörü başlatıldı (her {interval_minutes} dakikada)")
        
        while True:
            try:
                self.check_limit_orders()
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("🛑 Emir monitörü durduruldu")
                break
            except Exception as e:
                logger.error(f"❌ Monitör hatası: {e}")
                time.sleep(30)  # Hata durumunda 30 saniye bekle


class Perso1903Agent:
    """Ana agent sınıfı - Manuel emir sistemi"""
    
    def __init__(self):
        self.order_system = ManualOrderSystem()
        logger.info("🤖 Perso-1903 Agent başlatıldı")
        logger.info("📋 Manuel emir sistemi aktif")
    
    def create_buy_limit_order(self, token_address: str, token_symbol: str, 
                              chain: str, specific_chain: str, 
                              limit_price: float, amount_usd: float) -> Dict[str, Any]:
        """Alım limit emri oluştur"""
        return self.order_system.create_limit_order(
            token_address, token_symbol, chain, specific_chain, 
            limit_price, amount_usd, "buy"
        )
    
    def create_sell_limit_order(self, token_address: str, token_symbol: str,
                               chain: str, specific_chain: str,
                               limit_price: float, amount_usd: float) -> Dict[str, Any]:
        """Satım limit emri oluştur"""
        return self.order_system.create_limit_order(
            token_address, token_symbol, chain, specific_chain,
            limit_price, amount_usd, "sell"
        )
    
    def create_buy_market_order(self, token_address: str, token_symbol: str,
                               chain: str, specific_chain: str, 
                               amount_usd: float) -> Dict[str, Any]:
        """Alım market emri oluştur"""
        return self.order_system.create_market_order(
            token_address, token_symbol, chain, specific_chain,
            amount_usd, "buy"
        )
    
    def create_sell_market_order(self, token_address: str, token_symbol: str,
                                chain: str, specific_chain: str,
                                amount_usd: float) -> Dict[str, Any]:
        """Satım market emri oluştur"""
        return self.order_system.create_market_order(
            token_address, token_symbol, chain, specific_chain,
            amount_usd, "sell"
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """Emri iptal et"""
        return self.order_system.cancel_order(order_id)
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Emir durumu sorgula"""
        return self.order_system.get_order_status(order_id)
    
    def list_active_orders(self) -> List[Dict[str, Any]]:
        """Aktif emirleri listele"""
        return self.order_system.list_active_orders()
    
    def list_order_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Emir geçmişini listele"""
        return self.order_system.list_order_history(limit)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Portföy özeti al"""
        return self.order_system.get_portfolio_summary()
    
    def start_order_monitor(self, interval_minutes: int = 1) -> None:
        """Emir monitörü başlat"""
        self.order_system.run_order_monitor(interval_minutes)
    
    # Fiyat takip sistemi kaldırıldı
    
    def check_daily_trading_requirement(self) -> Dict[str, Any]:
        """Günlük işlem gereksinimini kontrol et"""
        return self.order_system.competition_manager.check_daily_requirement()
    
    def get_competition_status(self) -> Dict[str, Any]:
        """Yarışma durumunu kontrol et"""
        return self.order_system.competition_manager.get_competition_status()
    
    def generate_daily_report(self) -> str:
        """Günlük rapor oluştur"""
        return self.order_system.competition_manager.generate_daily_report()
    
    def sync_with_api(self) -> None:
        """API ile senkronize et"""
        self.order_system.competition_manager.sync_daily_trades_with_api()


if __name__ == "__main__":
    print("🚀 Perso-1903 Manuel Emir Sistemi")
    print("=" * 50)
    
    # Agent oluştur
    agent = Perso1903Agent()
    
    # Portföy özeti
    print("\n📊 Portföy Özeti:")
    portfolio = agent.get_portfolio_summary()
    if portfolio.get("success"):
        print(f"Toplam Değer: ${portfolio.get('totalValue', 0):.2f}")
        print(f"Token Sayısı: {len(portfolio.get('tokens', []))}")
    else:
        print(f"❌ Portfolio alınamadı: {portfolio.get('error')}")
    
    # Yarışma durumu
    print("\n🏆 Yarışma Durumu:")
    competition_status = agent.get_competition_status()
    if competition_status.get("success"):
        print(f"Aktif: {'✅ Evet' if competition_status.get('active') else '❌ Hayır'}")
        if competition_status.get("active"):
            print(f"Kalan Günler: {competition_status.get('days_remaining', 0)}")
    else:
        print(f"❌ Yarışma durumu alınamadı: {competition_status.get('error')}")
    
    # Günlük işlem kontrolü
    print("\n📊 Günlük İşlem Kontrolü:")
    daily_check = agent.check_daily_trading_requirement()
    print(f"Gün: {daily_check['day']}")
    print(f"Mevcut İşlemler: {daily_check['current_trades']}")
    print(f"Minimum Gereksinim: {daily_check['min_required']}")
    print(f"Durum: {daily_check['status']}")
    
    # Sistem durumu
    print("\n🖥️ Sistem Durumu:")
    system_status = agent.get_system_status()
    print(f"Başlatma Zamanı: {system_status['start_time']}")
    print(f"Çalışma Süresi: {system_status['uptime']}")
    print(f"Aktif Emirler: {system_status['active_orders']}")
    print(f"Toplam Emirler: {system_status['total_orders']}")
    print(f"API Durumu: {'✅ Sağlıklı' if system_status['api_health'] else '❌ Sorunlu'}")
    
    # Aktif emirler
    print("\n📋 Aktif Emirler:")
    active_orders = agent.list_active_orders()
    if active_orders:
        for order in active_orders:
            print(f"  {order['id']}: {order['token_symbol']} - ${order['limit_price']:.4f}")
    else:
        print("  Aktif emir yok")
    
    # Günlük rapor
    print("\n📋 Günlük Rapor:")
    daily_report = agent.generate_daily_report()
    print(daily_report)
    
    print("\n✅ Manuel emir sistemi hazır!")
    print("📝 Kullanım örnekleri:")
    print("  agent.create_buy_limit_order('token_address', 'SYMBOL', 'chain', 'specific_chain', limit_price, amount)")
    print("  agent.create_buy_market_order('token_address', 'SYMBOL', 'chain', 'specific_chain', amount)")
    print("  agent.start_order_monitor()  # Limit emirleri izlemek için")
    print("  agent.check_daily_trading_requirement()  # Günlük işlem kontrolü")
    print("  agent.sync_with_api()  # API ile senkronize et")
