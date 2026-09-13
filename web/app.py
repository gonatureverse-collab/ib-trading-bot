"""
Interactive Brokers Trading Bot - Web Dashboard
Flask application for real-time bot monitoring
"""

from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import os
import sqlite3
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trades.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ib-trading-bot-secret-key'

# Initialize Database
db = SQLAlchemy(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Trade(db.Model):
    """Trade history model"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    side = db.Column(db.String(10), nullable=False)  # BUY or SHORT
    profit_loss = db.Column(db.Float, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False)
    exit_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(20))  # SL, TP, Manual
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'entry_price': round(self.entry_price, 2),
            'exit_price': round(self.exit_price, 2),
            'quantity': self.quantity,
            'side': self.side,
            'profit_loss': round(self.profit_loss, 2),
            'entry_time': self.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': self.exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'reason': self.reason
        }

class BotStatus(db.Model):
    """Bot status model"""
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='stopped')  # running, stopped, error
    start_time = db.Column(db.DateTime)
    last_update = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.String(500))
    current_capital = db.Column(db.Float, default=10000.0)
    daily_pnl = db.Column(db.Float, default=0.0)
    trades_today = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'status': self.status,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'last_update': self.last_update.strftime('%Y-%m-%d %H:%M:%S'),
            'error_message': self.error_message,
            'current_capital': round(self.current_capital, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'trades_today': self.trades_today
        }

# ============================================================================
# ROUTES - WEB PAGES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/trades')
def trades_page():
    """Trade history page"""
    return render_template('trades.html')

@app.route('/settings')
def settings_page():
    """Bot settings page"""
    return render_template('settings.html')

# ============================================================================
# API ENDPOINTS - REAL-TIME DATA
# ============================================================================

@app.route('/api/bot-status')
def api_bot_status():
    """Get current bot status"""
    bot_status = BotStatus.query.first() or BotStatus()
    return jsonify(bot_status.to_dict())

@app.route('/api/today-trades')
def api_today_trades():
    """Get today's trades"""
    today = datetime.now().date()
    trades = Trade.query.filter(
        db.func.date(Trade.exit_time) == today
    ).all()
    
    trade_list = [t.to_dict() for t in trades]
    
    if trades:
        wins = len([t for t in trades if t.profit_loss > 0])
        total_pnl = sum(t.profit_loss for t in trades)
        
        return jsonify({
            'trades': trade_list,
            'total_trades': len(trades),
            'winning_trades': wins,
            'losing_trades': len(trades) - wins,
            'win_rate': round(wins / len(trades) * 100, 2),
            'total_pnl': round(total_pnl, 2),
            'best_trade': round(max([t.profit_loss for t in trades]), 2),
            'worst_trade': round(min([t.profit_loss for t in trades]), 2),
            'avg_trade': round(total_pnl / len(trades), 2)
        })
    else:
        return jsonify({
            'trades': [],
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_trade': 0
        })

@app.route('/api/weekly-stats')
def api_weekly_stats():
    """Get weekly statistics"""
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    trades = Trade.query.filter(Trade.exit_time >= week_ago).all()
    
    if trades:
        wins = len([t for t in trades if t.profit_loss > 0])
        total_pnl = sum(t.profit_loss for t in trades)
        
        return jsonify({
            'total_trades': len(trades),
            'winning_trades': wins,
            'losing_trades': len(trades) - wins,
            'win_rate': round(wins / len(trades) * 100, 2),
            'total_pnl': round(total_pnl, 2),
            'daily_avg': round(total_pnl / 7, 2),
            'best_trade': round(max([t.profit_loss for t in trades]), 2),
            'worst_trade': round(min([t.profit_loss for t in trades]), 2)
        })
    else:
        return jsonify({
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'daily_avg': 0,
            'best_trade': 0,
            'worst_trade': 0
        })

@app.route('/api/all-trades')
def api_all_trades():
    """Get all trades with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = Trade.query.order_by(Trade.exit_time.desc()).paginate(
        page=page, per_page=per_page
    )
    
    return jsonify({
        'trades': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@app.route('/api/bot-control', methods=['POST'])
def api_bot_control():
    """Control bot (start/stop)"""
    action = request.json.get('action')
    
    bot_status = BotStatus.query.first() or BotStatus()
    
    if action == 'start':
        bot_status.status = 'running'
        bot_status.start_time = datetime.utcnow()
        bot_status.trades_today = 0
        bot_status.daily_pnl = 0
    elif action == 'stop':
        bot_status.status = 'stopped'
    
    bot_status.last_update = datetime.utcnow()
    db.session.add(bot_status)
    db.session.commit()
    
    return jsonify({'status': 'success', 'bot_status': bot_status.to_dict()})

@app.route('/api/add-trade', methods=['POST'])
def api_add_trade():
    """Add new trade (from bot)"""
    data = request.json
    
    trade = Trade(
        symbol=data['symbol'],
        entry_price=data['entry_price'],
        exit_price=data['exit_price'],
        quantity=data['quantity'],
        side=data['side'],
        profit_loss=data['profit_loss'],
        entry_time=datetime.fromisoformat(data['entry_time']),
        exit_time=datetime.fromisoformat(data['exit_time']),
        reason=data.get('reason', 'TP')
    )
    
    db.session.add(trade)
    
    # Update bot status
    bot_status = BotStatus.query.first() or BotStatus()
    bot_status.daily_pnl += data['profit_loss']
    bot_status.trades_today += 1
    bot_status.last_update = datetime.utcnow()
    db.session.add(bot_status)
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'trade_id': trade.id})

@app.route('/api/chart-data')
def api_chart_data():
    """Get chart data (7 days)"""
    today = datetime.now().date()
    days_back = 7
    
    chart_data = {}
    
    for i in range(days_back, 0, -1):
        date = (datetime.now() - timedelta(days=i)).date()
        trades = Trade.query.filter(
            db.func.date(Trade.exit_time) == date
        ).all()
        
        if trades:
            daily_pnl = sum(t.profit_loss for t in trades)
            chart_data[str(date)] = round(daily_pnl, 2)
        else:
            chart_data[str(date)] = 0
    
    return jsonify(chart_data)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(debug=True, host='0.0.0.0', port=5000)