import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import ta
import math
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת תצורת דף PRO
st.set_page_config(page_title="DCA Matrix // Leveraged Terminal", layout="wide")

# רענון אוטומטי בכל 65 שניות כדי להישאר תמיד מתחת למגבלת ה-8 קרדיטים לדקה של Twelve Data
st_autorefresh(interval=65000, key="matrix_refresh")

# 2. הזרקת עיצוב קסטום 
st.markdown("""<style>
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
</style>""", unsafe_allow_html=True)

# 3. כותרת הטרמינל
st.markdown('<h1 style="text-align: center; color: #38bdf8; font-size: 36px; margin-bottom: 5px;">⚡ טבלת מעקב ממונפות וליבה (HYBRID REAL-TIME)</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 20px; margin-bottom: 30px;">לוגיקה משולבת לעקיפת חסימות קרדיטים – מחירי שוק באפס דיליי</p>', unsafe_allow_html=True)

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
    st.markdown("<p style='color: #34d399; font-weight: 800; text-align: center; font-size: 20px; margin-top: 10px;'>🟢 מותאם למגבלת 8 Credits/Min</p>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 5. הגדרת זוגות המטריצה
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (QQQ / TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXX / SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (SPY / UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (XLF / FAS)"}
]

API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
all_symbols = ["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"]
symbols_str = ",".join(all_symbols)

# פנייה לצינור /price החסכוני (צורך רק 8 קרדיטים לכל הבלוק)
price_url = f"https://api.twelvedata.com/price?symbol={symbols_str}&apikey={API_KEY}"

table_html = """
<table class="terminal-table">
<thead>
<tr>
<th>צמד נכסים (בסיס / ממונף)</th>
<th>שער אמת (בסיס / ממונף)</th>
<th>ירידת הבסיס מהשיא</th>
<th>⚡ מנות שנרכשו מהממונף</th>
<th>💰 הון מושקע בפוזיציה</th>
<th>🎯 טריגר כניסה למנה הבאה</th>
<th>🌡️ מדחום מומנטום</th>
<th>🔮 המלצה לביצוע ללא רגש</th>
</tr>
</thead>
<tbody>
"""

try:
    price_response = requests.get(price_url).json()
    
    if "status" in price_response and price_response["status"] == "error":
        st.error(f"❌ שגיאת מכסת API מצד Twelve Data: {price_response.get('message')}")
    else:
        for pair in asset_pairs:
            # שליפת מחירי הלייב המדויקים מ-Twelve Data
            base_realtime = price_response.get(pair["base"], {})
            lev_realtime = price_response.get(pair["leveraged"], {})
            
            if "price" in base_realtime and "price" in lev_realtime:
                base_curr = float(base_realtime["price"])
                lev_curr = float(lev_realtime["price"])
                
                # משיכת היסטוריה חינמית ללא מגבלות מ-yfinance עבור השיא וה-RSI
                base_stock = yf.Ticker(pair["base"])
                df_base = base_stock.history(period="6mo", interval="1d", auto_adjust=False)
                
                if len(df_base) > 14:
                    # מציאת השיא האבסולוטי (כולל מחיר הלייב הנוכחי במידה והוא שובר שיא עכשיו)
                    base_max = max(df_base['High'].max(), base_curr)
                    
                    # חישוב אחוז הירידה המדויק בזמן אמת
                    base_drop = ((base_curr - base_max) / base_max) * 100
                    abs_drop = abs(base_drop)
                    
                    # בניית סדרת מחירים מעודכנת להזרקת מחיר הלייב לתוך ה-RSI
                    close_series = df_base['Close'].copy()
                    close_series.iloc[-1] = base_curr
                    rsi = ta.momentum.rsi(close_series, window=14).iloc[-1]
                    
                    # מתמטיקת המטריצה
                    tranches_bought = math.floor(abs_drop / drop_interval)
                    total_deployed = tranches_bought * tranche_size
                    
                    next_tranche_num = tranches_bought + 1
                    next_base_drop_target = next_tranche_num * drop_interval
                    next_base_price = base_max * (1 - (next_base_drop_target / 100))
                    
                    # צביעת מדחום המומנטום
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
                    
                    table_html += f"""<tr>
<td style="font-size: 18px; font-weight: bold; color: #38bdf8;">{pair["name"]}</td>
<td style="font-size: 16px; line-height: 1.5;">
<b style="color: #94a3b8;">בסיס:</b> ${round(base_curr, 2)}<br>
<b style="color: #94a3b8;">ממונף:</b> ${round(lev_curr, 2)}
</td>
<td><span class="badge-drop">{round(base_drop, 1)}%</span></td>
<td><span class="badge-tranche">{tranches_bought} מנות בפנים</span></td>
<td><span class="badge-money">${total_deployed:,}</span></td>
<td style="font-size: 16px; line-height: 1.5;">
<span style="color: #ffffff; font-weight: bold;">כשהבסיס ({pair["base"]}) מגיע ל:</span><br>
<b style="color: #38bdf8; font-size: 18px;">${round(next_base_price, 2)}</b><br>
<span style="color: #94a3b8; font-size: 14px;">(קנה את {pair["leveraged"]} במחיר שוק)</span>
</td>
<td>{momentum_status}</td>
{rec_text}
</tr>"""
except Exception as e:
    st.error(f"שגיאה בעיבוד הנתונים הטרמינלי: {e}")

table_html += "</tbody></table>"

# הזרקת הטבלה 
st.markdown(table_html, unsafe_allow_html=True)

# 6. ספר חוקים הנדסי לקבוצה
st.write("")
st.write("---")
st.markdown('### 🛠️ מדריך הפעלה מהיר לקבוצה')

col_guide1, col_guide2 = st.columns(2)

with col_guide1:
    st.markdown("""<div class="playbook-card">
<h4 style="font-size: 19px; color: #38bdf8; margin-bottom: 8px;">📐 ארכיטקטורה היברידית חסכונית</h4>
<p style="font-size: 16px; color: #cbd5e1;">השיאים ההיסטוריים מחושבים באמצעות מנוע חינמי נטול הגבלות, בעוד שמחירי הניירות ברגע זה מוזרקים בלייב מ-Twelve Data כדי לשמור על אפס שניות דיליי בלי לחרוג מהמכסה.</p>
</div>""", unsafe_allow_html=True)

with col_guide2:
    st.markdown("""<div class="playbook-card" style="border-right-color: #34d399;">
<h4 style="font-size: 19px; color: #34d399; margin-bottom: 8px;">⏱️ קצב סנכרון המטריצה</h4>
<p style="font-size: 16px; color: #cbd5e1;">הדף מבצע רענון פנימי קבוע פעם ב-65 שניות כדי לכבד את חוקי השרת החינמיים. כל פעימה מציגה את המחיר המדויק שקיים בשוק באותה השנייה.</p>
</div>""", unsafe_allow_html=True)
