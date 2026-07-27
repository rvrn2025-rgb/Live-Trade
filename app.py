import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import ta
import math
import xml.etree.ElementTree as ET
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת תצורת דף 
st.set_page_config(page_title="DCA Matrix // Ultimate Terminal", layout="wide")

# רענון אוטומטי כל 65 שניות
st_autorefresh(interval=65000, key="matrix_refresh")

# 2. הזרקת עיצוב קסטום נקי ומתקדם
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #05070f !important;
    color: #ffffff !important;
    font-family: 'Assistant', sans-serif !important;
    direction: RTL !important;
    text-align: right !important;
}

h1, h2, h3, h4 { color: #ffffff !important; font-weight: 800 !important; }
label, p, span { font-size: 18px !important; font-weight: 600 !important; color: #f1f5f9 !important; }
input { font-size: 18px !important; font-weight: 700 !important; }

/* כרטיסי סיכום עליונים */
.kpi-container { display: flex; gap: 20px; margin-bottom: 25px; }
.kpi-card { flex: 1; background: #0f172a; border: 2px solid #1e293b; border-radius: 8px; padding: 15px; text-align: center; }
.kpi-title { font-size: 14px !important; color: #94a3b8 !important; margin-bottom: 5px; }
.kpi-value { font-size: 24px !important; font-weight: 800 !important; color: #38bdf8; }

/* עיצוב הטבלה */
.terminal-table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 17px; background-color: #0b0f19; border: 2px solid #1e293b; border-radius: 8px; overflow: hidden; }
.terminal-table th { background-color: #1e293b; color: #38bdf8; font-size: 16px; font-weight: 800; padding: 14px; text-align: right; border-bottom: 3px solid #334155; cursor: help; }
.terminal-table td { padding: 14px; border-bottom: 1px solid #1e293b; color: #ffffff; vertical-align: middle; }

/* שורות */
.row-trigger { background-color: #2d1510 !important; border-right: 6px solid #ef4444 !important; }
.row-normal:hover { background-color: #111827; }

/* תגיות */
.badge-drop { background-color: #7f1d1d; color: #fca5a5; padding: 4px 8px; border-radius: 6px; font-weight: 700; }
.badge-blackswan { background-color: #450a0a; color: #f87171; border: 1px solid #ef4444; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: 700; display: inline-block; margin-top: 4px; cursor: help; }
.badge-tranche { background-color: #1e3a8a; color: #93c5fd; padding: 4px 8px; border-radius: 6px; font-weight: 700; }
.badge-money { color: #34d399; font-weight: 700; }

/* חדשות */
.news-container { background: #0f172a; border: 2px solid #1e293b; border-radius: 8px; padding: 20px; margin-top: 30px; }
.news-title { cursor: help; color: #38bdf8; font-weight: 800; font-size: 22px; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; }
.news-item { margin-bottom: 10px; }
.news-item a { color: #cbd5e1; text-decoration: none; font-size: 16px; transition: 0.2s; }
.news-item a:hover { color: #38bdf8; }
</style>""", unsafe_allow_html=True)

# 3. כותרת הטרמינל
st.markdown('<h1 style="text-align: center; color: #38bdf8; font-size: 36px; margin-bottom: 5px;">⚡ טבלת מעקב ממונפות וליבה</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 20px; margin-bottom: 30px;">מערכת אלגוריתמית מתקדמת לניהול מנות איסוף ומיצוע הנדסי (DCA) ללא רגש</p>', unsafe_allow_html=True)

# 4. לוח בקרה
col_param1, col_param2, col_param3 = st.columns(3)
with col_param1:
    tranche_size = st.number_input("💰 גודל מנה קבועה לרכישה ($):", min_value=100, max_value=100000, value=3000, step=500)
with col_param2:
    drop_interval = st.selectbox("📐 מרווח ירידת הבסיס בין מנות (%):", [3.5, 5.0, 7.0, 10.0], index=0)
with col_param3:
    st.write("")
    st.write("")
    st.markdown("<p style='color: #34d399; font-weight: 800; text-align: center; font-size: 20px; margin-top: 5px;'>🟢 שערי אמת מסונכרנים בלייב</p>", unsafe_allow_html=True)

# 5. פונקציות משיכת נתונים מטמון
@st.cache_data(ttl=60)
def get_realtime_quotes(symbols_string, api_key):
    url = f"https://api.twelvedata.com/quote?symbol={symbols_string}&apikey={api_key}"
    try: return requests.get(url).json()
    except Exception as e: return {"status": "error", "message": str(e)}

@st.cache_data(ttl=900) # מטמון ל-15 דקות להיסטוריה ארוכה (מונע איטיות)
def get_historical_data(symbol):
    return yf.Ticker(symbol).history(period="max", auto_adjust=False)

@st.cache_data(ttl=600) # משיכת חדשות כל 10 דקות
def fetch_rss_news():
    try:
        url = "http://www.ynet.co.il/Integration/StoryRss6.xml" # Ynet כלכלה
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        root = ET.fromstring(res.content)
        return [{"title": item.find('title').text, "link": item.find('link').text} for item in root.findall('.//item')[:6]]
    except: return []

# הגדרת נכסים
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (QQQ/TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXX/SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (SPY/UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (XLF/FAS)"}
]

API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
symbols_str = ",".join(["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"])
quote_response = get_realtime_quotes(symbols_str, API_KEY)

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
                base_curr = float(base_quote.get("price", base_quote.get("close", 0)))
                lev_curr = float(lev_quote.get("price", lev_quote.get("close", 0)))
                lev_change = float(lev_quote.get("percent_change", 0))
                
                # משיכת היסטוריה (מאז ההנפקה - max)
                df_base = get_historical_data(pair["base"]).copy()
                df_lev = get_historical_data(pair["leveraged"]).copy()
                
                if len(df_base) > 200 and len(df_lev) > 14:
                    # הזרקת מחיר נוכחי לחישוב אינדיקטורים מדויק
                    df_base.loc[df_base.index[-1], 'Close'] = base_curr
                    if base_curr > df_base['High'].iloc[-1]: df_base.loc[df_base.index[-1], 'High'] = base_curr
                    if base_curr < df_base['Low'].iloc[-1]: df_base.loc[df_base.index[-1], 'Low'] = base_curr
                    
                    # שיא כללי מיום ההנפקה (ATH)
                    base_max = df_base['High'].max()
                    lev_max = df_lev['High'].max()
                    
                    base_drop = ((base_curr - base_max) / base_max) * 100
                    abs_drop = abs(base_drop)
                    lev_drop = ((lev_curr - lev_max) / lev_max) * 100
                    
                    # חישוב EMA 200 ומרחק
                    ema_200 = ta.trend.ema_indicator(df_base['Close'], window=200).iloc[-1]
                    ema_distance = ((base_curr - ema_200) / ema_200) * 100
                    
                    # אינדיקטורים (RSI ו-MFI)
                    rsi = ta.momentum.rsi(df_base['Close'], window=14).iloc[-1]
                    mfi = ta.volume.money_flow_index(df_base['High'], df_base['Low'], df_base['Close'], df_base['Volume'], window=14).iloc[-1]
                    
                    tranches_bought = math.floor(abs_drop / drop_interval)
                    total_deployed = tranches_bought * tranche_size
                    total_tranches_global += tranches_bought
                    total_money_global += total_deployed
                    
                    next_tranche_num = tranches_bought + 1
                    next_base_drop_target = next_tranche_num * drop_interval
                    next_base_price = base_max * (1 - (next_base_drop_target / 100))
                    
                    # עיצוב מוסדיים עם בועות ריחוף
                    if mfi < 30:
                        mfi_tooltip = "איסוף מוסדי חם: כסף גדול מנצל את הירידות כדי לקנות כמויות ענק של סחורה בזול בזמן שהציבור בורח."
                        mfi_html = f"<span title='{mfi_tooltip}' style='color: #34d399; font-weight: bold; cursor: help;'>📥 מוסדיים קונים ({round(mfi)})</span>"
                        mfi_bullish = True
                    elif mfi > 70:
                        mfi_tooltip = "סיכון גבוה: כסף חכם מממש רווחים ומוכר את הסחורה לציבור בשיא."
                        mfi_html = f"<span title='{mfi_tooltip}' style='color: #f87171; font-weight: bold; cursor: help;'>📤 מוסדיים מוכרים ({round(mfi)})</span>"
                        mfi_bullish = False
                    else:
                        mfi_tooltip = "פעילות שוק רגילה ונייטרלית. אין כניסה או יציאה חריגה של גופים מוסדיים."
                        mfi_html = f"<span title='{mfi_tooltip}' style='color: #cbd5e1; cursor: help;'>⚪ זרימה מאוזנת ({round(mfi)})</span>"
                        mfi_bullish = False
                        
                    # עיצוב מרחק מ-EMA 200
                    if ema_distance < 0:
                        ema_html = f"<span style='color: #34d399; font-weight: bold;'>מתחת לממוצע ({round(ema_distance, 1)}%)</span>"
                    else:
                        ema_html = f"<span style='color: #f87171;'>מעל הממוצע ({round(ema_distance, 1)}%)</span>"
                    
                    change_color = "#34d399" if lev_change >= 0 else "#f87171"
                    change_sign = "+" if lev_change > 0 else ""
                    change_html = f"<span style='color: {change_color}; font-weight: 700;'>{change_sign}{round(lev_change, 2)}%</span>"
                    
                    blackswan_html = ""
                    if lev_drop <= -50.0:
                        bs_tooltip = "אזהרת תנודתיות קצה: הנייר הממונף איבד מעל 50% מהשיא הכולל שלו (ATH) אי פעם. זו נקודת כניסה היסטורית אך ברמת סיכון ותנודתיות עצומה."
                        blackswan_html = f"<br><span class=\"badge-blackswan\" title='{bs_tooltip}'>🚨 קריסת קצה ({round(lev_drop)}%)</span>"
                    
                    # בדיקת טריגר ולוגיקת הצטלבות (Confluence)
                    distance_to_next = next_base_drop_target - abs_drop
                    trigger_active = distance_to_next <= 0.5
                    
                    if trigger_active:
                        row_class = "row-trigger"
                        active_triggers_count += 1
                        
                        # דירוג מטריצת העל
                        if (rsi < 35) and mfi_bullish and (ema_distance < 0):
                            matrix_grade = "<div style='margin-top: 8px; font-size: 15px; color: #d946ef; font-weight: 800; background: #4a044e; padding: 4px; border-radius: 4px;'>🎯 איתות זהב: הצטלבות מושלמת!</div>"
                        elif (rsi < 40) or mfi_bullish:
                            matrix_grade = "<div style='margin-top: 8px; font-size: 14px; color: #fbbf24; font-weight: 700;'>🔥 איתות חזק (מומנטום תומך)</div>"
                        else:
                            matrix_grade = "<div style='margin-top: 8px; font-size: 14px; color: #f8fafc;'>✅ מדרגה הנדסית רגילה</div>"
                            
                        rec_text = f"<td style='background-color: #78350f; color: #fbbf24; font-weight: bold; text-align: center;'>🚨 פקודה אקטיבית:<br>רכוש מנה {next_tranche_num}!{matrix_grade}</td>"
                    else:
                        row_class = "row-normal"
                        rec_text = f"<td style='color: #a1a1aa; text-align: center;'>⏳ ממתין למדרגה {next_tranche_num}<br><span style='font-size: 12px;'>מרחק לטריגר: {round(distance_to_next, 2)}%</span></td>"
                    
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
<span title="מדד המגמה המוסדי: ממוצע 200 מייצג את מחיר האיזון. אם המחיר תחתיו, אנו נמצאים בסייל (הנחה) עמוק."><b>EMA 200:</b> {ema_html}</span><br>
<b>מוסדיים:</b> {mfi_html}
</td>
{rec_text}
</tr>"""
    except Exception as e:
        st.error(f"שגיאה בעיבוד הנתונים הטרמינלי: {e}")

# 6. הצגת כרטיסי סיכום העליונים (KPIs)
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
        <div class="kpi-title">נכסים באזור רכישה חם</div>
        <div class="kpi-value" style="color: #fbbf24;">{active_triggers_count} / 4</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 7. הרכבת הטבלה עם בועות הסבר מקצועיות בכותרות
table_html = f"""
<table class="terminal-table">
<thead>
<tr>
<th title="צמד הנכסים במעקב. כולל נכס הבסיס המודד והנכס הממונף פי 3.">צמד נכסים</th>
<th title="שערי האמת הנוכחיים של הניירות בשוק באפס שניות דיליי.">שער אמת</th>
<th title="השינוי האחוז היומי הנוכחי של הנייר הממונף (Real-Time).">שינוי יומי (ממונף)</th>
<th title="המרחק של נכס הבסיס מנקודת השיא הכוללת (ATH) מאז שהונפק.">ירידה מהשיא (ATH)</th>
<th title="כמות המנות שנרכשו עבור נכס זה על פי מדרגות אחוזי הירידה שנקבעו.">⚡ מנות שנרכשו</th>
<th title="סך כל הכסף הדולרי שהושקע בנכס הממונף במצטבר.">💰 הון מושקע</th>
<th title="שער המטרה המדויק של נכס הבסיס שבהגעתו חובה לבצע רכישה.">🎯 טריגר למנה הבאה</th>
<th title="הצטלבות של זרימת כסף מוסדי (MFI) והמרחק מקו המגמה ארוך הטווח (EMA 200).">🌡️ תמיכה מוסדית וטכנית</th>
<th title="הוראת ביצוע החלטית המשלבת מתמטיקה ואיתותי עוצמה.">🔮 ציון מטריצה וביצוע</th>
</tr>
</thead>
<tbody>
{table_rows_html}
</tbody>
</table>
"""
st.markdown(table_html, unsafe_allow_html=True)

# 8. פיד חדשות כלכליות בלייב עם בועת הסבר מנטלית
news_items = fetch_rss_news()
if news_items:
    news_html = """<div class="news-container">
    <div class="news-title" title="איך לקרוא את החדשות? למשקיע DCA ממונף, חדשות רעות, כותרות אדומות ופאניקה בציבור הן סימן חיובי שמייצר הזדמנויות קנייה במחירי רצפה לפי המטריצה.">
    📰 מבזקי מאקרו (Ynet כלכלה) - רחף מעליי להסבר מנטלי
    </div>"""
    for item in news_items:
        news_html += f'<div class="news-item">🔹 <a href="{item["link"]}" target="_blank">{item["title"]}</a></div>'
    news_html += "</div>"
    st.markdown(news_html, unsafe_allow_html=True)
