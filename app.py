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

# רענון אוטומטי מובנה כל 65 שניות לעדכון שערי אמת וחדשות
st_autorefresh(interval=65000, key="matrix_live_refresh")

# 2. הזרקת ארכיטקטורת עיצוב רספונסיבית (מחשב + סלולר) ובועות לחיצות
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
label, p, span { font-size: 17px !important; font-weight: 600 !important; color: #f1f5f9 !important; }
input { font-size: 18px !important; font-weight: 700 !important; }

/* כרטיסי סיכום עליונים - גמישים למובייל */
.kpi-container { display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 25px; }
.kpi-card { flex: 1; min-width: 220px; background: #0f172a; border: 2px solid #1e293b; border-radius: 8px; padding: 15px; text-align: center; }
.kpi-title { font-size: 14px !important; color: #94a3b8 !important; margin-bottom: 5px; }
.kpi-value { font-size: 24px !important; font-weight: 800 !important; color: #38bdf8; }

/* מעטפת טבלה לגלילה רוחבית חלקה בניידים */
.table-responsive { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 20px 0; border: 2px solid #1e293b; border-radius: 8px; }
.terminal-table { width: 100%; border-collapse: collapse; font-size: 16px; background-color: #0b0f19; }
.terminal-table th { background-color: #1e293b; color: #38bdf8; font-size: 15px; font-weight: 800; padding: 12px; text-align: right; border-bottom: 3px solid #334155; white-space: nowrap; }
.terminal-table td { padding: 12px; border-bottom: 1px solid #1e293b; color: #ffffff; vertical-align: middle; white-space: nowrap; }

/* מצבי שורות */
.row-trigger { background-color: #2d1510 !important; border-right: 6px solid #ef4444 !important; }
.row-normal:hover { background-color: #111827; }

/* תגיות */
.badge-drop { background-color: #7f1d1d; color: #fca5a5; padding: 4px 8px; border-radius: 6px; font-weight: 700; }
.badge-blackswan { background-color: #450a0a; color: #f87171; border: 1px solid #ef4444; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: 700; display: inline-block; margin-top: 4px; }
.badge-tranche { background-color: #1e3a8a; color: #93c5fd; padding: 4px 8px; border-radius: 6px; font-weight: 700; }

/* 🌟 מנגנון בועות מידע אינטראקטיביות (עובד בריחוף במחשב ובקליק/טאפ בנייד) */
.m-tip { position: relative; display: inline-block; color: #38bdf8; cursor: pointer; font-weight: bold; }
.m-tip .m-tip-text { visibility: hidden; width: 260px; background-color: #0f172a; color: #f1f5f9; text-align: right; border: 2px solid #38bdf8; border-radius: 6px; padding: 12px; position: absolute; z-index: 999; bottom: 130%; right: 0; opacity: 0; transition: opacity 0.2s; font-size: 14px; white-space: normal; box-shadow: 0 10px 25px rgba(0,0,0,0.7); }
.m-tip:hover .m-tip-text, .m-tip:focus .m-tip-text { visibility: visible; opacity: 1; }

/* עיצוב כפתור שחרור מנות */
.btn-exit-matrix { display: inline-block; margin-top: 6px; background-color: #1e293b; color: #34d399 !important; border: 1px solid #34d399; padding: 3px 8px; border-radius: 4px; font-size: 13px; font-weight: 700; text-align: center; }

/* התאמות מסך קטן במיוחד (מובייל) */
@media (max-width: 768px) {
    .kpi-container { flex-direction: column; }
    .kpi-card { width: 100%; }
    .terminal-table th, .terminal-table td { padding: 8px; font-size: 14px; }
}

/* תיבת חדשות */
.news-container { background: #0f172a; border: 2px solid #1e293b; border-radius: 8px; padding: 20px; margin-top: 30px; }
.news-title { color: #38bdf8; font-weight: 800; font-size: 20px; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
.news-item { margin-bottom: 12px; font-size: 15px; border-bottom: 1px dashed #1e293b; padding-bottom: 8px; }
.news-tag { background: #1e293b; color: #38bdf8; font-weight: bold; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 8px; }
.news-item a { color: #cbd5e1; text-decoration: none; transition: 0.2s; }
.news-item a:hover { color: #38bdf8; }
</style>""", unsafe_allow_html=True)

# 3. כותרת עליונה ונכסים
st.markdown('<h1 style="text-align: center; color: #38bdf8; font-size: 32px; margin-bottom: 5px;">⚡ טבלת מעקב ממונפות וליבה</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 18px; margin-bottom: 25px;">מערכת אלגוריתמית מתקדמת לניהול מנות איסוף ויעדי שחרור מדורגים ללא רגש</p>', unsafe_allow_html=True)

col_param1, col_param2, col_param3 = st.columns(3)
with col_param1:
    tranche_size = st.number_input("💰 גודל מנה קבועה לרכישה ($):", min_value=100, max_value=100000, value=3000, step=500)
with col_param2:
    drop_interval = st.selectbox("📐 מרווח ירידת הבסיס בין מנות (%):", [3.5, 5.0, 7.0, 10.0], index=0)
with col_param3:
    st.write("")
    st.write("")
    st.markdown("<p style='color: #34d399; font-weight: 800; text-align: center; font-size: 18px; margin-top: 5px;'>🟢 שערי אמת מסונכרנים ומותאמים לסלולר</p>", unsafe_allow_html=True)

# 4. פונקציות תשתית ומטמון לנתונים
@st.cache_data(ttl=60)
def get_realtime_quotes(symbols_string, api_key):
    url = f"https://api.twelvedata.com/quote?symbol={symbols_string}&apikey={api_key}"
    try: return requests.get(url).json()
    except: return {}

@st.cache_data(ttl=900)
def get_historical_data(symbol):
    return yf.Ticker(symbol).history(period="max", auto_adjust=False)

# מנוע תרגום חופשי וחכם מבוסס Google Translate ללא ספריות חיצוניות
@st.cache_data(ttl=3600)
def translate_headline(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=he&dt=t&q={quote(text)}"
        res = requests.get(url, timeout=4).json()
        return "".join([part[0] for part in res[0] if part[0]])
    except:
        return text

# משיכת חדשות ממוקדות לפי טיקרים מ-Yahoo Finance
@st.cache_data(ttl=600)
def fetch_ticker_news(tickers_list):
    combined_stories = []
    for t in tickers_list:
        try:
            url = f"https://feeds.finance.yahoo.com/rss.2.0/headline?s={t}"
            res = requests.get(url, timeout=4)
            root = ET.fromstring(res.content)
            items = root.findall('.//item')[:2] # לוקחים את 2 הכתבות הכי חמות לכל נייר
            for item in items:
                title_en = item.find('title').text
                link = item.find('link').text
                title_he = translate_headline(title_en)
                combined_stories.append({"ticker": t, "title": title_he, "link": link})
        except:
            continue
    return combined_stories

# רשימת ניירות ערך במטריצה
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (QQQ/TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXX/SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (SPY/UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (XLF/FAS)"}
]

API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
all_tickers = ["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"]
quote_response = get_realtime_quotes(",".join(all_tickers), API_KEY)

total_tranches_global = 0
total_money_global = 0
active_triggers_count = 0
table_rows_html = ""

if "status" in quote_response and quote_response["status"] == "error":
    st.error("❌ שגיאת מכסת API מצד ספק הנתונים. המערכת תתעדכן מחדש בעוד דקה.")
else:
    for pair in asset_pairs:
        base_quote = quote_response.get(pair["base"], {})
        lev_quote = quote_response.get(pair["leveraged"], {})
        
        if "close" in base_quote or "price" in base_quote:
            base_curr = float(base_quote.get("price", base_quote.get("close", 0)))
            lev_curr = float(lev_quote.get("price", lev_quote.get("close", 0)))
            lev_change = float(lev_quote.get("percent_change", 0))
            
            # חישוב היסטורי אבסולוטי (ATH) מיום ההנפקה
            df_base = get_historical_data(pair["base"]).copy()
            df_lev = get_historical_data(pair["leveraged"]).copy()
            
            if len(df_base) > 200 and len(df_lev) > 14:
                df_base.loc[df_base.index[-1], 'Close'] = base_curr
                base_max = df_base['High'].max()
                lev_max = df_lev['High'].max()
                
                base_drop = ((base_curr - base_max) / base_max) * 100
                abs_drop = abs(base_drop)
                lev_drop = ((lev_curr - lev_max) / lev_max) * 100
                
                # ממוצע נע 200 ומרחק
                ema_200 = ta.trend.ema_indicator(df_base['Close'], window=200).iloc[-1]
                ema_distance = ((base_curr - ema_200) / ema_200) * 100
                
                # מתנדים
                rsi = ta.momentum.rsi(df_base['Close'], window=14).iloc[-1]
                mfi = ta.volume.money_flow_index(df_base['High'], df_base['Low'], df_base['Close'], df_base['Volume'], window=14).iloc[-1]
                
                # חישוב מנות
                tranches_bought = math.floor(abs_drop / drop_interval)
                total_deployed = tranches_bought * tranche_size
                total_tranches_global += tranches_bought
                total_money_global += total_deployed
                
                next_tranche_num = tranches_bought + 1
                next_base_drop_target = next_tranche_num * drop_interval
                next_base_price = base_max * (1 - (next_base_drop_target / 100))
                
                # 📊 חישוב מתמטי מדויק לפקודות שחרור (Scaling-Out Matrix) מבוסס מנה אחרונה
                exit_tooltip_html = ""
                if tranches_bought == 0:
                    exit_tooltip_html = "אין מנות פעילות לשחרור כרגע בנכס זה."
                else:
                    # הערכת שער כניסה של המנה האחרונה לפי ירידת הבסיס הרלוונטית (פקטור מינוף ממוצע פי 3)
                    last_tranche_base_drop = tranches_bought * drop_interval
                    lev_entry_est = lev_max * (1 - (last_tranche_base_drop * 3 / 100))
                    if lev_entry_est <= 0: lev_entry_est = lev_curr
                    
                    if tranches_bought == 1:
                        steps, div_name = [11, 22, 33], "שלישים (33% לכל חלק)"
                    elif tranches_bought == 2:
                        steps, div_name = [10, 20, 30, 40], "רבעים (25% לכל חלק)"
                    elif tranches_bought == 3:
                        steps, div_name = [10, 20, 30, 40, 50, 60], "שישיות (16.6% לכל חלק)"
                    elif tranches_bought == 4:
                        steps, div_name = [10, 20, 30, 40, 50, 60, 70, 80], "שמיניות (12.5% לכל חלק)"
                    else:
                        steps, div_name = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], "עשיריות (10% לכל חלק)"
                    
                    exit_tooltip_html = f"<b>📋 מפת יעדי יציאה מדורגת ({div_name}):</b><br>"
                    exit_tooltip_html += f"מחיר מנה אחרונה משוער: ${round(lev_entry_est, 2)}<br><hr style='margin:5px 0; border-color:#38bdf8;'>"
                    for i, step in enumerate(steps):
                        target_price = lev_entry_est * (1 + step / 100)
                        exit_tooltip_html += f"יעד {i+1}: למכור בשער <b>${round(target_price, 2)}</b> (+{step}%)<br>"
                
                # עיצוב מוסדיים (MFI)
                if mfi < 30:
                    mfi_html = f"<span class='m-tip' tabindex='0'>📥 מוסדיים אוספים ({round(mfi)})<span class='m-tip-text'>איסוף מוסדי חם: כסף גדול מנצל את הירידות כדי לקנות כמויות ענק של סחורה בזול בזמן שהציבור בורח.</span></span>"
                    mfi_bullish = True
                elif mfi > 70:
                    mfi_html = f"<span class='m-tip' tabindex='0' style='color:#f87171;'>📤 מוסדיים מוכרים ({round(mfi)})<span class='m-tip-text'>סיכון גבוה: כסף חכם מממש רווחים ומוכר את הסחורה לציבור בשיא.</span></span>"
                    mfi_bullish = False
                else:
                    mfi_html = f"<span class='m-tip' tabindex='0' style='color:#cbd5e1;'>⚪ זרימה מאוזנת ({round(mfi)})<span class='m-tip-text'>פעילות שוק רגילה ונייטרלית. אין כניסה או יציאה חריגה של גופים מוסדיים.</span></span>"
                    mfi_bullish = False
                
                # מרחק מ-EMA 200
                ema_color = "#34d399" if ema_distance < 0 else "#f87171"
                ema_status = "מתחת" if ema_distance < 0 else "מעל"
                ema_html = f"<span style='color: {ema_color}; font-weight: bold;'>{ema_status} לממוצע ({round(ema_distance, 1)}%)</span>"
                
                # קריסת קצה (Black Swan)
                blackswan_html = ""
                if lev_drop <= -50.0:
                    blackswan_html = f"<br><span class=\"badge-blackswan m-tip\" tabindex=\"0\">🚨 קריסת קצה ({round(lev_drop)}%)<span class=\"m-tip-text\">אזהרת תנודתיות קצה: הנייר איבד מעל 50% מהשיא הכולל שלו אי פעם (ATH). נקודת כניסה היסטורית אך ברמת סיכון עצומה.</span></span>"
                
                change_color = "#34d399" if lev_change >= 0 else "#f87171"
                change_sign = "+" if lev_change > 0 else ""
                change_html = f"<span style='color: {change_color}; font-weight: 700;'>{change_sign}{round(lev_change, 2)}%</span>"
                
                # בדיקת איתות והצטלבות (Confluence)
                distance_to_next = next_base_drop_target - abs_drop
                trigger_active = distance_to_next <= 0.5
                
                if trigger_active:
                    row_class = "row-trigger"
                    active_triggers_count += 1
                    if (rsi < 35) and mfi_bullish and (ema_distance < 0):
                        matrix_grade = "<div style='margin-top: 8px; font-size: 14px; color: #d946ef; font-weight: 800; background: #4a044e; padding: 4px; border-radius: 4px;'>🎯 איתות זהב: הצטלבות מושלמת!</div>"
                    elif (rsi < 40) or mfi_bullish:
                        matrix_grade = "<div style='margin-top: 8px; font-size: 13px; color: #fbbf24; font-weight: 700;'>🔥 איתות חזק (מומנטום תומך)</div>"
                    else:
                        matrix_grade = "<div style='margin-top: 8px; font-size: 13px; color: #f8fafc;'>✅ מדרגה הנדסית רגילה</div>"
                    rec_text = f"<td style='background-color: #78350f; color: #fbbf24; font-weight: bold; text-align: center;'>🚨 פקודה אקטיבית:<br>רכוש מנה {next_tranche_num}!{matrix_grade}</td>"
                else:
                    row_class = "row-normal"
                    rec_text = f"<td style='color: #a1a1aa; text-align: center;'>⏳ ממתין למדרגה {next_tranche_num}<br><span style='font-size: 12px;'>מרחק לטריגר: {round(distance_to_next, 2)}%</span></td>"
                
                table_rows_html += f"""<tr class="{row_class}">
<td>
<span style="font-size: 17px; font-weight: bold; color: #38bdf8;">{pair["name"]}</span>
{blackswan_html}
</td>
<td>
<b style="color: #94a3b8;">בסיס:</b> ${round(base_curr, 2)}<br>
<b style="color: #94a3b8;">ממונף:</b> ${round(lev_curr, 2)}
</td>
<td>{change_html}</td>
<td><span class="badge-drop">{round(base_drop, 1)}%</span></td>
<td>
<span class="badge-tranche">{tranches_bought} מנות</span><br>
<span class="btn-exit-matrix m-tip" tabindex="0">📋 יעדי שחרור<span class="m-tip-text">{exit_tooltip_html}</span></span>
</td>
<td><span style="color: #34d399; font-weight: bold;">${total_deployed:,}</span></td>
<td>
<span style="color: #ffffff;">במחיר בסיס:</span><br>
<b style="color: #38bdf8; font-size: 17px;">${round(next_base_price, 2)}</b><br>
<span style="color: #94a3b8; font-size: 12px;">(יעד: {next_base_drop_target}%)</span>
</td>
<td>
<span class="m-tip" tabindex="0"><b>EMA 200:</b> {ema_html}<span class="m-tip-text">ממוצע נע 200 מייצג את מחיר האיזון השנתי. כל אחוז מתחתיו נחשב להנחה משמעותית בשוק.</span></span><br>
<b>זרם הון:</b> {mfi_html}
</td>
{rec_text}
</tr>"""

# 5. הצגת כרטיסי סיכום (KPIs)
st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-title">סה"כ מנות שנאספו במטריצה</div>
        <div class="kpi-value">{total_tranches_global}</div>
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

# 6. הצגת הטבלה הרספונסיבית עם האייקונים הלחיצים בנייד
table_html = f"""
<div class="table-responsive">
<table class="terminal-table">
<thead>
<tr>
<th>צמד נכסים <span class="m-tip" tabindex="0">❓<span class="m-tip-text">צמד הניירות במעקב. נכס הבסיס המודד והנכס הממונף פי 3 לביצוע.</span></span></th>
<th>שער אמת</th>
<th>שינוי יומי</th>
<th>ירידה מהשיא (ATH) <span class="m-tip" tabindex="0">❓<span class="m-tip-text">המרחק האחוזי של נכס הבסיס מנקודת השיא האבסולוטית שלו מאז יום הנפקתו (All-Time High).</span></span></th>
<th>⚡ מנות ויעדי שחרור</th>
<th>💰 הון מושקע</th>
<th>🎯 טריגר למנה הבאה</th>
<th>🌡️ תמיכה מוסדית וטכנית</th>
<th>🔮 ציון מטריצה וביצוע</th>
</tr>
</thead>
<tbody>
{table_rows_html}
</tbody>
</table>
</div>
"""
st.markdown(table_html, unsafe_allow_html=True)

# 7. פיד חדשות מתורגם ומפולטר לפי טיקרים בלייב
ticker_news_list = fetch_ticker_news(["QQQ", "SOXX", "SPY", "XLF"])
if ticker_news_list:
    news_html = """<div class="news-container">
    <div class="news-title">
    📰 מבזקי מאקרו מתורגמים לטיקרים שבמעקב 
    <span class="m-tip" tabindex="0" style="font-size:15px; color:#94a3b8;">❓<span class="m-tip-text">משקיע DCA מנצל פאניקה. כותרות אדומות או מבוהלות לגבי הטיקרים שבטבלה הן האישור המנטלי הכי טוב לכך שהמתמטיקה של המטריצה עובדת בנקודות קיצון.</span></span>
    </div>"""
    for story in ticker_news_list:
        news_html += f"""<div class="news-item">
            <span class="news-tag">{story['ticker']}</span>
            <a href="{story['link']}" target="_blank">{story['title']}</a>
        </div>"""
    news_html += "</div>"
    st.markdown(news_html, unsafe_allow_html=True)
