"""
Interactive Brokers Delayed Data 15-Minute Trading Bot
TEST 1 OPTIMIZED PARAMETERS
SMA(8/20) + RSI(50/50) Strategy
FREE - Delayed Market Data (15-20 min delay)
Paper Trading Mode
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import numpy as np
import threading
import time
from collections import deque
from datetime import datetime

class IBDelayedDataBot(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        
        # TEST 1 OPTIMAL PARAMETERS
        self.SMA_SHORT = 8
        self.SMA_LONG = 20
        self.RSI_PERIOD = 14
        self.RSI_THRESHOLD = 50
        
        # Risk Management
        self.STOP_LOSS_PERCENT = 0.01      # 1%
        self.TAKE_PROFIT_PERCENT = 0.03    # 3%
        self.MAX_POSITION_SIZE = 0.02      # 2%
        self.MAX_POSITIONS = 3
        self.DAILY_LOSS_LIMIT = 0.05       # 5%
        
        # Symbols
        self.symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        # State
        self.initial_capital = 10000.0
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.price_history = {s: deque(maxlen=100) for s in self.symbols}
        self.daily_pnl = 0.0
        self.trade_count = 0
        self.next_order_id = None
        self.contract_ids = {
            'AAPL': 265598,
            'GOOGL': 360468,
            'MSFT': 272093
        }
        self.session_start_time = datetime.now()
        
        print("\n" + "="*80)
        print("INTERACTIVE BROKERS - 15-MINUTE DELAYED DATA BOT")
        print("TEST 1 OPTIMIZED PARAMETERS - FREE VERSION")
        print("="*80)
        print("\nCONNECTING TO IB GATEWAY...")
    
    def nextValidId(self, orderId):
        """Connection established"""
        self.next_order_id = orderId
        print(f"✓ Connected to IB Gateway (Delayed Data Mode)")
        print(f"✓ Next Order ID: {orderId}")
        print(f"✓ Session Start: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.start_subscriptions()
    
    def start_subscriptions(self):
        """Subscribe to delayed 15-minute bars"""
        print("\n" + "="*80)
        print("STRATEGY CONFIGURATION")
        print("="*80)
        print("\nSTRATEGY (TEST 1 - APPROVED):")
        print(f"  SMA Short/Long:      {self.SMA_SHORT}/{self.SMA_LONG}")
        print(f"  RSI Period:          {self.RSI_PERIOD}")
        print(f"  RSI Threshold:       {self.RSI_THRESHOLD} (both sides)")
        
        print("\nRISK MANAGEMENT:")
        print(f"  Stop Loss:           {self.STOP_LOSS_PERCENT*100:.1f}%")
        print(f"  Take Profit:         {self.TAKE_PROFIT_PERCENT*100:.1f}%")
        print(f"  Position Size:       {self.MAX_POSITION_SIZE*100:.1f}%")
        print(f"  Max Concurrent:      {self.MAX_POSITIONS}")
        print(f"  Daily Loss Limit:    {self.DAILY_LOSS_LIMIT*100:.1f}%")
        
        print("\nMARKET DATA:")
        print(f"  Type:                DELAYED (15-20 min) - FREE ✓")
        print(f"  Subscription:        NOT REQUIRED")
        
        print("\nTARGETS:")
        print(f"  Daily Trades:        20+ trades (target)")
        print(f"  Win Rate:            >55%")
        print(f"  Daily Return:        +0.5-1.0%")
        
        print("\nTRADING SYMBOLS:")
        for symbol in self.symbols:
            print(f"  - {symbol}")
        
        print("="*80)
        print("\nSubscribing to 15-minute DELAYED bars...\n")
        
        for symbol in self.symbols:
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            # Request delayed/frozen 15-minute bars
            self.reqRealTimeBars(
                self.contract_ids[symbol],
                contract,
                15,  # 15-minute bars
                "TRADES",
                False,  # FALSE = use delayed data (frozen)
                []
            )
            print(f"  ✓ {symbol} - subscribed (15-min DELAYED bars)")
        
        print("\n" + "="*80)
        print("LIVE TRADING STARTED - WAITING FOR 15-MIN DELAYED BARS")
        print("Note: Data is delayed 15-20 minutes (FREE)")
        print("="*80 + "\n")
    
    def realtimeBar(self, reqId, time, open_, high, low, close, volume, wap, count):
        """Process delayed 15-minute bar"""
        
        symbol_map = {v: k for k, v in self.contract_ids.items()}
        symbol = symbol_map.get(reqId)
        
        if not symbol:
            return
        
        timestamp = datetime.fromtimestamp(time).strftime("%Y-%m-%d %H:%M:%S")
        price = close
        
        # Add to history
        self.price_history[symbol].append(price)
        
        # Check daily loss limit
        if self.daily_pnl < -self.initial_capital * self.DAILY_LOSS_LIMIT:
            print(f"[{timestamp}] ⚠️  DAILY LOSS LIMIT REACHED - STOPPING")
            self.disconnect()
            return
        
        # Process exits
        if symbol in self.positions:
            pos = self.positions[symbol]
            entry_price = pos['entry_price']
            qty = pos['qty']
            side = pos['side']
            
            # Stop Loss
            if side == "BUY" and price <= entry_price * (1 - self.STOP_LOSS_PERCENT):
                profit_loss = (price - entry_price) * qty
                print(f"[{timestamp}] 🔴 STOP LOSS {symbol} | BUY @ ${entry_price:.2f} → SELL @ ${price:.2f} | P&L: ${profit_loss:.2f}")
                self.cash += price * qty
                self.daily_pnl += profit_loss
                self.trades.append({'symbol': symbol, 'profit_loss': profit_loss, 'reason': 'SL'})
                del self.positions[symbol]
                self.trade_count += 1
                return
            
            elif side == "SHORT" and price >= entry_price * (1 + self.STOP_LOSS_PERCENT):
                profit_loss = (entry_price - price) * qty
                print(f"[{timestamp}] 🔴 STOP LOSS {symbol} | SHORT @ ${entry_price:.2f} → COVER @ ${price:.2f} | P&L: ${profit_loss:.2f}")
                self.cash += price * qty
                self.daily_pnl += profit_loss
                self.trades.append({'symbol': symbol, 'profit_loss': profit_loss, 'reason': 'SL'})
                del self.positions[symbol]
                self.trade_count += 1
                return
            
            # Take Profit
            if side == "BUY" and price >= entry_price * (1 + self.TAKE_PROFIT_PERCENT):
                profit_loss = (price - entry_price) * qty
                print(f"[{timestamp}] 🟢 TAKE PROFIT {symbol} | BUY @ ${entry_price:.2f} → SELL @ ${price:.2f} | P&L: ${profit_loss:.2f}")
                self.cash += price * qty
                self.daily_pnl += profit_loss
                self.trades.append({'symbol': symbol, 'profit_loss': profit_loss, 'reason': 'TP'})
                del self.positions[symbol]
                self.trade_count += 1
                return
            
            elif side == "SHORT" and price <= entry_price * (1 - self.TAKE_PROFIT_PERCENT):
                profit_loss = (entry_price - price) * qty
                print(f"[{timestamp}] 🟢 TAKE PROFIT {symbol} | SHORT @ ${entry_price:.2f} → COVER @ ${price:.2f} | P&L: ${profit_loss:.2f}")
                self.cash += price * qty
                self.daily_pnl += profit_loss
                self.trades.append({'symbol': symbol, 'profit_loss': profit_loss, 'reason': 'TP'})
                del self.positions[symbol]
                self.trade_count += 1
                return
        
        # Get signal
        signal = self.get_signal(symbol)
        
        # Entry Logic
        if len(self.positions) < self.MAX_POSITIONS:
            if signal == "BUY" and symbol not in self.positions:
                position_value = self.MAX_POSITION_SIZE * self.initial_capital
                qty = int(position_value / price)
                
                if qty > 0 and qty * price <= self.cash:
                    self.positions[symbol] = {
                        'entry_price': price,
                        'qty': qty,
                        'side': 'BUY',
                        'entry_time': timestamp
                    }
                    self.cash -= qty * price
                    print(f"[{timestamp}] 🟦 BUY {symbol} | Price: ${price:.2f} | Qty: {qty}")
            
            elif signal == "SELL" and symbol not in self.positions:
                position_value = self.MAX_POSITION_SIZE * self.initial_capital
                qty = int(position_value / price)
                
                if qty > 0:
                    self.positions[symbol] = {
                        'entry_price': price,
                        'qty': qty,
                        'side': 'SHORT',
                        'entry_time': timestamp
                    }
                    self.cash -= qty * price
                    print(f"[{timestamp}] 🟥 SHORT {symbol} | Price: ${price:.2f} | Qty: {qty}")
    
    def get_signal(self, symbol):
        """Get trading signal"""
        prices = self.price_history[symbol]
        
        if len(prices) < self.SMA_LONG:
            return "HOLD"
        
        sma_short = float(np.mean(list(prices)[-self.SMA_SHORT:]))
        sma_long = float(np.mean(list(prices)[-self.SMA_LONG:]))
        rsi = self.calculate_rsi(prices)
        
        if rsi is None:
            return "HOLD"
        
        # BUY: SMA(8) > SMA(20) AND RSI < 50
        if sma_short > sma_long and rsi < self.RSI_THRESHOLD:
            return "BUY"
        # SELL: SMA(8) < SMA(20) AND RSI > 50
        elif sma_short < sma_long and rsi > self.RSI_THRESHOLD:
            return "SELL"
        
        return "HOLD"
    
    def calculate_rsi(self, prices):
        """Calculate RSI"""
        if len(prices) < self.RSI_PERIOD + 1:
            return None
        
        prices_list = list(prices)
        deltas = np.diff(prices_list[-self.RSI_PERIOD-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
    
    def error(self, reqId, errorCode, errorString):
        """Error handling"""
        # Filter out info messages
        if errorCode in [2104, 2106, 2158]:
            pass
        elif errorCode == 420:
            # Expected for delayed data - ignore
            pass
        else:
            print(f"Error {errorCode}: {errorString}")
    
    def print_summary(self):
        """Print session summary"""
        print("\n" + "="*80)
        print("DELAYED DATA BOT - SESSION SUMMARY")
        print("="*80)
        
        session_duration = (datetime.now() - self.session_start_time).total_seconds() / 3600
        
        print(f"\nSESSION INFO:")
        print(f"  Duration:            {session_duration:.1f} hours")
        print(f"  Data Mode:           DELAYED (15-20 min) - FREE ✓")
        print(f"  Trades Executed:     {len(self.trades)}")
        
        if session_duration > 0:
            print(f"  Avg Trades/Hour:     {len(self.trades)/session_duration:.1f}")
        
        if self.trades:
            wins = len([t for t in self.trades if t['profit_loss'] > 0])
            losses = len([t for t in self.trades if t['profit_loss'] < 0])
            total_pnl = sum(t['profit_loss'] for t in self.trades)
            
            print(f"\nTRADE STATISTICS:")
            print(f"  Winning Trades:      {wins}")
            print(f"  Losing Trades:       {losses}")
            print(f"  Win Rate:            {wins/len(self.trades)*100:.1f}%")
            print(f"  Total P&L:           ${total_pnl:.2f}")
            print(f"  Avg Trade:           ${total_pnl/len(self.trades):.2f}")
            
            best = max([t['profit_loss'] for t in self.trades])
            worst = min([t['profit_loss'] for t in self.trades])
            print(f"  Best Trade:          ${best:.2f}")
            print(f"  Worst Trade:         ${worst:.2f}")
            
            portfolio = self.initial_capital + total_pnl
            daily_return = (total_pnl / self.initial_capital) * 100
            
            print(f"\nPORTFOLIO:")
            print(f"  Initial Capital:     ${self.initial_capital:.2f}")
            print(f"  Final Balance:       ${portfolio:.2f}")
            print(f"  Daily Return:        {daily_return:.2f}%")
            
            print(f"\nDECISION:")
            if len(self.trades) >= 10 and wins/len(self.trades) > 0.55:
                print(f"  ✓ EXCELLENT - Consider upgrading to real-time data")
            elif len(self.trades) >= 10 and wins/len(self.trades) > 0.5:
                print(f"  ✓ GOOD - Strategy working with delayed data")
            else:
                print(f"  ⚠ Monitoring - Continue testing")
        else:
            print(f"\n  No trades yet - waiting for market signals...")
        
        print("="*80 + "\n")
    
    def disconnect_gracefully(self):
        """Disconnect gracefully"""
        print("\n\nDisconnecting from IB Gateway...")
        self.print_summary()
        EClient.disconnect(self)


# MAIN EXECUTION
if __name__ == "__main__":
    app = IBDelayedDataBot()
    
    # TWS Paper Trading: port 7497
    # IB Gateway Paper Trading: port 4002
    app.connect("127.0.0.1", 7497, clientId=1)
    
    print("\n✓ Connecting to TWS (127.0.0.1:7497)...")
    print("  Using DELAYED market data (15-20 min delay) - FREE")
    print("  No subscription required!\n")
    
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    time.sleep(2)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down bot...")
        app.disconnect_gracefully()
