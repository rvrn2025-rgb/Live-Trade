import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import math
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת תצורת דף PRO
st.set_page_config(page_title="DCA Matrix // Leveraged Terminal", layout="wide")

# רענון אוטומטי של המסך בכל 30 שניות לשמירה על נתוני אמת
st_autorefresh(interval=30000, key="matrix_refresh")

# 2. הזרקת עיצוב קסטום (הצמדה לשוליים כדי למנוע הצגת קוד גולמי)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #05070f !important;
    color: #ffffff !important;
    font-family: 'Assistant', sans-serif !important;
    direction: RTL !important;
    text-align: right !important;
}

h1, h2, h3, h4 {
    color: #ffffff !important;
    font-weight: 800 !important;
}

label, p, span {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #f1f5f9 !important;
}

input {
    font-size: 18px !important;
    font-weight: 700 !important;
}

.control-panel {
    background: #0f172a;
    border: 2px solid #1e293b;
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 25px;
}

.terminal-table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 17px;
    font-weight: 600;
    background-color: #0b0f19;
    border: 2px solid #1e293b;
    border-radius: 8px;
    overflow: hidden;
}

.terminal-table th {
    background-color: #1e293b;
    color: #38bdf8;
    font-size: 18px;
    font-weight: 800;
    padding: 16px;
    text-align: right;
    border-bottom: 3px solid #334155;
}

.terminal-table td {
    padding: 16px;
    border-bottom: 1px solid #1e293b;
    color: #ffffff;
    vertical-align: middle;
}

.terminal-table tr:hover {
    background-color: #111827;
}

.badge-drop {
    background-color: #7f1d1d;
    color: #fca5a5;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 16px;
}

.badge-tranche {
    background-color: #1e3a8a;
    color: #93c5fd;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 700;
}

.badge-money {
    color: #34d399;
    font-weight: 700;
}

