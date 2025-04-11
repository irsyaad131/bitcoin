from flask import Flask, render_template, request, jsonify
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objs as go
import plotly
import json
import ta
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_bitcoin_data(period='1y'):
    try:
        btc = yf.Ticker("BTC-USD")
        hist = btc.history(period=period)
        df = pd.DataFrame(hist)
        df = df[['Close']].rename(columns={'Close': 'price'})
        df = df.resample('D').mean().ffill()
        
        # Calculate technical indicators
        df['sma_20'] = ta.trend.sma_indicator(df['price'], window=20)
        df['sma_50'] = ta.trend.sma_indicator(df['price'], window=50)
        df['rsi'] = ta.momentum.rsi(df['price'], window=14)
        
        return df
    except Exception as e:
        logger.error(f"Error fetching Bitcoin data: {str(e)}")
        raise

def analyze_bitcoin(df):
    recommendations = []
    last_row = df.iloc[-1]
    
    # Get current values
    current_price = round(last_row['price'], 2)
    sma_20 = round(last_row['sma_20'], 2)
    sma_50 = round(last_row['sma_50'], 2)
    rsi = round(last_row['rsi'], 2)
    
    # Determine allocation based on RSI
    if rsi < 15:
        allocation = 60
        rsi_recommendation = {
            'type': 'RSI Extreme Oversold',
            'strength': 'Strong Buy Signal',
            'description': f'RSI sangat rendah ({rsi}), alokasikan 60% modal'
        }
    elif rsi < 30:
        allocation = 30
        rsi_recommendation = {
            'type': 'RSI Oversold',
            'strength': 'Buy Signal',
            'description': f'RSI rendah ({rsi}), alokasikan 30% modal'
        }
    else:
        allocation = 10
        rsi_recommendation = {
            'type': 'RSI Normal',
            'strength': 'Hold',
            'description': f'RSI normal ({rsi}), alokasikan 10% modal'
        }
    
    # Add RSI recommendation
    recommendations.append({
        **rsi_recommendation,
        'date': df.index[-1].strftime('%Y-%m-%d'),
        'price': current_price,
        'allocation': allocation,
        'rsi': rsi
    })
    
    # Golden Cross detection
    if len(df) > 50:
        golden_cross = df[df['sma_20'] > df['sma_50']].index
        if len(golden_cross) > 0:
            last_cross = golden_cross[-1]
            recommendations.append({
                'type': 'Golden Cross',
                'date': last_cross.strftime('%Y-%m-%d'),
                'price': round(df.loc[last_cross, 'price'], 2),
                'strength': 'Bullish Signal',
                'description': 'SMA 20 melewati SMA 50 ke atas',
                'allocation': allocation,
                'rsi': rsi
            })
    
    return {
        'recommendations': recommendations,
        'current_price': current_price,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'rsi': rsi,
        'default_allocation': allocation,
        'last_updated': df.index[-1].strftime('%Y-%m-%d')
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    period = data.get('period', '1y')
    
    try:
        df = get_bitcoin_data(period)
        analysis = analyze_bitcoin(df)
        
        # Create plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['price'],
            name='Bitcoin Price',
            line=dict(color='#FF9500', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['sma_20'],
            name='SMA 20',
            line=dict(color='#34C759', width=1.5, dash='dot')
        ))
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['sma_50'],
            name='SMA 50',
            line=dict(color='#AF52DE', width=1.5, dash='dot')
        ))
        
        fig.update_layout(
            title='Bitcoin Price Analysis',
            xaxis_title='Date',
            yaxis_title='Price (USD)',
            template='plotly_dark',
            hovermode='x unified'
        )
        
        return jsonify({
            'status': 'success',
            'recommendations': analysis['recommendations'],
            'chart': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
            'current_price': analysis['current_price'],
            'sma_20': analysis['sma_20'],
            'sma_50': analysis['sma_50'],
            'rsi': analysis['rsi'],
            'default_allocation': analysis['default_allocation'],
            'last_updated': analysis['last_updated']
        })
        
    except Exception as e:
        logger.error(f"Error in get_recommendations: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True)
