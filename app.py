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
st.set_page_config(page_title="DCA Matrix Terminal", layout="wide")

# רענון אוטומטי מובנה כל 65 שניות
st_autorefresh(interval=65000, key="matrix_live_refresh")

# 2. הזרקת ארכיטקטורת עיצוב (מחשב + סלולר)
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
label, p, span { font-size: 16px !important; font-weight: 600 !important; color: #f1f5f9 !important; }

/* כרטיסי סיכום עליונים */
.kpi-container { display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 25px; }
.kpi-card { flex: 1; min-width: 220px; background: #0f172a; border: 2px solid #1e293b; border-radius: 8px; padding: 15px; text-align: center; }
.kpi-title { font-size: 14px !important; color: #94a3b8 !important; margin-bottom: 5px; }
.kpi-value { font-size: 24px !important; font-weight: 800 !important; color: #38bdf8; }

/* קוביות נכסים בסגנון טרמינל מתקדם (במקום טבלה חתוכה במובייל) */
.asset-row-card {
    background: #0b0f19;
    border: 2px solid #1e293b;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 15px;
    transition: 0.2s;
}
.asset-row-card.trigger-active {
    border-right: 6px solid #ef4444 !important;
    background: #2d1510;
}

/* תגיות עיצוב */
.badge-drop { background-color: #7f1d1d; color: #fca5a5; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 14px; }
.badge-tranche { background-color: #1e3a8a; color: #93c5fd; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 14px; }
.badge-blackswan { background-color: #450a0a; color: #f87171; border: 1px solid #ef4444; padding: 4px 8px; border-radius: 6px; font-size: 13px; font-weight: 700; display: inline-block; }

/* תיבת חדשות */
.news-container { background: #0f172a; border: 2px solid #1e293b; border-radius: 8px; padding: 20px; margin-top: 30px; }
.news-title { color: #38bdf8; font-weight: 800; font-size: 20px; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; }
.news-item { margin-bottom: 12px; font-size: 15px; border-bottom: 1px dashed #1e293b; padding-bottom: 8px; }
.news-tag { background: #1e293b; color: #38bdf8; font-weight: bold; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 8px; }
.news-item a { color: #cbd5e1; text-decoration: none; }
.news-item a:hover { color: #38bdf8; }

/* תיקון כיווניות של שדות קלט מובנים */
div[data-testid="stNumberInput"] input {
    text-align: right !important;
    background-color: #1e293b !important;
    color: #ffffff !important;
}
</style>""", unsafe_allow_html=True)

# 3. כותרת עליונה והגדרות יסוד
st.markdown('<h1 style="text-align: center; color: #38bdf8; font-size: 32px; margin-bottom: 5px;">⚡ טבלת מעקב ממונפות וניהול פוזיציה</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 17px; margin-bottom: 25px;">מערכת אישית ומבודדת לכל משתמש – נתונים אינם שיתופיים ונשמרים רק בדפדפן שלך</p>', unsafe_allow_html=True)

# אתחול State פרטי למשתמש עבור התיק שלו במידה ולא קיים
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (QQQ/TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXX/SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (SPY/UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (XLF/FAS)"}
]

for pair in asset_pairs:
    lev = pair["leveraged"]
    if f"{lev}_avg_cost" not in st.session_state:
        st.session_state[f"{lev}_avg_cost"] = 0.0
    if f"{lev}_tranches" not in st.session_state:
        st.session_state[f"{lev}_tranches"] = 0

# הגדרות כלליות
col_param1, col_param2 = st.columns(2)
with col_param1:
    tranche_size = st.number_input("💰 גודל מנה קבועה לרכישה ($):", min_value=100, max_value=100000, value=3000, step=500)
with col_param2:
    drop_interval = st.selectbox("📐 מרווח ירידת הבסיס בין מנות (%):", [3.5, 5.0, 7.0, 10.0], index=0)

# 4. פונקציות תשתית ומטמון לנתונים
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

API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
all_tickers = ["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"]
quote_response = get_realtime_quotes(",".join(all_tickers), API_KEY)

# מונים גלובליים לתצוגה
total_money_global = 0
total_tranches_global = 0
active_triggers_count = 0

st.markdown("---")

if "status" in quote_response and quote_response["status"] == "error":
    st.error("❌ שגיאת מכסת API מצד ספק הנתונים. המערכת תתעדכן מחדש בעוד דקה.")
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
                
                # מתנדים וממוצע נע
                ema_200 = ta.trend.ema_indicator(df_base['Close'], window=200).iloc[-1]
                ema_distance = ((base_curr - ema_200) / ema_200) * 100
                rsi = ta.momentum.rsi(df_base['Close'], window=14).iloc[-1]
                mfi = ta.volume.money_flow_index(df_base['High'], df_base['Low'], df_base['Close'], df_base['Volume'], window=14).iloc[-1]
                
                # חישוב מנוע הנדסי אוטומטי (לצד הזנת משתמש)
                auto_tranches = math.floor(abs_drop / drop_interval)
                next_tranche_num = auto_tranches + 1
                next_base_drop_target = next_tranche_num * drop_interval
                next_base_price = base_max * (1 - (next_base_drop_target / 100))
                
                distance_to_next = next_base_drop_target - abs_drop
                trigger_active = distance_to_next <= 0.5
                
                if trigger_active:
                    active_triggers_count += 1
                    card_class = "asset-row-card trigger-active"
                else:
                    card_class = "asset-row-card"
                
                # --- תחילת בניית שורת נכס דינמית ---
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                
                # חלוקה לעמודות פונקציונליות
                col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.3, 1.3])
                
                with col1:
                    st.markdown(f'<span style="font-size: 19px; font-weight: 800; color: #38bdf8;">{pair["name"]}</span>', unsafe_allow_html=True)
                    change_color = "#34d399" if lev_change >= 0 else "#f87171"
                    st.markdown(f"שער אמת: **${round(lev_curr, 2)}** (<span style='color:{change_color};'>{round(lev_change, 2)}%</span>)", unsafe_allow_html=True)
                    st.markdown(f'<span class="badge-drop">מרחק משיא הבסיס: {round(base_drop, 1)}%</span>', unsafe_allow_html=True)
                    if lev_drop <= -50.0:
                        st.markdown(f'<span class="badge-blackswan" style="margin-top:5px;">🚨 קריסת קצה בממונף ({round(lev_drop)}%)</span>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<p style='color:#94a3b8; font-size:14px; margin-bottom:2px;'>🌡️ אינדיקטורים טכניים:</p>", unsafe_allow_html=True)
                    ema_txt = "מתחת" if ema_distance < 0 else "מעל"
                    ema_col = "#34d399" if ema_distance < 0 else "#f87171"
                    st.markdown(f"• מרחק מ-EMA 200: <span style='color:{ema_col}; font-weight:700;'>{ema_txt} ({round(ema_distance, 1)}%)</span>", unsafe_allow_html=True)
                    
                    mfi_status = "📥 מוסדיים קונים" if mfi < 30 else ("📤 מוסדיים מוכרים" if mfi > 70 else "⚪ זרימה מאוזנת")
                    mfi_color = "#34d399" if mfi < 30 else ("#f87171" if mfi > 70 else "#cbd5e1")
                    st.markdown(f"• זרם הון: <span style='color:{mfi_color}; font-weight:700;'>{mfi_status} ({round(mfi)})</span>", unsafe_allow_html=True)
                    st.markdown(f"• מדד RSI מומנטום: **{round(rsi)}**")
                
                with col3:
                    st.markdown("<p style='color:#38bdf8; font-size:14px; margin-bottom:2px;'>💼 הפוזיציה האישית שלך (הזן כאן):</p>", unsafe_allow_html=True)
                    # קלט משתמש מקומי - נשמר בסשן המבודד שלו
                    user_tranches = st.number_input(f"מנות שנרכשו בפועל", min_value=0, max_value=20, value=int(st.session_state[f"{lev}_tranches"]), key=f"{lev}_input_tranches", step=1)
                    user_avg = st.number_input(f"מחיר קנייה ממוצע ($)", min_value=0.0, value=float(st.session_state[f"{lev}_avg_cost"]), key=f"{lev}_input_avg", step=0.5)
                    
                    # עדכון ה-state
                    st.session_state[f"{lev}_tranches"] = user_tranches
                    st.session_state[f"{lev}_avg_cost"] = user_avg
                    
                    total_tranches_global += user_tranches
                    total_money_global += (user_tranches * tranche_size)
                
                with col4:
                    st.markdown("<p style='color:#34d399; font-size:14px; margin-bottom:2px;'>🔮 פקודות ביצוע ומטריצה:</p>", unsafe_allow_html=True)
                    
                    if trigger_active:
                        st.markdown(f"<div style='background:#4a044e; color:#d946ef; padding:6px; border-radius:6px; font-weight:800; text-align:center;'>🚨 פקודת קנייה אקטיבית!<br>בצע רכישת מנה הבאה בשער בסיס ${round(next_base_price, 2)}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='background:#1e293b; color:#cbd5e1; padding:6px; border-radius:6px; text-align:center; font-size:14px;'>⏳ בהמתנה למדרגה הבאה<br>יעד קנייה: ${round(next_base_price, 2)} ({next_base_drop_target}%)</div>", unsafe_allow_html=True)
                    
                    # 🌟 פתרון הבועה שנחתכת: רכיב Popover מובנה שנפתח תמיד כלפי מטה בצורה מושלמת
                    with st.popover("📋 מטריצת יעדי שחרור מדורגים"):
                        st.markdown(f"<h5 style='color:#34d399;'>🎯 תוכנית שחרור מנות ל-{lev}:</h5>", unsafe_allow_html=True)
                        if user_tranches == 0:
                            st.info("אנא הזן 'מנות שנרכשו בפועל' (גדול מ-0) כדי לחשב את מפת יעדי המכירה האישיים שלך.")
                        else:
                            # שימוש במחיר הממוצע שהוזן על ידי המשתמש, ואם הוא 0 משתמשים באומדן מבוסס מחיר שוק
                            reference_price = user_avg if user_avg > 0 else lev_curr
                            
                            # קביעת מדרגות אחוזיות ויעדי חלוקה בהתאם למספר המנות הפעילות
                            if user_tranches == 1:
                                steps, div_name = [11, 22, 33], "שלישים (33% לכל חלק)"
                            elif user_tranches == 2:
                                steps, div_name = [10, 20, 30, 40], "רבעים (25% לכל חלק)"
                            elif user_tranches == 3:
                                steps, div_name = [10, 20, 30, 40, 50, 60], "שישיות (16.6% לכל חלק)"
                            elif user_tranches == 4:
                                steps, div_name = [10, 20, 30, 40, 50, 60, 70, 80], "שמיניות (12.5% לכל חלק)"
                            else:
                                steps, div_name = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], "עשיריות (10% לכל חלק)"
                                
                            st.write(f"**מודל חלוקה:** {div_name}")
                            st.write(f"מחיר בסיס לחישוב: **${round(reference_price, 2)}**")
                            st.markdown("---")
                            for i, step in enumerate(steps):
                                target_dollar = reference_price * (1 + step / 100)
                                st.markdown(f"📍 **יעד {i+1}** ({step}%+): למכור בשער **`${round(target_dollar, 2)}`**")
                
                st.markdown('</div>', unsafe_allow_html=True)
                # --- סיום בניית שורת נכס ---

# 5. עדכון כרטיסי סיכום עליונים דינמיים מבוססי State
st.sidebar.markdown("### 📊 סיכום הון במטריצה")
st.sidebar.metric("סה\"כ מנות בתיק", total_tranches_global)
st.sidebar.metric("הון מנוצל כולל", f"${total_money_global:,}")
st.sidebar.metric("נכסים באזור קנייה חם", f"{active_triggers_count} / 4")

# 6. פיד חדשות מאקרו מתורגם ומפולטר בלייב
ticker_news_list = fetch_ticker_news(["QQQ", "SOXX", "SPY", "XLF"])
if ticker_news_list:
    news_html = """<div class="news-container">
    <div class="news-title">📰 מבזקי מאקרו מתורגמים לטיקרים שבמעקב (סינון פאניקה)</div>"""
    for story in ticker_news_list:
        news_html += f"""<div class="news-item">
            <span class="news-tag">{story['ticker']}</span>
            <a href="{story['link']}" target="_blank">{story['title']}</a>
        </div>"""
    news_html += "</div>"
    st.markdown(news_html, unsafe_allow_html=True)
