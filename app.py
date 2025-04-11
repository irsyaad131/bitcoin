from flask import Flask, render_template, request, jsonify
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.graph_objs as go
import plotly
import json
import ta
import logging
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_bitcoin_data(period='5y'):  # Changed default to 5y
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

def analyze_dca(df, initial_investment=1000):
    end_date = df.index[-1]
    start_date = df.index[0]
    
    dca_dates = []
    current_date = start_date
    
    # Generate DCA dates every 4 months
    while current_date <= end_date:
        dca_dates.append(current_date)
        current_date += relativedelta(months=4)
    
    dca_results = []
    total_btc = 0
    total_invested = 0
    
    for date in dca_dates:
        if date in df.index:
            price = df.loc[date, 'price']
            btc_bought = initial_investment / price
            total_btc += btc_bought
            total_invested += initial_investment
            
            dca_results.append({
                'date': date.strftime('%Y-%m-%d'),
                'price': round(price, 2),
                'btc_bought': round(btc_bought, 6),
                'total_btc': round(total_btc, 6),
                'total_invested': round(total_invested, 2),
                'current_value': round(total_btc * price, 2)
            })
    
    # Calculate final results
    if dca_results:
        final_value = total_btc * df['price'].iloc[-1]
        profit = final_value - total_invested
        roi = (profit / total_invested) * 100
        
        return {
            'transactions': dca_results,
            'summary': {
                'total_invested': round(total_invested, 2),
                'total_btc': round(total_btc, 6),
                'current_value': round(final_value, 2),
                'profit': round(profit, 2),
                'roi': round(roi, 2),
                'final_price': round(df['price'].iloc[-1], 2)
            }
        }
    return None

def analyze_bitcoin(df):
    recommendations = []
    last_row = df.iloc[-1]
    
    # Get current values
    current_price = round(last_row['price'], 2)
    sma_20 = round(last_row['sma_20'], 2)
    sma_50 = round(last_row['sma_50'], 2)
    rsi = round(last_row['rsi'], 2)
    
    # BUY Recommendations based on new RSI rules
    if rsi < 15:
        allocation = 40
        recommendations.append({
            'type': 'RSI Extreme Oversold',
            'action': 'buy',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Strong Buy Signal',
            'description': f'RSI sangat rendah ({rsi}), alokasikan 40% modal',
            'allocation': allocation,
            'rsi': rsi
        })
    elif rsi < 30:
        allocation = 20
        recommendations.append({
            'type': 'RSI Oversold',
            'action': 'buy',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Buy Signal',
            'description': f'RSI rendah ({rsi}), alokasikan 20% modal',
            'allocation': allocation,
            'rsi': rsi
        })
    elif rsi > 40:
        allocation = 10
        recommendations.append({
            'type': 'RSI Normal',
            'action': 'buy',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Normal Market',
            'description': f'RSI normal ({rsi}), alokasikan 10% modal',
            'allocation': allocation,
            'rsi': rsi
        })
    
    # SELL Recommendations
    if rsi > 80:
        sell_percentage = 40
        recommendations.append({
            'type': 'RSI Extreme Overbought',
            'action': 'sell',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Strong Sell Signal',
            'description': f'RSI sangat tinggi ({rsi}), jual 40% Bitcoin',
            'percentage': sell_percentage,
            'rsi': rsi
        })
    elif rsi > 70:
        sell_percentage = 20
        recommendations.append({
            'type': 'RSI Overbought',
            'action': 'sell',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Sell Signal',
            'description': f'RSI tinggi ({rsi}), jual 20% Bitcoin',
            'percentage': sell_percentage,
            'rsi': rsi
        })
    
    return {
        'recommendations': recommendations,
        'current_price': current_price,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'rsi': rsi,
        'default_allocation': allocation if 'allocation' in locals() else 0
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    period = data.get('period', '5y')  # Changed default to 5y
    dca_amount = data.get('dca_amount', 1000)
    
    try:
        df = get_bitcoin_data(period)
        analysis = analyze_bitcoin(df)
        dca_analysis = analyze_dca(df, dca_amount)
        
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
        
        # Add DCA markers
        if dca_analysis:
            dca_dates = [datetime.strptime(t['date'], '%Y-%m-%d') for t in dca_analysis['transactions']]
            dca_prices = [t['price'] for t in dca_analysis['transactions']]
            fig.add_trace(go.Scatter(
                x=dca_dates,
                y=dca_prices,
                name='DCA Points',
                mode='markers',
                marker=dict(
                    color='#007AFF',
                    size=10,
                    symbol='triangle-up'
                )
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
            'dca_analysis': dca_analysis,
            'chart': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
            'current_price': analysis['current_price'],
            'sma_20': analysis['sma_20'],
            'sma_50': analysis['sma_50'],
            'rsi': analysis['rsi'],
            'default_allocation': analysis['default_allocation'],
            'last_updated': df.index[-1].strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        logger.error(f"Error in get_recommendations: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True)
