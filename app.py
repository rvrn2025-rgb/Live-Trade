import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import ta
import math
import xml.etree.ElementTree as ET
from urllib.parse import quote
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת תצורת דף ומערכת
st.set_page_config(page_title="DCA Matrix Terminal", layout="wide", initial_sidebar_state="collapsed")

# רענון אוטומטי מובנה כל 65 שניות
st_autorefresh(interval=65000, key="matrix_live_refresh")

# 2. הזרקת ארכיטקטורת עיצוב נקייה ויוקרתית (Mobile-First & RTL)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');

/* חסימה הרמטית של פסי גלילה אופקיים בכל רבדי המערכת */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main, .block-container, [data-testid="stMain"] {
    background-color: #05070f !important;
    color: #ffffff !important;
    font-family: 'Assistant', sans-serif !important;
    overflow-x: hidden !important; 
    max-width: 100vw !important;
}

/* יישור מימין לשמאל נקי של גוף האפליקציה */
[data-testid="stAppViewContainer"] {
    direction: RTL !important;
    text-align: right !important;
}

h1, h2, h3, h4, h5 { color: #f8fafc !important; font-weight: 800 !important; }

/* תיקון טקסטים - הגדרה ממוקדת ללא פגיעה ברכיבי המערכת */
.stMarkdown p, label { 
    font-size: 16px !important; 
    font-weight: 600 !important; 
    color: #cbd5e1 !important; 
    text-align: right !important;
}

/* לוח פקודות עליון - Action Items */
.action-box {
    background: #0f172a;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 25px;
    text-align: center;
}
.action-alert { border: 2px solid #ef4444; background-color: #450a0a; }

/* כרטיסי אקורדיון מעוצבים כשורות טרמינל */
.streamlit-expanderHeader {
    background-color: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px !important;
    padding: 12px 18px !important;
    font-size: 17px !important;
    color: #38bdf8 !important;
}

/* מד-מתח ויזואלי מותאם אישית */
.progress-bar-container {
    width: 100%;
    background-color: #1e293b;
    border-radius: 6px;
    margin: 8px 0;
    overflow: hidden;
}
.progress-bar-fill {
    height: 10px;
    background: linear-gradient(90deg, #3b82f6, #ef4444);
    transition: width 0.5s ease;
}

/* התאמות קלט */
div[data-testid="stNumberInput"] input {
    text-align: right !important;
    background-color: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
}
</style>""", unsafe_allow_html=True)

# 3. אתחול נכסים והגדרות בסיס
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (FAS)"}
]

# הגדרת פרמטרים בסיסיים (כולל אפשרות הזנה חופשית לאחוזים)
col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
with col_p1:
    tranche_size = st.number_input("💰 תקציב קבוע למנה ($):", min_value=100, max_value=100000, value=3000, step=500)
with col_p2:
    interval_choice = st.selectbox("📐 מרווח ירידה בין מנות:", ["3.5%", "5.0%", "7.0%", "10.0%", "הזן ידנית..."], index=1)
with col_p3:
    if interval_choice == "הזן ידנית...":
        drop_interval = st.number_input("הזן אחוז מרווח אישי:", min_value=0.5, max_value=50.0, value=6.5, step=0.5)
    else:
        drop_interval = float(interval_choice.replace("%", ""))

# 4. פונקציות תשתית ומטמון
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
            for item in root.findall('.//item')[:1]:
                title_en = item.find('title').text
                link = item.find('link').text
                combined_stories.append({"ticker": t, "title": translate_headline(title_en), "link": link})
        except: continue
    return combined_stories

API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
all_tickers = ["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"]
quote_response = get_realtime_quotes(",".join(all_tickers), API_KEY)

# מנוע חישוב ואיסוף נתוני מטריצה
processed_assets = []
any_active_trigger = False
total_portfolio_value = 0
total_portfolio_tranches = 0

if "status" in quote_response and quote_response["status"] == "error":
    st.error("❌ שגיאה זמנית במשיכת נתוני השוק. המערכת תתרענן אוטומטית בעוד דקה.")
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
                
                auto_tranches = math.floor(abs_drop / drop_interval)
                next_tranche_num = auto_tranches + 1
                next_base_drop_target = next_tranche_num * drop_interval
                next_base_price = base_max * (1 - (next_base_drop_target / 100))
                
                distance_to_next = next_base_drop_target - abs_drop
                trigger_active = distance_to_next <= 0.5
                
                if trigger_active:
                    any_active_trigger = True
                
                current_interval_progress = ((abs_drop - (auto_tranches * drop_interval)) / drop_interval) * 100
                current_interval_progress = max(0, min(100, current_interval_progress))
                
                ema_200 = ta.trend.ema_indicator(df_base['Close'], window=200).iloc[-1]
                ema_distance = ((base_curr - ema_200) / ema_200) * 100
                rsi = ta.momentum.rsi(df_base['Close'], window=14).iloc[-1]
                mfi = ta.volume.money_flow_index(df_base['High'], df_base['Low'], df_base['Close'], df_base['Volume'], window=14).iloc[-1]
                
                if f"{lev}_override_active" not in st.session_state:
                    st.session_state[f"{lev}_override_active"] = False
                if f"{lev}_tranches_count" not in st.session_state:
                    st.session_state[f"{lev}_tranches_count"] = auto_tranches
                if f"{lev}_manual_avg" not in st.session_state:
                    st.session_state[f"{lev}_manual_avg"] = 0.0
                
                if not st.session_state[f"{lev}_override_active"]:
                    st.session_state[f"{lev}_tranches_count"] = auto_tranches
                
                processed_assets.append({
                    "pair": pair, "base_curr": base_curr, "lev_curr": lev_curr, "lev_change": lev_change,
                    "base_max": base_max, "base_drop": base_drop, "lev_drop": lev_drop,
                    "auto_tranches": auto_tranches, "next_tranche_num": next_tranche_num,
                    "next_base_price": next_base_price, "next_base_drop_target": next_base_drop_target,
                    "distance_to_next": distance_to_next, "trigger_active": trigger_active,
                    "progress_bar": current_interval_progress, "ema_distance": ema_distance, "rsi": rsi, "mfi": mfi
                })
                
                total_portfolio_tranches += st.session_state[f"{lev}_tranches_count"]
                total_portfolio_value += (st.session_state[f"{lev}_tranches_count"] * tranche_size)

    # 5. קוביות "מה עושים היום?" (Action Items) - מופיע רק כשיש טריגר פעיל באמת
    if any_active_trigger:
        st.markdown("""<div class="action-box action-alert">
            <h3 style="margin:0; color:#ffffff;">🚨 פקודות ביצוע אקטיביות ממתינות לך!</h3>
            <p style="margin:5px 0 0 0; color:#fca5a5; font-size:16px;">אחד או יותר מהנכסים הגיע למדרגת קנייה הנדסית. פתח את הנכסים המסומנים באדום לביצוע.</p>
        </div>""", unsafe_allow_html=True)

    # 6. הצגת כרטיסי הנכסים במבנה אקורדיון נקי ומפוצל
    for asset in processed_assets:
        lev = asset["pair"]["leveraged"]
        base = asset["pair"]["base"]
        name = asset["pair"]["name"]
        
        sign = "+" if asset["lev_change"] > 0 else ""
        status_label = "🔴 טריגר רכישה!" if asset["trigger_active"] else "⏳ ממתין במדרגה"
        title_text = f"{name} | מחיר: ${asset['lev_curr']:.2f} ({sign}{asset['lev_change']:.2f}%) | מצב: {status_label}"
        
        with st.expander(title_text, expanded=asset["trigger_active"]):
            col_right, col_left = st.columns(2)
            
            # --- טור ימין: ניתוח מצב השוק והנדסת מדרגות ---
            with col_right:
                st.markdown("<h4 style='color:#38bdf8; margin-top:0;'>📊 נתוני שוק והנדסה</h4>", unsafe_allow_html=True)
                st.markdown(f"מרחק נוכחי משיא כל הזמנים: **`{asset['base_drop']:.1f}%`**")
                
                st.markdown(f"<p style='font-size:14px; margin-bottom:2px;'>🔋 מד-מתח לקראת מנה {asset['next_tranche_num']} (יעד {asset['next_base_drop_target']}%):</p>", unsafe_allow_html=True)
                st.markdown(f"""<div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width: {asset['progress_bar']}%;"></div>
                </div>""", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size:13px; color:#94a3b8; margin-top:0;'>מרחק לטריגר: {asset['distance_to_next']:.2f}% במדד הבסיס</p>", unsafe_allow_html=True)
                
                shares_to_buy = round(tranche_size / asset['lev_curr'])
                if asset["trigger_active"]:
                    st.error(f"💥 **הוראת ביצוע:** קנה כעת **{shares_to_buy} מניות** של {lev} (שווה ערך ל-${tranche_size:,}) בשער בסיס ${asset['next_base_price']:.2f}")
                else:
                    st.markdown(f"🎯 שער טריגר עתידי לקנייה: **${asset['next_base_price']:.2f}** (בנכס {base})")
                
                with st.expander("🔬 מדדים טכניים וזרימת הון"):
                    st.write(f"• מרחק ממוצע נע 200 השנתי: {asset['ema_distance']:.1f}%")
                    st.write(f"• מדד עוצמה יחסית RSI: {asset['rsi']:.0f}")
                    st.write(f"• זרם הון מוסדי MFI: {asset['mfi']:.0f}")

            # --- טור שמאל: ניהול תיק אישי ומפת פקודות מכירה (Take Profit) ---
            with col_left:
                st.markdown("<h4 style='color:#34d399; margin-top:0;'>💼 הפוזיציה והשחרורים שלך</h4>", unsafe_allow_html=True)
                
                c_input1, c_input2 = st.columns(2)
                with c_input1:
                    active_t = st.number_input("מנות בתיק:", min_value=0, max_value=20, value=int(st.session_state[f"{lev}_tranches_count"]), key=f"{lev}_input_t")
                with c_input2:
                    avg_c = st.number_input("מחיר ממוצע ($):", min_value=0.0, value=float(st.session_state[f"{lev}_manual_avg"]), key=f"{lev}_input_a", step=0.5)
                
                if active_t != st.session_state[f"{lev}_tranches_count"] or avg_c != st.session_state[f"{lev}_manual_avg"]:
                    st.session_state[f"{lev}_override_active"] = True
                    st.session_state[f"{lev}_tranches_count"] = active_t
                    st.session_state[f"{lev}_manual_avg"] = avg_c
                
                if st.session_state[f"{lev}_override_active"]:
                    st.markdown("<p style='color:#fbbf24; font-size:13px; margin:0;'>⚠️ מצב עריכה ידנית פעיל</p>", unsafe_allow_html=True)
                    if st.button("🔄 חזור לסנכרון אוטומטי מלא", key=f"{lev}_reset_btn"):
                        st.session_state[f"{lev}_override_active"] = False
                        st.session_state[f"{lev}_tranches_count"] = asset["auto_tranches"]
                        st.session_state[f"{lev}_manual_avg"] = 0.0
                        st.rerun()
                
                st.markdown("---")
                
                current_active_tranches = st.session_state[f"{lev}_tranches_count"]
                if current_active_tranches > 0:
                    st.markdown("<h5 style='color:#fbbf24; margin-bottom:10px;'>🎯 מפת פקודות מכירה עתידיות (Take Profit Matrix)</h5>", unsafe_allow_html=True)
                    
                    reference_price = st.session_state[f"{lev}_manual_avg"] if st.session_state[f"{lev}_manual_avg"] > 0 else asset["lev_curr"]
                    
                    if current_active_tranches == 1: steps, label = [11, 22, 33], "שלישים"
                    elif current_active_tranches == 2: steps, label = [10, 20, 30, 40], "רבעים"
                    elif current_active_tranches == 3: steps, label = [10, 20, 30, 40, 50, 60], "שישיות"
                    elif current_active_tranches == 4: steps, label = [10, 20, 30, 40, 50, 60, 70, 80], "שמיניות"
                    else: steps, label = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], "עשיריות"
                    
                    total_shares_owned = round((current_active_tranches * tranche_size) / reference_price)
                    shares_per_step = max(1, round(total_shares_owned / len(steps)))
                    
                    st.markdown(f"<p style='font-size:13px; color:#94a3b8;'>חלוקה מומלצת לפי כמות מנות: <b>{label}</b> (כ-{shares_per_step} מניות ליעד)</p>", unsafe_allow_html=True)
                    
                    for i, step in enumerate(steps):
                        target_price = reference_price * (1 + step / 100)
                        st.markdown(f"📍 **יעד {i+1} (+{step}%):** למכור **{shares_per_step} מניות** בשער **`${target_price:.2f}`**")
                else:
                    st.markdown("<span style='color:#94a3b8; font-size:14px;'>אין מנות פעילות בתיק כרגע. יעדי המכירה יופיעו כאן אוטומטית.</span>", unsafe_allow_html=True)

# 7. סרגל צדי לסיכום הון כולל
st.sidebar.markdown("### 📊 סיכום הון במטריצה")
st.sidebar.metric("סה\"כ מנות בתיק", total_portfolio_tranches)
st.sidebar.metric("הון מנוצל כולל", f"${total_portfolio_value:,}")

# 8. פיד חדשות מאקרו מתורגם וממוקד
ticker_news_list = fetch_ticker_news(["QQQ", "SOXX", "SPY", "XLF"])
if ticker_news_list:
    st.markdown("### 📰 מבזקי מאקרו רלוונטיים (סינון פאניקה)")
    for story in ticker_news_list:
        st.markdown(f"• **{story['ticker']}**: [{story['title']}]({story['link']})")
