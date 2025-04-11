# Update the analyze_bitcoin function
def analyze_bitcoin(df):
    recommendations = []
    last_row = df.iloc[-1]
    
    # Get current indicator values
    current_price = round(last_row['price'], 2)
    sma_20 = round(last_row['sma_20'], 2)
    sma_50 = round(last_row['sma_50'], 2)
    rsi = round(last_row['rsi'], 2)
    
    # Calculate allocation based on RSI
    allocation = 10  # Default allocation
    if rsi < 15:
        allocation = 60
        recommendations.append({
            'type': 'RSI Extreme Oversold',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Strong Buy Opportunity',
            'description': f'RSI at extremely low level ({rsi}), consider allocating 60% of capital',
            'allocation': allocation,
            'rsi': rsi
        })
    elif rsi < 30:
        allocation = 30
        recommendations.append({
            'type': 'RSI Oversold',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Buy Opportunity',
            'description': f'RSI at low level ({rsi}), consider allocating 30% of capital',
            'allocation': allocation,
            'rsi': rsi
        })
    else:
        recommendations.append({
            'type': 'RSI Normal',
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': current_price,
            'strength': 'Normal Market',
            'description': f'RSI at normal level ({rsi}), consider allocating 10% of capital',
            'allocation': allocation,
            'rsi': rsi
        })
    
    # Golden Cross detection
    if len(df) > 50:  # Ensure enough data for SMA 50
        golden_cross = df[df['sma_20'] > df['sma_50']].index
        if len(golden_cross) > 0:
            last_golden_cross = golden_cross[-1]
            recommendations.append({
                'type': 'Golden Cross',
                'date': last_golden_cross.strftime('%Y-%m-%d'),
                'price': round(df.loc[last_golden_cross, 'price'], 2),
                'strength': 'Bullish Signal',
                'description': 'Short-term SMA crossed above long-term SMA',
                'allocation': allocation,
                'rsi': rsi
            })
    
    return {
        'recommendations': recommendations,
        'current_price': current_price,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'rsi': rsi,
        'default_allocation': allocation
    }

# Update the get_recommendations endpoint
@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    period = data.get('period', '1y')
    
    try:
        df = get_bitcoin_data(period)
        analysis_result = analyze_bitcoin(df)
        
        # Create plot (existing code remains the same)
        fig = go.Figure()
        # ... (keep your existing chart code)
        
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({
            'status': 'success',
            'recommendations': analysis_result['recommendations'],
            'chart': graphJSON,
            'current_price': analysis_result['current_price'],
            'sma_20': analysis_result['sma_20'],
            'sma_50': analysis_result['sma_50'],
            'rsi': analysis_result['rsi'],
            'default_allocation': analysis_result['default_allocation'],
            'last_updated': df.index[-1].strftime('%Y-%m-%d')
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })
