import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import ta
import math
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת תצורת דף PRO
st.set_page_config(page_title="DCA Matrix // Ultimate Terminal", layout="wide")

# רענון אוטומטי בכל 65 שניות למניעת חריגת קרדיטים
st_autorefresh(interval=65000, key="matrix_refresh")

# 2. הזרקת עיצוב קסטום מתקדם (כולל תמיכה בטריגרים, בועות ריחוף וסיכומים)
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

/* כרטיסי סיכום עליונים */
.kpi-container {
    display: flex;
    gap: 20px;
    margin-bottom: 25px;
}
.kpi-card {
    flex: 1;
    background: #0f172a;
    border: 2px solid #1e293b;
    border-radius: 8px;
    padding: 15px;
    text-align: center;
}
.kpi-title {
    font-size: 14px !important;
    color: #94a3b8 !important;
    margin-bottom: 5px;
}
.kpi-value {
    font-size: 24px !important;
    font-weight: 800 !important;
    color: #38bdf8;
}

/* עיצוב הטבלה */
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
    font-size: 16px;
    font-weight: 800;
    padding: 14px;
    text-align: right;
    border-bottom: 3px solid #334155;
    cursor: help;
}

.terminal-table td {
    padding: 14px;
    border-bottom: 1px solid #1e293b;
    color: #ffffff;
    vertical-align: middle;
}

/* שורה במצב טריגר אקטיבי לקנייה */
.row-trigger {
    background-color: #2d1510 !important;
    border-right: 6px solid #ef4444 !important;
}
.row-normal:hover {
    background-color: #111827;
}

.badge-drop {
    background-color: #7f1d1d;
    color: #fca5a5;
    padding: 4px 8px;
    border-radius: 6px;
    font-weight: 700;
}

.badge-blackswan {
    background-color: #450a0a;
    color: #f87171;
    border: 1px solid #ef4444;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
    display: inline-block;
    margin-top: 4px;
}

.badge-tranche {
    background-color: #1e3a8a;
    color: #93c5fd;
    padding: 4px 8px;
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
st.markdown('<h1 style="text-align: center; color: #38bdf8; font-size: 36px; margin-bottom: 5px;">⚡ טבלת מעקב ממונפות וליבה</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 20px; margin-bottom: 30px;">מערכת אלגוריתמית מתקדמת לניהול מנות איסוף ומיצוע הנדסי (DCA) ללא רגש</p>', unsafe_allow_html=True)

# 4. לוח בקרה אינטראקטיבי
col_param1, col_param2, col_param3 = st.columns(3)

with col_param1:
    tranche_size = st.number_input("💰 גודל מנה קבועה לרכישה מהממונף ($):", min_value=100, max_value=100000, value=3000, step=500)

with col_param2:
    drop_interval = st.selectbox("📐 מרווח ירידת הבסיס בין מנות (%):", [3.5, 5.0, 7.0, 10.0], index=0)

with col_param3:
    st.write("")
    st.write("")
    st.markdown("<p style='color: #34d399; font-weight: 800; text-align: center; font-size: 20px; margin-top: 5px;'>🟢 שערי אמת מסונכרנים בלייב</p>", unsafe_allow_html=True)

# 5. פונקציית משיכת נתונים מרוכזת עם הגנת Cache ל-60 שניות
@st.cache_data(ttl=60)
def get_realtime_quotes(symbols_string, api_key):
    url = f"https://api.twelvedata.com/quote?symbol={symbols_string}&apikey={api_key}"
    try:
        res = requests.get(url).json()
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}

# הגדרת נכסים
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (QQQ / TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXX / SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (SPY / UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (XLF / FAS)"}
]

API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
all_symbols = ["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"]
symbols_str = ",".join(all_symbols)

quote_response = get_realtime_quotes(symbols_str, API_KEY)

# משתני סיכום עבור ה-KPIs
total_tranches_global = 0
total_money_global = 0
active_triggers_count = 0

table_rows_html = ""

if "status" in quote_response and quote_response["status"] == "error":
    st.error(f"❌ שגיאת מכסת API מצד Twelve Data: {quote_response.get('message')}")
else:
    try:
        for pair in asset_pairs:
            base_quote = quote_response.get(pair["base"], {})
            lev_quote = quote_response.get(pair["leveraged"], {})
            
            if "close" in base_quote or "price" in base_quote:
                # חילוץ מחיר נוכחי ושינוי יומי מתוך ה-Quote API
                base_curr = float(base_quote.get("price", base_quote.get("close", 0)))
                lev_curr = float(lev_quote.get("price", lev_quote.get("close", 0)))
                lev_change = float(lev_quote.get("percent_change", 0))
                
                # משיכת היסטוריה מ-yfinance ללא מגבלת מכסות (עבור שיאים, RSI ו-MFI)
                base_stock = yf.Ticker(pair["base"])
                df_base = base_stock.history(period="6mo", interval="1d", auto_adjust=False)
                
                lev_stock = yf.Ticker(pair["leveraged"])
                df_lev = lev_stock.history(period="6mo", interval="1d", auto_adjust=False)
                
                if len(df_base) > 14 and len(df_lev) > 14:
                    # עדכון נר הלייב האחרון בבסיס
                    df_base.loc[df_base.index[-1], 'Close'] = base_curr
                    if base_curr > df_base.loc[df_base.index[-1], 'High']:
                        df_base.loc[df_base.index[-1], 'High'] = base_curr
                    if base_curr < df_base.loc[df_base.index[-1], 'Low']:
                        df_base.loc[df_base.index[-1], 'Low'] = base_curr
                    
                    # חישוב מרחקים מהשיא
                    base_max = max(df_base['High'].max(), base_curr)
                    base_drop = ((base_curr - base_max) / base_max) * 100
                    abs_drop = abs(base_drop)
                    
                    lev_max = max(df_lev['High'].max(), lev_curr)
                    lev_drop = ((lev_curr - lev_max) / lev_max) * 100
                    
                    # חישוב RSI מומונטום ואינדיקטור זרימת כסף מוסדי (MFI)
                    rsi = ta.momentum.rsi(df_base['Close'], window=14).iloc[-1]
                    mfi = ta.volume.money_flow_index(high=df_base['High'], low=df_base['Low'], close=df_base['Close'], volume=df_base['Volume'], window=14).iloc[-1]
                    
                    # לוגיקת המטריצה ומנות
                    tranches_bought = math.floor(abs_drop / drop_interval)
                    total_deployed = tranches_bought * tranche_size
                    
                    total_tranches_global += tranches_bought
                    total_money_global += total_deployed
                    
                    next_tranche_num = tranches_bought + 1
                    next_base_drop_target = next_tranche_num * drop_interval
                    next_base_price = base_max * (1 - (next_base_drop_target / 100))
                    
                    # קביעת סטטוס ומומנטום משולב
                    if rsi < 30 and mfi < 30:
                        momentum_status = f"<span style='color: #ef4444; font-weight: bold;'>🔥 מכירת יתר ואיסוף מוסדי מוגבר</span>"
                    elif rsi < 45:
                        momentum_status = f"<span style='color: #f97316; font-weight: bold;'>📉 מומנטום חלש (לחץ מוכרים)</span>"
                    elif rsi < 60:
                        momentum_status = f"<span style='color: #94a3b8;'>⚪ נייטרלי / דשדוש</span>"
                    else:
                        momentum_status = f"<span style='color: #22c55e; font-weight: bold;'>📈 מומנטום חזק (כניסת כסף)</span>"
                    
                    # עיצוב מדד מוסדיים MFI
                    if mfi < 30:
                        mfi_html = f"<span style='color: #34d399; font-weight: bold;'>📥 מוסדיים קונים ({round(mfi)}/100)</span>"
                    elif mfi > 70:
                        mfi_html = f"<span style='color: #f87171; font-weight: bold;'>📤 מוסדיים מוכרים ({round(mfi)}/100)</span>"
                    else:
                        mfi_html = f"<span style='color: #cbd5e1;'>⚪ זרימה מאוזנת ({round(mfi)})</span>"
                    
                    # עיצוב אחוז יומי
                    change_color = "#34d399" if lev_change >= 0 else "#f87171"
                    change_sign = "+" if lev_change > 0 else ""
                    change_html = f"<span style='color: {change_color}; font-weight: 700;'>{change_sign}{round(lev_change, 2)}%</span>"
                    
                    # בדיקת התרעת ברבור שחור בממונף
                    blackswan_html = ""
                    if lev_drop <= -50.0:
                        blackswan_html = f"<br><span class=\"badge-blackswan\">🚨 קריסת קצה ({round(lev_drop)}%)</span>"
                    
                    # בדיקת טריגר לקנייה וקביעת מחלקת עיצוב לשורה
                    distance_to_next = next_base_drop_target - abs_drop
                    if distance_to_next <= 0.5:
                        row_class = "row-trigger"
                        active_triggers_count += 1
                        rec_text = f"<td style='background-color: #78350f; color: #fbbf24; font-weight: bold; text-align: center;'>🚨 פקודה אקטיבית:<br>רכוש מנה {next_tranche_num}!</td>"
                    else:
                        row_class = "row-normal"
                        rec_text = f"<td style='color: #a1a1aa; text-align: center;'>⏳ ממתין למדרגה {next_tranche_num}</td>"
                    
                    table_rows_html += f"""<tr class="{row_class}">
<td>
<span style="font-size: 18px; font-weight: bold; color: #38bdf8;">{pair["name"]}</span>
{blackswan_html}
</td>
<td>
<b style="color: #94a3b8;">בסיס:</b> ${round(base_curr, 2)}<br>
<b style="color: #94a3b8;">ממונף:</b> ${round(lev_curr, 2)}
</td>
<td>{change_html}</td>
<td><span class="badge-drop">{round(base_drop, 1)}%</span></td>
<td><span class="badge-tranche">{tranches_bought} מנות</span></td>
<td><span class="badge-money">${total_deployed:,}</span></td>
<td>
<span style="color: #ffffff; font-weight: bold;">במחיר בסיס:</span><br>
<b style="color: #38bdf8; font-size: 18px;">${round(next_base_price, 2)}</b><br>
<span style="color: #94a3b8; font-size: 13px;">(יעד: {next_base_drop_target}%)</span>
</td>
<td>
<b>טכני:</b> {momentum_status}<br>
<b>זרימה:</b> {mfi_html}
</td>
{rec_text}
</tr>"""
    except Exception as e:
        st.error(f"שגיאה בעיבוד הנתונים הטרמינלי: {e}")

# 6. הצגת כרטיסי סיכום (KPIs) בחלק העליון
st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-title">סה"כ מנות שנאספו במטריצה</div>
        <div class="kpi-value" style="color: #38bdf8;">{total_tranches_global}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">הון מנוצל נוכחי בתיק</div>
        <div class="kpi-value" style="color: #34d399;">${total_money_global:,}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">נכסים באזור טריגר רכישה חם</div>
        <div class="kpi-value" style="color: #fbbf24;">{active_triggers_count} / 4</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 7. הרכבת והזרקת הטבלה המלאה עם בועות הריחוף (Tooltips מבוססי תכונת title)
table_html = f"""
<table class="terminal-table">
<thead>
<tr>
<th title="צמד הנכסים במעקב. כולל נכס הבסיס המודד והנכס הממונף פי 3 שנרכש בפועל.">צמד נכסים</th>
<th title="שערי האמת הנוכחיים של הניירות בשוק באפס שניות דיליי.">שער אמת</th>
<th title="השינוי האחוז באחוזים של הנייר הממונף במהלך יום המסחר הנוכחי.">שינוי יומי ממונף</th>
<th title="המרחק באחוזים של נכס הבסיס מנקודת השיא הגבוהה ביותר שלו ב-6 החודשים האחרונים.">ירידת בסיס משיא</th>
<th title="כמות המנות ההנדסיות שנרכשו עבור נכס זה על פי מדרגות אחוזי הירידה שנקבעו.">⚡ מנות שנרכשו</th>
<th title="סך כל הכסף הדולרי שהושקע בנכס הממונף הספציפי הזה במצטבר.">💰 הון מושקע</th>
<th title="שער המטרה המדויק של נכס הבסיס שבהגעתו חובה לבצע רכישה של המנה הבאה בברוקר.">🎯 טריגר למנה הבאה</th>
<th title="שילוב של מדד RSI (עוצמה יחסית) ומדד MFI (מדד זרימת כסף המשלב נפח מסחר) לזיהוי כניסת כסף מוסדי ומצבי קיצון.">🌡️ מומנטום וזרימת מוסדיים</th>
<th title="הוראת ביצוע החלטית וקרה המבוססת על מתמטיקה טהורה בלבד.">🔮 המלצה לביצוע</th>
</tr>
</thead>
<tbody>
{table_rows_html}
</tbody>
</table>
"""

st.markdown(table_html, unsafe_allow_html=True)

# 8. ספר חוקים הנדסי לקבוצה
st.write("")
st.markdown('### 🛠️ מדריך הפעלה מהיר לקבוצה')

col_guide1, col_guide2 = st.columns(2)

with col_guide1:
    st.markdown("""<div class="playbook-card">
<h4 style="font-size: 19px; color: #38bdf8; margin-bottom: 8px;">📐 בועות ריחוף וזרימת כסף (MFI)</h4>
<p style="font-size: 16px; color: #cbd5e1;">רחף עם העכבר מעל כותרות הטבלה כדי לקבל הסבר טכני על העמודה. עמודת המומנטום משלבת כעת את ה-Money Flow Index כדי לאתר כניסה חשאית של כסף מוסדי גדול.</p>
</div>""", unsafe_allow_html=True)

with col_guide2:
    st.markdown("""<div class="playbook-card" style="border-right-color: #34d399;">
<h4 style="font-size: 19px; color: #34d399; margin-bottom: 8px;">🎯 צביעת שורות והתרעות ברבור</h4>
<p style="font-size: 16px; color: #cbd5e1;">כאשר נכס נכנס לטווח של 0.5% או פחות מטריגר הרכישה שלו, השורה כולה תיצבע ברקע אדום-כתום בוהק. במקרה של קריסת שוק קיצונית בממונף (מעל 50%), תופעל תגית הגנת קצה מיוחדת.</p>
</div>""", unsafe_allow_html=True)
