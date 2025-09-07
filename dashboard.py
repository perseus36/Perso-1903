#!/usr/bin/env python3
"""
Perso-1903 Trading Agent Dashboard
Real-time monitoring interface for trading positions and performance
"""

import json
import time
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import threading
import queue

# Import risk management for live data
try:
    from risk_management import RiskManager
    # Create a fresh instance for dashboard
    RISK_MANAGER = RiskManager()
    RISK_MANAGER.load_positions()
except ImportError:
    RISK_MANAGER = None

app = Flask(__name__)

# Global data cache
dashboard_data = {
    'positions': {},
    'trades': [],
    'scalping': {},
    'double_down': {},
    'performance': {},
    'last_update': None
}

def load_trade_history():
    """Load trade history from JSON logs"""
    trades = []
    log_file = Path("logs/agent.jsonl")
    
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            trade = json.loads(line.strip())
                            if trade.get('event') in ['trade_intent', 'trade_post']:
                                trades.append(trade)
                        except json.JSONDecodeError:
                            continue  # Skip invalid JSON lines
        except Exception as e:
            print(f"Error loading trade history: {e}")
    
    return trades[-100:]  # Last 100 trades

def load_risk_state():
    """Load current risk state"""
    risk_file = Path("risk_state.json")
    if risk_file.exists():
        try:
            with open(risk_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading risk state: {e}")
    return {}

def calculate_performance(trades):
    """Calculate performance metrics"""
    total_trades = len(trades)
    successful_trades = sum(1 for t in trades if t.get('success', False))
    
    # Calculate P&L from trade data
    total_pnl = 0
    for trade in trades:
        if trade.get('success') and 'pnl' in trade:
            total_pnl += trade.get('pnl', 0)
    
    return {
        'total_trades': total_trades,
        'successful_trades': successful_trades,
        'success_rate': (successful_trades / total_trades * 100) if total_trades > 0 else 0,
        'total_pnl': total_pnl,
        'avg_trade_size': sum(t.get('amount', 0) for t in trades) / total_trades if total_trades > 0 else 0
    }

def update_dashboard_data():
    """Update dashboard data from various sources"""
    global dashboard_data
    
    try:
        # Load trade history
        trades = load_trade_history()
        
        # Load risk state
        risk_state = load_risk_state()
        
        # Get positions from RiskManager if available
        positions = {}
        scalping = {}
        double_down = {}
        
        if RISK_MANAGER:
            positions = RISK_MANAGER.get_active_positions()
            scalping = RISK_MANAGER.scalping_positions
            double_down = RISK_MANAGER.double_down_positions
        
        # Calculate performance
        performance = calculate_performance(trades)
        
        # Update global data
        dashboard_data.update({
            'positions': positions,
            'trades': trades,
            'scalping': scalping,
            'double_down': double_down,
            'performance': performance,
            'risk_state': risk_state,
            'last_update': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error updating dashboard data: {e}")

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/data')
def api_data():
    """API endpoint for dashboard data"""
    update_dashboard_data()
    return jsonify(dashboard_data)

@app.route('/api/positions')
def api_positions():
    """API endpoint for positions only"""
    update_dashboard_data()
    return jsonify({
        'positions': dashboard_data['positions'],
        'scalping': dashboard_data['scalping'],
        'double_down': dashboard_data['double_down']
    })

@app.route('/api/trades')
def api_trades():
    """API endpoint for trades only"""
    update_dashboard_data()
    return jsonify({
        'trades': dashboard_data['trades'],
        'performance': dashboard_data['performance']
    })

@app.route('/api/status')
def api_status():
    """API endpoint for system status"""
    return jsonify({
        'status': 'running',
        'last_update': dashboard_data.get('last_update'),
        'risk_manager_available': RISK_MANAGER is not None,
        'log_file_exists': Path("logs/agent.jsonl").exists(),
        'risk_file_exists': Path("risk_state.json").exists()
    })

def run_dashboard():
    """Run the dashboard server"""
    print("🚀 Starting Perso-1903 Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8080")
    print("📈 Real-time monitoring enabled")
    
    # Update data initially
    update_dashboard_data()
    
    # Run Flask app
    app.run(host='127.0.0.1', port=8080, debug=False, threaded=True)

if __name__ == '__main__':
    run_dashboard()
