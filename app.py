from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objs as go
import plotly
import json
import ta
import sqlite3
from flask_caching import Cache

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Setup database
def init_db():
    conn = sqlite3.connect('bitcoin.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS recommendations
                 (date text, type text, price real, action text, confidence text)''')
    conn.commit()
    conn.close()

init_db()

@cache.cached(timeout=3600)
def get_bitcoin_data(period='1y'):
    btc = yf.Ticker("BTC-USD")
    hist = btc.history(period=period)
    df = pd.DataFrame(hist)
    df = df[['Close', 'Volume']].rename(columns={'Close': 'price'})
    df = df.resample('D').mean().ffill()
    
    # Calculate indicators
    df['sma_20'] = ta.trend.sma_indicator(df['price'], window=20)
    df['sma_50'] = ta.trend.sma_indicator(df['price'], window=50)
    df['rsi'] = ta.momentum.rsi(df['price'], window=14)
    df['golden_cross'] = (df['sma_20'] > df['sma_50']) & (df['sma_20'].shift(1) <= df['sma_50'].shift(1))
    df['death_cross'] = (df['sma_20'] < df['sma_50']) & (df['sma_20'].shift(1) >= df['sma_50'].shift(1))
    
    return df

def analyze_bitcoin(df):
    recommendations = []
    current_price = df['price'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    
    # Golden Cross Recommendation
    if df['golden_cross'].iloc[-1]:
        recommendations.append({
            'type': 'Golden Cross Confirmed',
            'action': 'Allocate 50% of capital',
            'confidence': 'High',
            'price': current_price,
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'details': 'SMA 20 crossed above SMA 50 indicating bullish trend'
        })
    
    # Buy the Dip (RSI based)
    if rsi < 30:
        dip_percentage = ((df['price'].iloc[-3] - current_price) / df['price'].iloc[-3]) * 100
        recommendations.append({
            'type': f'Buy the Dip (RSI {rsi:.1f})',
            'action': f'Allocate 30% capital (Dip {dip_percentage:.1f}%)',
            'confidence': 'High' if dip_percentage > 10 else 'Medium',
            'price': current_price,
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'details': f'RSI indicates oversold condition at {rsi:.1f}'
        })
    
    # SMA Trend Analysis
    if current_price > df['sma_50'].iloc[-1]:
        sma_status = {
            'type': 'Price Above SMA 50',
            'action': 'Hold/Buy small amounts',
            'confidence': 'Medium',
            'price': current_price,
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'details': 'Price is in overall uptrend'
        }
    else:
        sma_status = {
            'type': 'Price Below SMA 50',
            'action': 'Be cautious with new investments',
            'confidence': 'Low',
            'price': current_price,
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'details': 'Price is in overall downtrend'
        }
    recommendations.append(sma_status)
    
    # Save to DB
    conn = sqlite3.connect('bitcoin.db')
    c = conn.cursor()
    for rec in recommendations:
        c.execute("INSERT INTO recommendations VALUES (?, ?, ?, ?, ?)",
                 (rec['date'], rec['type'], rec['price'], rec['action'], rec['confidence']))
    conn.commit()
    conn.close()
    
    return recommendations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    period = data.get('period', '1y')
    
    try:
        df = get_bitcoin_data(period)
        recommendations = analyze_bitcoin(df)
        
        # Create plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['price'], name='Bitcoin Price', line=dict(color='#FF9500', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['sma_20'], name='SMA 20', line=dict(color='#34C759', width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=df['sma_50'], name='SMA 50', line=dict(color='#AF52DE', width=1)))
        
        # Add golden cross markers
        cross_dates = df[df['golden_cross']].index
        if not cross_dates.empty:
            fig.add_trace(go.Scatter(
                x=cross_dates,
                y=df.loc[cross_dates, 'price'],
                mode='markers',
                name='Golden Cross',
                marker=dict(color='green', size=10)
            ))
        
        fig.update_layout(
            title='Bitcoin Price Analysis',
            xaxis_title='Date',
            yaxis_title='Price (USD)',
            template='plotly_dark',
            hovermode='x unified'
        )
        
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({
            'status': 'success',
            'recommendations': recommendations,
            'chart': graphJSON,
            'current_price': round(df['price'].iloc[-1], 2),
            'last_updated': df.index[-1].strftime('%Y-%m-%d')
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/dca_simulator', methods=['POST'])
def dca_simulator():
    data = request.json
    initial_investment = float(data['amount'])
    period = data['period']
    
    df = get_bitcoin_data(period)
    weekly_dates = df.resample('W').last().index
    
    results = []
    total_btc = 0
    total_invested = 0
    for date in weekly_dates:
        price = df.loc[date, 'price']
        btc_bought = initial_investment / price
        total_btc += btc_bought
        total_invested += initial_investment
        results.append({
            'date': date.strftime('%Y-%m-%d'),
            'price': price,
            'btc_bought': btc_bought,
            'btc_accumulated': total_btc,
            'investment': total_invested
        })
    
    final_value = total_btc * df['price'].iloc[-1]
    profit_loss = final_value - total_invested
    roi = (profit_loss / total_invested) * 100
    
    return jsonify({
        'status': 'success',
        'results': results,
        'final_value': final_value,
        'total_invested': total_invested,
        'profit_loss': profit_loss,
        'roi': roi,
        'final_btc': total_btc
    })

if __name__ == '__main__':
    app.run(debug=True)
