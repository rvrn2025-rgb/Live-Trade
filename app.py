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

# 2. הזרקת עיצוב הייטקיסטי יוקרתי (Mobile-First & RTL)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main, .block-container, [data-testid="stMain"] {
    background-color: #030712 !important;
    color: #f3f4f6 !important;
    font-family: 'Assistant', sans-serif !important;
    overflow-x: hidden !important; 
    max-width: 100vw !important;
}

[data-testid="stAppViewContainer"] {
    direction: RTL !important;
    text-align: right !important;
}

h1, h2, h3, h4, h5 { color: #f9fafb !important; font-weight: 800 !important; }

.stMarkdown p, label { 
    font-size: 16px !important; 
    font-weight: 600 !important; 
    color: #9ca3af !important; 
    text-align: right !important;
}

.action-box {
    background: #111827;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 20px;
    text-align: center;
}
.action-alert { border: 2px solid #ef4444; background-color: #450a0a; }

.streamlit-expanderHeader {
    background-color: #1f2937 !important;
    border: 1px solid #374151 !important;
    border-radius: 8px !important;
    padding: 14px !important;
    font-size: 16px !important;
    color: #38bdf8 !important;
}

div[data-testid="stNumberInput"] input {
    text-align: right !important;
    background-color: #111827 !important;
    color: #ffffff !important;
    border: 1px solid #4b5563 !important;
}

/* קופסת מידע הייטקיסטית לכניסות גריד */
.cyber-info-box {
    background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
    border: 1px solid #1e293b;
    border-right: 4px solid #38bdf8;
    border-radius: 6px;
    padding: 14px;
    margin: 15px 0;
}
.cyber-row {
    font-family: 'JetBrains Mono', monospace, sans-serif;
    font-size: 14px;
    color: #e5e7eb;
    padding: 6px 0;
    border-bottom: 1px dashed #1e293b;
    display: flex;
    justify-content: space-between;
}

/* כרטיסי שחרור ויעדי מכירה */
.step-card {
    background-color: #111827;
    border-right: 4px solid #3b82f6;
    padding: 12px 16px;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
    border: 1px solid #1f2937;
    border-right: 4px solid #3b82f6;
}
.step-card-free {
    border-right-color: #10b981 !important;
    background-color: #064e3b !important;
    border-top: 1px solid #047857 !important;
    border-bottom: 1px solid #047857 !important;
    border-left: 1px solid #047857 !important;
}
</style>""", unsafe_allow_html=True)

# 3. פונקציית עזר לניהול זיכרון ידני חסין לופים
def trigger_manual_mode(lev_symbol):
    st.session_state[f"{lev_symbol}_is_manual"] = True

# 4. אתחול נכסים והגדרות בסיס
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (FAS)"}
]

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

# 5. פונקציות תשתית למשיכת נתונים
@st.cache_data(ttl=60)
def get_realtime_quotes(symbols_string, api_key):
    url = f"https://api.twelvedata.com/quote?symbol={symbols_string}&apikey={api_key}"
    try: return requests.get(url).json()
    except: return {}

@st.cache_data(ttl=900)
def get_historical_data(symbol):
    return yf.Ticker(symbol).history(period="max", auto_adjust=False)

API_KEY = "1541f1cd2a48488f83cfc193a9ada724"
all_tickers = ["QQQ", "TQQQ", "SOXX", "SOXL", "SPY", "UPRO", "XLF", "FAS"]
quote_response = get_realtime_quotes(",".join(all_tickers), API_KEY)

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
                
                auto_tranches = math.floor(abs_drop / drop_interval)
                next_tranche_num = auto_tranches + 1
                next_base_drop_target = next_tranche_num * drop_interval
                next_base_price = base_max * (1 - (next_base_drop_target / 100))
                next_lev_price = lev_max * (1 - ((next_base_drop_target * 3) / 100))
                
                distance_to_next = next_base_drop_target - abs_drop
                trigger_active = distance_to_next <= 0.5
                
                if trigger_active:
                    any_active_trigger = True
                
                # מנגנון סטייט חסין לנעילות ובלתי תלוי ברפרושים
                is_manual_key = f"{lev}_is_manual"
                tranches_key = f"{lev}_manual_tranches"
                
                if is_manual_key not in st.session_state:
                    st.session_state[is_manual_key] = False
                
                if not st.session_state[is_manual_key]:
                    st.session_state[tranches_key] = int(auto_tranches)
                
                processed_assets.append({
                    "pair": pair, "base_curr": base_curr, "lev_curr": lev_curr, "lev_change": lev_change,
                    "base_max": base_max, "lev_max": lev_max, "base_drop": base_drop,
                    "auto_tranches": auto_tranches, "next_tranche_num": next_tranche_num,
                    "next_base_price": next_base_price, "next_lev_price": next_lev_price, "next_base_drop_target": next_base_drop_target,
                    "distance_to_next": distance_to_next, "trigger_active": trigger_active,
                    "is_manual_key": is_manual_key, "tranches_key": tranches_key
                })

    # 6. התראה עליונה אקטיבית
    if any_active_trigger:
        st.markdown("""<div class="action-box action-alert">
            <h3 style="margin:0; color:#ffffff;">🚨 טריגר ביצוע אקטיבי!</h3>
            <p style="margin:5px 0 0 0; color:#fca5a5; font-size:15px;">אחד מהנכסים הגיע למדרגת הקנייה שלו. ההוראות בפנים מסומנות באדום.</p>
        </div>""", unsafe_allow_html=True)

    # 7. תצוגת הכרטיסים האנכית החדשה
    for asset in processed_assets:
        lev = asset["pair"]["leveraged"]
        base = asset["pair"]["base"]
        name = asset["pair"]["name"]
        
        sign = "+" if asset["lev_change"] > 0 else ""
        status_label = "🔴 טריגר רכישה!" if asset["trigger_active"] else "⏳ בהמתנה"
        title_text = f"{name} | ${asset['lev_curr']:.2f} ({sign}{asset['lev_change']:.2f}%) | {status_label}"
        
        with st.expander(title_text, expanded=asset["trigger_active"]):
            
            # --- חלק 1: יעדי כניסה ונתוני שוק ---
            st.markdown("<h4 style='color:#38bdf8; margin:0 0 10px 0;'>🎯 סטטוס ויעדי קנייה</h4>", unsafe_allow_html=True)
            st.markdown(f"• מרחק נוכחי משיא כל הזמנים: **`{asset['base_drop']:.1f}%`**")
            
            if not asset["trigger_active"]:
                st.markdown(f"• מרחק למדרגה הבאה (מנה {asset['next_tranche_num']}): עוד **`{asset['distance_to_next']:.1f}%`** ירידה בנכס הבסיס.")
            
            shares_to_buy = round(tranche_size / asset['lev_curr'])
            
            if asset["trigger_active"]:
                st.error(f"💥 **פקודת ביצוע מיידית:** רכוש כעת **{shares_to_buy} מניות** של {lev}")
            else:
                st.markdown(f"• **פקודה עתידית מתוכננת (מנה {asset['next_tranche_num']}):** קניית **{shares_to_buy} מניות** במידה ו-{base} מגיע ל-**`${asset['next_base_price']:.2f}`** (שער משוער לממונף: `${asset['next_lev_price']:.2f}`).")
            
            st.markdown("<hr style='margin:15px 0; border-color:#374151;'>", unsafe_allow_html=True)
            
            # --- חלק 2: ניהול פוזיציה ויעדי מכירה ---
            st.markdown("<h4 style='color:#34d399; margin:0 0 10px 0;'>💼 הפוזיציה הנוכחית ומפת שחרורים</h4>", unsafe_allow_html=True)
            
            # שדה קלט מנות מנוהל באמצעות קולבק ייעודי שלא ננעל לעולם
            active_t = st.number_input(
                "מנות אקטיביות בתיק כרגע:", 
                min_value=0, 
                max_value=20, 
                key=asset["tranches_key"],
                on_change=trigger_manual_mode,
                args=(lev,)
            )
            
            # הצגת כפתור איפוס תקין רק במידה ופעיל מעקף ידני
            if st.session_state[asset["is_manual_key"]]:
                st.markdown("<p style='color:#fbbf24; font-size:13px; margin:4px 0;'>⚠️ מצב עריכה ידנית פעיל (הסינכרון האוטומטי מושהה)</p>", unsafe_allow_html=True)
                if st.button("🔄 חזור לטייס אוטומטי", key=f"{lev}_reset_btn"):
                    st.session_state[asset["is_manual_key"]] = False
                    st.session_state[asset["tranches_key"]] = int(asset["auto_tranches"])
                    st.rerun()
            
            current_active_tranches = st.session_state[asset["tranches_key"]]
            
            # עדכון סורק תיק כולל
            total_portfolio_tranches += current_active_tranches
            total_portfolio_value += (current_active_tranches * tranche_size)
            
            if current_active_tranches > 0:
                # --- תיבת מידע אינפורמטיבית והייטקיסטית לפירוט נקודות הכניסה ---
                st.markdown('<div class="cyber-info-box">', unsafe_allow_html=True)
                st.markdown('<span style="color: #38bdf8; font-weight: bold; font-size: 14px; display:block; margin-bottom:8px;">📊 פירוט שערים הנדסיים של המנות שנרכשו:</span>', unsafe_allow_html=True)
                
                theoretical_prices = []
                for i in range(1, current_active_tranches + 1):
                    base_tranche_drop = i * drop_interval
                    lev_tranche_drop = base_tranche_drop * 3
                    
                    t_base_price = asset["base_max"] * (1 - (base_tranche_drop / 100))
                    t_lev_price = asset["lev_max"] * (1 - (lev_tranche_drop / 100))
                    theoretical_prices.append(t_lev_price)
                    
                    st.markdown(f"""<div class="cyber-row">
                        <span>🔹 מנה {i} (ירידה בבסיס: {base_tranche_drop}%)</span>
                        <span>שער בסיס: <b>${t_base_price:.2f}</b> | שער ממונף: <b>${t_lev_price:.2f}</b></span>
                    </div>""", unsafe_allow_html=True)
                
                auto_calculated_avg = sum(theoretical_prices) / len(theoretical_prices)
                st.markdown(f'<span style="color: #a3a3a3; font-size: 13px; display:block; margin-top:10px;">📐 מחיר ממוצע משוקלל של הגריד: <b>${auto_calculated_avg:.2f}</b></span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # הגדרת אסטרטגיית שחרורים לפי כמות מנות
                if current_active_tranches == 1: steps, label = [11, 22, 33], "שלישים"
                elif current_active_tranches == 2: steps, label = [10, 20, 30, 40], "רבעים"
                elif current_active_tranches == 3: steps, label = [10, 20, 30, 40, 50, 60], "שישיות"
                elif current_active_tranches == 4: steps, label = [10, 20, 30, 40, 50, 60, 70, 80], "שמיניות"
                else: steps, label = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], "עשיריות"
                
                total_invested_capital = current_active_tranches * tranche_size
                total_shares_owned = round(total_invested_capital / auto_calculated_avg)
                shares_per_step = max(1, round(total_shares_owned / len(steps)))
                
                st.markdown(f"<h5 style='color:#fbbf24; margin:15px 0 5px 0;'>🎯 יעדי פקודות מכירה (Take Profit)</h5>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size:13px; color:#9ca3af; margin-top:0;'>חלוקת אקזיט: <b>{label}</b> ({shares_per_step} מניות בכל תחנה)</p>", unsafe_allow_html=True)
                
                cumulative_cash_returned = 0
                for i, step in enumerate(steps):
                    target_price = auto_calculated_avg * (1 + step / 100)
                    step_cash = shares_per_step * target_price
                    cumulative_cash_returned += step_cash
                    return_pct = (cumulative_cash_returned / total_invested_capital) * 100
                    
                    if return_pct >= 100:
                        st.markdown(f"""<div class="step-card step-card-free">
                            <b>📍 יעד {i+1} (+{step}%):</b> מכור <b>{shares_per_step} מניות</b> בשער <b>${target_price:.2f}</b><br>
                            <span style='font-size:12px; color:#34d399; font-weight:700;'>🟢 פדיון מצטבר: ${cumulative_cash_returned:,.0f} ({return_pct:.0f}% מהקרן) 🚀 סיכון אפס! הקרן כוסתה.</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div class="step-card">
                            <b>📍 יעד {i+1} (+{step}%):</b> מכור <b>{shares_per_step} מניות</b> בשער <b>${target_price:.2f}</b><br>
                            <span style='font-size:12px; color:#9ca3af;'>💰 פדיון מצטבר: ${cumulative_cash_returned:,.0f} ({return_pct:.0f}% מהקרן)</span>
                        </div>""", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#9ca3af; font-size:14px;'>אין מנות פעילות בתיק כרגע. ברגע שהשוק ירד ויבוצע איסוף, יעדי המכירה והכניסות יופיעו כאן.</span>", unsafe_allow_html=True)

# 8. סרגל צדי לסיכום הון כולל
st.sidebar.markdown("### 📊 סיכום הון במטריצה")
st.sidebar.metric("סה\"כ מנות בתיק", total_portfolio_tranches)
st.sidebar.metric("הון מנוצל כולל", f"${total_portfolio_value:,}")