.playbook-card {
    background-color: #0f172a;
    border-right: 5px solid #3b82f6;
    padding: 20px;
    border-radius: 4px 12px 12px 4px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# 3. כותרת הטרמינל
st.markdown('<h1 style="text-align: center; color: #38bdf8; font-size: 36px; margin-bottom: 5px;">⚡ טבלת מעקב ממונפות וליבה</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 20px; margin-bottom: 30px;">מערכת אלגוריתמית מתקדמת לניהול מנות איסוף ומיצוע הנדסי (DCA) ללא רגש</p>', unsafe_allow_html=True)

# 4. לוח בקרה אינטראקטיבי
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
col_param1, col_param2, col_param3 = st.columns(3)

with col_param1:
    tranche_size = st.number_input("💰 גודל מנה קבועה לרכישה מהממונף ($):", min_value=100, max_value=100000, value=3000, step=500)

with col_param2:
    drop_interval = st.selectbox("📐 מרווח ירידת הבסיס בין מנות (%):", [3.5, 5.0, 7.0, 10.0], index=0)

with col_param3:
    st.write("")
    st.write("")
    st.markdown("<p style='color: #34d399; font-weight: 800; text-align: center; font-size: 20px; margin-top: 10px;'>📡 סימולטור אישי פעיל בזמן אמת</p>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 5. הגדרת זוגות המטריצה
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (QQQ / TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXX / SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (SPY / UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (XLF / FAS)"}
]

# בניית שלד הטבלה ב-HTML
table_html = """
<table class="terminal-table">
    <thead>
        <tr>
            <th>צמד נכסים (בסיס / ממונף)</th>
            <th>ירידת הבסיס מהשיא</th>
            <th>⚡ מנות שנרכשו מהממונף</th>
            <th>💰 הון מושקע בפוזיציה</th>
            <th>🎯 מחירי יעד למנה הבאה</th>
            <th title="מדד RSI מתורגם למצב פסיכולוגי">🌡️ מדחום מומנטום</th>
            <th>🔮 המלצה לביצוע ללא רגש</th>
        </tr>
    </thead>
    <tbody>
"""

for pair in asset_pairs:
    try:
        base_stock = yf.Ticker(pair["base"])
        base_hist = base_stock.history(period="6mo", interval="1d")
        
        lev_stock = yf.Ticker(pair["leveraged"])
        lev_hist = lev_stock.history(period="6mo", interval="1d")
        
        if len(base_hist) > 14 and len(lev_hist) > 14:
            base_curr = base_hist['Close'].iloc[-1]
            base_max = base_hist['High'].max()
            
            lev_curr = lev_hist['Close'].iloc[-1]
            lev_max = lev_hist['High'].max()
            
            base_drop = ((base_curr - base_max) / base_max) * 100
            abs_drop = abs(base_drop)
            
            tranches_bought = math.floor(abs_drop / drop_interval)
            total_deployed = tranches_bought * tranche_size
            
            next_tranche_num = tranches_bought + 1
            next_base_drop_target = next_tranche_num * drop_interval
            next_lev_drop_target = next_base_drop_target * 3
            
            next_base_price = base_max * (1 - (next_base_drop_target / 100))
            next_lev_price = lev_max * (1 - (next_lev_drop_target / 100))
            if next_lev_price < 0: next_lev_price = 0
            
            rsi = ta.momentum.rsi(base_hist['Close'], window=14).iloc[-1]
            if rsi < 30:
                momentum_status = f"<span style='color: #ef4444; font-weight: bold;'>🔥 מכירת יתר קיצונית ({round(rsi,1)})</span>"
            elif rsi < 45:
                momentum_status = f"<span style='color: #f97316; font-weight: bold;'>📉 מומנטום חלש ({round(rsi,1)})</span>"
            elif rsi < 60:
                momentum_status = f"<span style='color: #94a3b8;'>⚪ נייטרלי לחלוטין ({round(rsi,1)})</span>"
            else:
                momentum_status = f"<span style='color: #22c55e; font-weight: bold;'>📈 מומנטום חזק ({round(rsi,1)})</span>"
            
            distance_to_next = next_base_drop_target - abs_drop
            if distance_to_next <= 0.5:
                rec_text = f"<td style='background-color: #78350f; color: #fbbf24; font-weight: bold;'>🚨 פקודה: רכוש מנה {next_tranche_num}!</td>"
            else:
                rec_text = f"<td style='color: #a1a1aa;'>⏳ ממתין למדרגה {next_tranche_num} ב-{next_base_drop_target}%</td>"
                
            table_html += f"""
            <tr>
                <td style="font-size: 18px; font-weight: bold; color: #38bdf8;">{pair["name"]}</td>
                <td><span class="badge-drop">{round(base_drop, 1)}%</span></td>
                <td><span class="badge-tranche">{tranches_bought} מנות בפנים</span></td>
                <td><span class="badge-money">${total_deployed:,}</span></td>
                <td style="font-size: 16px; line-height: 1.5;">
                    <b style="color: #94a3b8;">בסיס ({pair["base"]}):</b> <b style="color: #ffffff;">${round(next_base_price, 2)}</b><br>
                    <b style="color: #94a3b8;">ממונף ({pair["leveraged"]}):</b> <b style="color: #34d399;">${round(next_lev_price, 2)}</b>
                </td>
                <td>{momentum_status}</td>
                {rec_text}
            </tr>
            """
    except Exception as e:
        continue

table_html += "</tbody></table>"

# הזרקת הטבלה המעוצבת
st.markdown(table_html, unsafe_allow_html=True)

# 6. ספר חוקים הנדסי
st.write("")
st.write("---")
st.markdown('### 🛠️ מדריך הפעלה מהיר לקבוצה')

col_guide1, col_guide2 = st.columns(2)

with col_guide1:
    st.markdown("""
<div class="playbook-card">
    <h4 style="font-size: 19px; color: #38bdf8; margin-bottom: 8px;">📐 חוק המנות והמרווח הדינמי</h4>
    <p style="font-size: 16px; color: #cbd5e1;">הטבלה מחלקת את השוק לרצועות קשיחות לבחירתך. המנות שנקנות הן <b>אך ורק של הנייר הממונף (TQQQ, SOXL וכו')</b>. המערכת סופרת כמה מנות היית אמור לקנות באופן קר ומכפילה בתקציב שלך כדי להציג את ההון הממושך בפוזיציה.</p>
</div>
""", unsafe_allow_html=True)

with col_guide2:
    st.markdown("""
<div class="playbook-card" style="border-right-color: #34d399;">
    <h4 style="font-size: 19px; color: #34d399; margin-bottom: 8px;">🎯 טריגר לפי הבסיס - קנייה בממונף</h4>
    <p style="font-size: 16px; color: #cbd5e1;">עמודת <b>מחירי היעד</b> מציגה לך את שני המחירים במקביל: מחיר היעד של הבסיס שמהווה את הטריגר הראשי, ומחיר היעד המשוער של הממונף באותה נקודה בדיוק (מחושב ביחס של פי 3 ירידה מהטופ שלו) כדי שתוכל להציב פקודות בהתאם.</p>
</div>
""", unsafe_allow_html=True)
