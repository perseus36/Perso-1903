#!/usr/bin/env python3
"""
Perso-1903 Modern Dashboard
Manuel Emir Sistemi için Dashboard
"""

from flask import Flask, render_template, jsonify, request
from perso_1903_agent import Perso1903Agent
from perso_1903_client import get_portfolio, get_price, get_trade_history, get_agent_transactions
import json
import logging
from datetime import datetime
import os

# Flask app oluştur
app = Flask(__name__)
app.secret_key = 'perso-1903-dashboard-secret'

# Logging ayarla
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent = None

def get_agent():
    """Agent instance'ını al veya oluştur"""
    global agent
    if agent is None:
        agent = Perso1903Agent()
    return agent

@app.route('/')
def dashboard():
    """Ana dashboard sayfası"""
    return render_template('dashboard.html')

@app.route('/api/portfolio')
def api_portfolio():
    """Portföy verilerini API olarak döndür"""
    try:
        portfolio = get_portfolio()
        if portfolio.get('success'):
            return jsonify({
                'success': True,
                'data': portfolio
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Portfolio fetch failed'
            })
    except Exception as e:
        logger.error(f"Portfolio API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/balances')
def api_balances():
    """Bakiye verilerini API olarak döndür - RECALL API ONLY"""
    try:
        portfolio = get_portfolio()
        if portfolio.get('success'):
            balances = {}
            total_value = portfolio.get('totalValue', 0)
            
            # Chain bazında bakiyeleri hesapla
            for token in portfolio.get('tokens', []):
                chain = token.get('specificChain', 'unknown')
                if chain not in balances:
                    balances[chain] = {
                        'usdc_balance': 0,
                        'tokens': [],
                        'total_value': 0
                    }
                
                # USDC/USDbC bakiyelerini ayır
                if token.get('symbol') in ['USDC', 'USDbC']:
                    balances[chain]['usdc_balance'] += token.get('value', 0)
                else:
                    balances[chain]['tokens'].append({
                        'symbol': token.get('symbol'),
                        'amount': token.get('amount', 0),
                        'price': token.get('price', 0),
                        'value': token.get('value', 0),
                        'address': token.get('tokenAddress')
                    })
                
                balances[chain]['total_value'] += token.get('value', 0)
            
            return jsonify({
                'success': True,
                'data': {
                    'balances': balances,
                    'total_value': total_value
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Balances fetch failed'
            })
    except Exception as e:
        logger.error(f"Balances API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/trade-history')
def api_trade_history():
    """Trade geçmişini API olarak döndür - RECALL API ONLY"""
    try:
        # Recall API'den trade history çek
        recall_trades = get_trade_history(limit=100)
        
        if recall_trades.get('success'):
            trades = recall_trades.get('trades', [])
            
            # Recall API formatını dashboard formatına çevir
            dashboard_trades = []
            for trade in trades:
                dashboard_trade = {
                    'type': 'buy' if trade.get('fromTokenSymbol') == 'USDC' else 'sell',
                    'timestamp': trade.get('timestamp', ''),
                    'token_address': trade.get('toToken', '') if trade.get('fromTokenSymbol') == 'USDC' else trade.get('fromToken', ''),
                    'token_symbol': trade.get('toTokenSymbol', '') if trade.get('fromTokenSymbol') == 'USDC' else trade.get('fromTokenSymbol', ''),
                    'chain': trade.get('toChain', '') if trade.get('fromTokenSymbol') == 'USDC' else trade.get('fromChain', ''),
                    'specific_chain': trade.get('toSpecificChain', '') if trade.get('fromTokenSymbol') == 'USDC' else trade.get('fromSpecificChain', ''),
                    'amount': trade.get('toAmount', 0) if trade.get('fromTokenSymbol') == 'USDC' else trade.get('fromAmount', 0),
                    'price_usd': trade.get('tradeAmountUsd', 0) / (trade.get('toAmount', 1) if trade.get('fromTokenSymbol') == 'USDC' else trade.get('fromAmount', 1)) if (trade.get('toAmount', 0) > 0 if trade.get('fromTokenSymbol') == 'USDC' else trade.get('fromAmount', 0) > 0) else 0,
                    'total_usd': trade.get('tradeAmountUsd', 0),
                    'reason': trade.get('reason', '')
                }
                dashboard_trades.append(dashboard_trade)
            
            # Tarihe göre sırala
            dashboard_trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Buy/sell sayılarını hesapla
            buy_count = len([t for t in dashboard_trades if t.get('type') == 'buy'])
            sell_count = len([t for t in dashboard_trades if t.get('type') == 'sell'])
            
            return jsonify({
                'success': True,
                'data': {
                    'trades': dashboard_trades[:50],  # Son 50 işlem
                    'buy_count': buy_count,
                    'sell_count': sell_count,
                    'new_system_trades': len(dashboard_trades),
                    'old_system_trades': 0
                }
            })
        
        # Recall API başarısız olursa hata döndür
        return jsonify({
            'success': False,
            'error': 'Recall API trade history fetch failed'
        })
    except Exception as e:
        logger.error(f"Trade history API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/positions')
def api_positions():
    """Aktif pozisyonları API olarak döndür - RECALL API ONLY"""
    try:
        portfolio = get_portfolio()
        if not portfolio.get('success'):
            return jsonify({
                'success': False,
                'error': 'Portfolio fetch failed'
            })
        
        positions = {}
        tokens = portfolio.get('tokens', [])
        
        # Her token için pozisyon oluştur (sadece değeri olanlar)
        for token in tokens:
            if token.get('value', 0) > 0 and token.get('symbol') not in ['USDC', 'USDbC', 'USDT', 'USDT0']:
                key = f"{token['symbol']}_{token['specificChain']}"
                
                positions[key] = {
                    'token_address': token.get('tokenAddress', ''),
                    'token_symbol': token.get('symbol', ''),
                    'chain': token.get('chain', ''),
                    'specific_chain': token.get('specificChain', ''),
                    'total_amount': token.get('amount', 0),
                    'total_invested': token.get('value', 0),  # Use actual value from API
                    'average_buy_price': token.get('price', 0),
                    'current_price': token.get('price', 0),
                    'current_value': token.get('value', 0),
                    'profit_loss': 0,  # Will be calculated based on actual trading
                    'profit_loss_pct': 0,
                    'first_buy_date': '',
                    'last_buy_date': ''
                }
        
        return jsonify({
            'success': True,
            'data': {
                'positions': positions,
                'total_positions': len(positions),
                'total_buys': len(positions),
                'total_sells': 0
            }
        })
    except Exception as e:
        logger.error(f"Positions API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/pnl')
def api_pnl():
    """PNL verilerini API olarak döndür - RECALL API ONLY"""
    try:
        portfolio = get_portfolio()
        if not portfolio.get('success'):
            return jsonify({
                'success': False,
                'error': 'Portfolio fetch failed'
            })
        
        total_current_value = portfolio.get('totalValue', 0)
        
        # Yarışma başlangıç bakiyesi: 6 ağ x 5000 USDC = 30000 USDC
        total_invested = 30000.0
        
        total_profit_loss = total_current_value - total_invested
        total_profit_loss_pct = (total_profit_loss / total_invested) * 100 if total_invested > 0 else 0
        
        # Pozisyon sayısını hesapla (değeri olan tokenlar)
        tokens = portfolio.get('tokens', [])
        positions_count = len([t for t in tokens if t.get('value', 0) > 0 and t.get('symbol') not in ['USDC', 'USDbC', 'USDT', 'USDT0']])
        
        return jsonify({
            'success': True,
            'data': {
                'total_invested': total_invested,
                'total_current_value': total_current_value,
                'total_profit_loss': total_profit_loss,
                'total_profit_loss_pct': total_profit_loss_pct,
                'positions_count': positions_count
            }
        })
    except Exception as e:
        logger.error(f"PNL API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/performance-report')
def api_performance_report():
    """Performans raporunu API olarak döndür"""
    try:
        agent = get_agent()
        report = agent.generate_performance_report()
        
        return jsonify({
            'success': True,
            'data': {
                'report': report
            }
        })
    except Exception as e:
        logger.error(f"Performance report API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    print("🚀 Perso-1903 Modern Dashboard Başlatılıyor...")
    print("📊 Manuel Emir Sistemi Dashboard")
    print("🌐 http://localhost:5000 adresinde erişilebilir")
    
    # Templates klasörünü oluştur
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
