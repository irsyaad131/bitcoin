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
from forex_python.converter import CurrencyRates

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
c = CurrencyRates()

# Setup database
def init_db():
    conn = sqlite3.connect('bitcoin.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS rekomendasi
                 (tanggal text, tipe text, harga real, aksi text, confidence text)''')
    conn.commit()
    conn.close()

init_db()

def usd_to_idr(usd_amount):
    try:
        return c.convert('USD', 'IDR', usd_amount)
    except:
        return usd_amount * 15000  # Fallback rate jika API error

@cache.cached(timeout=3600)
def get_bitcoin_data(periode='1y'):
    btc = yf.Ticker("BTC-USD")
    hist = btc.history(period=periode)
    df = pd.DataFrame(hist)
    df = df[['Close', 'Volume']].rename(columns={'Close': 'harga'})
    df = df.resample('D').mean().ffill()
    
    # Konversi harga ke IDR
    df['harga_idr'] = df['harga'].apply(lambda x: usd_to_idr(x))
    
    # Hitung indikator
    df['sma_20'] = ta.trend.sma_indicator(df['harga'], window=20)
    df['sma_50'] = ta.trend.sma_indicator(df['harga'], window=50)
    df['rsi'] = ta.momentum.rsi(df['harga'], window=14)
    df['golden_cross'] = (df['sma_20'] > df['sma_50']) & (df['sma_20'].shift(1) <= df['sma_50'].shift(1))
    df['death_cross'] = (df['sma_20'] < df['sma_50']) & (df['sma_20'].shift(1) >= df['sma_50'].shift(1))
    
    return df

def analisis_bitcoin(df):
    rekomendasi = []
    harga_terkini = df['harga'].iloc[-1]
    harga_terkini_idr = df['harga_idr'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    
    # Deteksi Golden Cross
    if df['golden_cross'].iloc[-1]:
        rekomendasi.append({
            'tipe': 'Golden Cross Terdeteksi',
            'aksi': 'Alokasikan 50% modal',
            'confidence': 'Tinggi',
            'harga': harga_terkini,
            'harga_idr': harga_terkini_idr,
            'tanggal': df.index[-1].strftime('%Y-%m-%d'),
            'detail': 'SMA 20 melewati SMA 50 ke atas, indikasi tren bullish'
        })
    
    # Beli saat harga turun (RSI)
    if rsi < 30:
        persentase_penurunan = ((df['harga'].iloc[-3] - harga_terkini) / df['harga'].iloc[-3]) * 100
        rekomendasi.append({
            'tipe': f'Beli saat Turun (RSI {rsi:.1f})',
            'aksi': f'Alokasikan 30% modal (Turun {persentase_penurunan:.1f}%)',
            'confidence': 'Tinggi' if persentase_penurunan > 10 else 'Sedang',
            'harga': harga_terkini,
            'harga_idr': harga_terkini_idr,
            'tanggal': df.index[-1].strftime('%Y-%m-%d'),
            'detail': f'RSI menunjukkan kondisi oversold di {rsi:.1f}'
        })
    
    # Analisis tren SMA
    if harga_terkini > df['sma_50'].iloc[-1]:
        status_sma = {
            'tipe': 'Harga di Atas SMA 50',
            'aksi': 'Tahan/Beli dalam jumlah kecil',
            'confidence': 'Sedang',
            'harga': harga_terkini,
            'harga_idr': harga_terkini_idr,
            'tanggal': df.index[-1].strftime('%Y-%m-%d'),
            'detail': 'Harga dalam tren naik keseluruhan'
        }
    else:
        status_sma = {
            'tipe': 'Harga di Bawah SMA 50',
            'aksi': 'Hati-hati dengan investasi baru',
            'confidence': 'Rendah',
            'harga': harga_terkini,
            'harga_idr': harga_terkini_idr,
            'tanggal': df.index[-1].strftime('%Y-%m-%d'),
            'detail': 'Harga dalam tren turun keseluruhan'
        }
    rekomendasi.append(status_sma)
    
    # Simpan ke database
    conn = sqlite3.connect('bitcoin.db')
    cur = conn.cursor()
    for rec in rekomendasi:
        cur.execute("INSERT INTO rekomendasi VALUES (?, ?, ?, ?, ?)",
                 (rec['tanggal'], rec['tipe'], rec['harga'], rec['aksi'], rec['confidence']))
    conn.commit()
    conn.close()
    
    return rekomendasi

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dapatkan_rekomendasi', methods=['POST'])
def dapatkan_rekomendasi():
    data = request.json
    periode = data.get('periode', '1y')
    
    try:
        df = get_bitcoin_data(periode)
        rekomendasi = analisis_bitcoin(df)
        
        # Buat plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['harga_idr'],
            name='Harga Bitcoin',
            line=dict(color='#FF9500', width=2),
            hovertemplate='%{y:,.0f} IDR'
        ))
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['sma_20'].apply(lambda x: usd_to_idr(x)),
            name='SMA 20',
            line=dict(color='#34C759', width=1),
            hovertemplate='%{y:,.0f} IDR'
        ))
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['sma_50'].apply(lambda x: usd_to_idr(x)),
            name='SMA 50',
            line=dict(color='#AF52DE', width=1),
            hovertemplate='%{y:,.0f} IDR'
        ))
        
        # Tambahkan marker golden cross
        cross_dates = df[df['golden_cross']].index
        if not cross_dates.empty:
            fig.add_trace(go.Scatter(
                x=cross_dates,
                y=df.loc[cross_dates, 'harga_idr'],
                mode='markers',
                name='Golden Cross',
                marker=dict(color='green', size=10),
                hovertemplate='%{y:,.0f} IDR'
            ))
        
        fig.update_layout(
            title='Analisis Harga Bitcoin',
            xaxis_title='Tanggal',
            yaxis_title='Harga (IDR)',
            template='plotly_dark',
            hovermode='x unified',
            yaxis_tickformat=',.0f'
        )
        
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({
            'status': 'sukses',
            'rekomendasi': rekomendasi,
            'grafik': graphJSON,
            'harga_terkini': round(df['harga'].iloc[-1], 2),
            'harga_terkini_idr': round(df['harga_idr'].iloc[-1], 2),
            'terakhir_update': df.index[-1].strftime('%Y-%m-%d')
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'pesan': str(e)})

@app.route('/simulator_dca', methods=['POST'])
def simulator_dca():
    data = request.json
    investasi_awal = float(data['jumlah'])
    periode = data['periode']
    
    df = get_bitcoin_data(periode)
    tanggal_mingguan = df.resample('W').last().index
    
    hasil = []
    total_btc = 0
    total_investasi = 0
    for tanggal in tanggal_mingguan:
        harga = df.loc[tanggal, 'harga']
        harga_idr = df.loc[tanggal, 'harga_idr']
        btc_didapat = investasi_awal / harga
        total_btc += btc_didapat
        total_investasi += investasi_awal
        hasil.append({
            'tanggal': tanggal.strftime('%Y-%m-%d'),
            'harga': harga,
            'harga_idr': harga_idr,
            'btc_didapat': btc_didapat,
            'total_btc': total_btc,
            'investasi': total_investasi,
            'investasi_idr': total_investasi * 15000  # Asumsi kurs 15.000
        })
    
    nilai_akhir = total_btc * df['harga'].iloc[-1]
    nilai_akhir_idr = total_btc * df['harga_idr'].iloc[-1]
    profit_rugi = nilai_akhir - total_investasi
    profit_rugi_idr = nilai_akhir_idr - (total_investasi * 15000)
    roi = (profit_rugi / total_investasi) * 100
    
    return jsonify({
        'status': 'sukses',
        'hasil': hasil,
        'nilai_akhir': nilai_akhir,
        'nilai_akhir_idr': nilai_akhir_idr,
        'total_investasi': total_investasi,
        'total_investasi_idr': total_investasi * 15000,
        'profit_rugi': profit_rugi,
        'profit_rugi_idr': profit_rugi_idr,
        'roi': roi,
        'total_btc': total_btc
    })

if __name__ == '__main__':
    app.run(debug=True)
