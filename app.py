import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import ta
import math
import xml.etree.ElementTree as ET
from urllib.parse import quote
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת תצורת דף ומערכת (חובה להיות הפקודה הראשונה)
st.set_page_config(page_title="DCA Matrix Terminal", layout="wide", initial_sidebar_state="collapsed")

# רענון אוטומטי מובנה כל 65 שניות
st_autorefresh(interval=65000, key="matrix_live_refresh")

# 2. עיצוב מינימליסטי ו-RTL מובנה
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #05070f !important;
    color: #ffffff !important;
    font-family: 'Assistant', sans-serif !important;
    direction: RTL !important;
    text-align: right !important;
}

h1, h2, h3, h4, h5 { color: #f8fafc !important; font-weight: 800 !important; }

/* עיצוב כרטיסי סיכום (KPI) */
div[data-testid="metric-container"] {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 15px;
    text-align: center;
}

/* עיצוב אקורדיון (Expander) כדי שייראה כמו כרטיס יוקרתי */
.streamlit-expanderHeader {
    background-color: #1e293b !important;
    border-radius: 8px !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #38bdf8 !important;
}

/* תיקון כיווניות של שדות קלט מובנים */
div[data-testid="stNumberInput"] input {
    text-align: right !important;
    background-color: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
}

/* עיצוב תיבת החדשות */
.news-container { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; margin-top: 30px; }
.news-title { color: #38bdf8; font-weight: 800; font-size: 20px; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; }
.news-item { margin-bottom: 12px; font-size: 15px; border-bottom: 1px dashed #1e293b; padding-bottom: 8px; }
.news-tag { background: #1e293b; color: #34d399; font-weight: bold; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 8px; }
.news-item a { color: #cbd5e1; text-decoration: none; }
.news-item a:hover { color: #38bdf8; }
</style>""", unsafe_allow_html=True)

# 3. ניהול State פרטי לכל משתמש
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "נאסד\"ק"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "שבבים"},
    {"base": "SPY", "leveraged": "UPRO", "name": "S&P 500"},
    {"base": "XLF", "leveraged": "FAS", "name": "פיננסים"}
]

for pair in asset_pairs:
    lev = pair["leveraged"]
    if f"{lev}_avg_cost" not in st.session_state:
        st.session_state[f"{lev}_avg_cost"] = 0.0
    if f"{lev}_tranches" not in st.session_state:
        st.session_state[f"{lev}_tranches"] = 0

# 4. פונקציות תשתית (API וחישובים)
@st.cache_data(ttl=60)
def get_realtime_quotes(symbols_string, api_key):
    url = f"https://api.twelvedata.com/quote?symbol={symbols_string}&apikey={api_key}"
    try: return requests.get(url).json()
    except: return {}

@st.cache_data(ttl=900)
def get_historical_data(symbol):
    return yf.Ticker(symbol).history(period="max", auto_adjust=False)

@st.cache_data(ttl=3600)
def translate_headline(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=he&dt=t&q={quote(text)}"
        res = requests.get(url, timeout=4).json()
        return "".join([part[0] for part in res[0] if part[0]])
    except: return text

@st.cache_data(ttl=600)
def fetch_ticker_news(tickers_list):
    combined_stories = []
    for t in tickers_list:
        try:
            url = f"https://feeds.finance.yahoo.com/rss.2.0/headline?s={t}"
            res = requests.get(url, timeout=4)
            root = ET.fromstring(res.content)
            for item in root.findall('.//item')[:2]:
                title_en = item.find('title').text
                link = item.find('link').text
                combined_stories.append({"ticker": t, "title": translate_headline(title_en), "link": link})
        except: continue
    return combined_stories

# --- בניית ה-UI הראשי ---
st.markdown('<h1 style="text-align: center; color: #38bdf8;">⚡ מסוף DCA וניהול פוזיציות</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8; margin-bottom: 30px;">מרחב עבודה נקי ומבודד אישית</p>', unsafe_allow_html=True)

# הגדרות כלליות בראש העמוד (מוסתר באקורדיון כדי לשמור על ניקיון)
with st.expander("⚙️ הגדרות אסטרטגיה בסיסיות (לחץ לעריכה)"):
    col_param1, col_param2 = st.columns(2)
    with col_param1:
        tranche_size = st.number_input("💰 גודל מנה לרכישה ($):", min_value=100, max_value=100000, value=3000, step=500)
    with col_param2:
        drop_interval = st.selectbox("📐 מרווח ירידה בין מנות (%):", [3.5, 5.0, 7.0, 10.0], index=0)

# הבאת נתונים
API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
all_tickers = ["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"]
quote_response = get_realtime_quotes(",".join(all_tickers), API_KEY)

total_money_global = 0
total_tranches_global = 0
active_triggers_count = 0
cards_data = []

# חישוב נתונים לכל נכס לפני הצגה
if "status" in quote_response and quote_response["status"] == "error":
    st.error("❌ שגיאת API. הנתונים לא זמינים כרגע.")
else:
    for pair in asset_pairs:
        base = pair["base"]
        lev = pair["leveraged"]
        
        base_quote = quote_response.get(base, {})
        lev_quote = quote_response.get(lev, {})
        
        if "close" in base_quote or "price" in base_quote:
            base_curr = float(base_quote.get("price", base_quote.get("close", 0)))
            lev_curr = float(lev_quote.get("price", lev_quote.get("close", 0)))
            lev_change = float(lev_quote.get("percent_change", 0))
            
            df_base = get_historical_data(base).copy()
            df_lev = get_historical_data(lev).copy()
            
            if len(df_base) > 200 and len(df_lev) > 14:
                df_base.loc[df_base.index[-1], 'Close'] = base_curr
                base_max = df_base['High'].max()
                lev_max = df_lev['High'].max()
                
                base_drop = ((base_curr - base_max) / base_max) * 100
                abs_drop = abs(base_drop)
                lev_drop = ((lev_curr - lev_max) / lev_max) * 100
                
                ema_200 = ta.trend.ema_indicator(df_base['Close'], window=200).iloc[-1]
                ema_distance = ((base_curr - ema_200) / ema_200) * 100
                rsi = ta.momentum.rsi(df_base['Close'], window=14).iloc[-1]
                mfi = ta.volume.money_flow_index(df_base['High'], df_base['Low'], df_base['Close'], df_base['Volume'], window=14).iloc[-1]
                
                auto_tranches = math.floor(abs_drop / drop_interval)
                next_tranche_num = auto_tranches + 1
                next_base_drop_target = next_tranche_num * drop_interval
                next_base_price = base_max * (1 - (next_base_drop_target / 100))
                
                distance_to_next = next_base_drop_target - abs_drop
                trigger_active = distance_to_next <= 0.5
                
                if trigger_active:
                    active_triggers_count += 1
                
                user_tranches = st.session_state[f"{lev}_tranches"]
                total_tranches_global += user_tranches
                total_money_global += (user_tranches * tranche_size)
                
                cards_data.append({
                    "pair": pair, "base_curr": base_curr, "lev_curr": lev_curr, "lev_change": lev_change,
                    "base_drop": base_drop, "lev_drop": lev_drop, "ema_distance": ema_distance, "rsi": rsi, "mfi": mfi,
                    "next_base_price": next_base_price, "next_base_drop_target": next_base_drop_target,
                    "trigger_active": trigger_active
                })

    # שורת מדדים (KPIs)
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("סה\"כ מנות פעילות בתיק", total_tranches_global)
    kpi2.metric("שווי תיק מושקע מחושב", f"${total_money_global:,}")
    kpi3.metric("טריגרים אקטיביים לקנייה", f"{active_triggers_count} / 4")
    
    st.markdown("---")
    st.markdown("### 📊 רשימת נכסים (לחץ על נכס לפתיחת ניהול פוזיציה)")

    # רינדור כרטיסי הנכסים (האקורדיונים)
    for data in cards_data:
        lev = data["pair"]["leveraged"]
        base = data["pair"]["base"]
        name = data["pair"]["name"]
        
        # כותרת האקורדיון - נקייה וברורה
        change_sign = "+" if data["lev_change"] > 0 else ""
        status_icon = "🚨 קנייה אקטיבית!" if data["trigger_active"] else "⏳ ממתין"
        expander_title = f"{name} ({lev}/{base}) | שער: ${data['lev_curr']:.2f} ({change_sign}{data['lev_change']:.2f}%) | סטטוס: {status_icon}"
        
        with st.expander(expander_title, expanded=data["trigger_active"]):
            # חלוקה ל-2 טורים בתוך הכרטיס
            col_market, col_portfolio = st.columns(2)
            
            # --- טור ימין: שוק והנדסה ---
            with col_market:
                st.markdown(f"<h4 style='color:#38bdf8;'>מצב השוק ({base})</h4>", unsafe_allow_html=True)
                st.write(f"**מרחק משיא כל הזמנים (ATH):** {data['base_drop']:.2f}%")
                
                if data["trigger_active"]:
                    st.error(f"🎯 **טריגר קנייה!** שער הבסיס הגיע ליעד. מחיר קנייה מומלץ לבסיס: ${data['next_base_price']:.2f}")
                else:
                    st.info(f"📍 **יעד המדרגה הבאה:** מתחת ל-{data['next_base_drop_target']}% (שער ${data['next_base_price']:.2f})")
                
                if data["lev_drop"] <= -50.0:
                    st.warning(f"⚠️ **קריסת קצה בממונף:** הנייר איבד {abs(data['lev_drop']):.1f}% משיאו.")
                
                # הרעש הטכני מוסתר פה
                with st.expander("🛠️ נתונים טכניים (RSI, MFI, EMA)"):
                    st.write(f"**מרחק ממוצע נע 200:** {data['ema_distance']:.1f}%")
                    st.write(f"**מומנטום RSI:** {data['rsi']:.0f}")
                    st.write(f"**זרם כסף מוסדי MFI:** {data['mfi']:.0f}")
            
            # --- טור שמאל: התיק ויעדי השחרור ---
            with col_portfolio:
                st.markdown(f"<h4 style='color:#34d399;'>ניהול פוזיציה ({lev})</h4>", unsafe_allow_html=True)
                
                # שדות הזנה
                user_tranches = st.number_input("מנות פעילות בידיים שלי:", min_value=0, max_value=20, value=int(st.session_state[f"{lev}_tranches"]), key=f"{lev}_input_tranches", step=1)
                user_avg = st.number_input("מחיר קנייה ממוצע ($):", min_value=0.0, value=float(st.session_state[f"{lev}_avg_cost"]), key=f"{lev}_input_avg", step=0.1)
                
                st.session_state[f"{lev}_tranches"] = user_tranches
                st.session_state[f"{lev}_avg_cost"] = user_avg
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # בניית מפת שחרור בצורה נקייה וישירה
                if user_tranches > 0:
                    st.markdown(f"<h5 style='color:#fbbf24; border-bottom:1px solid #334155; padding-bottom:5px;'>🎯 מפת יעדי מכירה (Take Profit)</h5>", unsafe_allow_html=True)
                    
                    ref_price = user_avg if user_avg > 0 else data["lev_curr"]
                    
                    if user_tranches == 1: steps = [11, 22, 33]
                    elif user_tranches == 2: steps = [10, 20, 30, 40]
                    elif user_tranches == 3: steps = [10, 20, 30, 40, 50, 60]
                    elif user_tranches == 4: steps = [10, 20, 30, 40, 50, 60, 70, 80]
                    else: steps = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
                    
                    # רשימת היעדים
                    for i, step in enumerate(steps):
                        target_price = ref_price * (1 + step / 100)
                        st.markdown(f"**יעד {i+1} (+{step}%):** למכור בשער **`${target_price:.2f}`**")
                else:
                    st.markdown("<span style='color:#94a3b8; font-size:14px;'>הזן מנות פעילות כדי לראות את מפת יעדי המכירה.</span>", unsafe_allow_html=True)

# 6. פיד חדשות מתורגם למטה
ticker_news_list = fetch_ticker_news(["QQQ", "SOXX", "SPY", "XLF"])
if ticker_news_list:
    news_html = """<div class="news-container">
    <div class="news-title">📰 מבזקי מאקרו (מתורגם לעברית)</div>"""
    for story in ticker_news_list:
        news_html += f"""<div class="news-item">
            <span class="news-tag">{story['ticker']}</span>
            <a href="{story['link']}" target="_blank">{story['title']}</a>
        </div>"""
    news_html += "</div>"
    st.markdown(news_html, unsafe_allow_html=True)
