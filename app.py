import streamlit as st
import yfinance as yf
import pandas as pd
import math
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת תצורת דף ומערכת לביצועים מקסימליים
st.set_page_config(page_title="DCA Matrix Terminal", layout="wide", initial_sidebar_state="collapsed")

# רענון אוטומטי מובנה כל 30 שניות לסנכרון שערים חי
st_autorefresh(interval=30000, key="matrix_live_refresh")

# 2. ארכיטקטורת עיצוב הייטקיסטית (Mobile-First, ללא Sidebar, תמיכת RTL מלאה)
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

.global-summary-box {
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
    border: 1px solid #312e81;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 25px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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

.step-card {
    background-color: #111827;
    border-right: 4px solid #3b82f6;
    padding: 12px 16px;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
    border: 1px solid #1f2937;
}
.step-card-free {
    border-right-color: #10b981 !important;
    background-color: #064e3b !important;
    border-top: 1px solid #047857 !important;
    border-bottom: 1px solid #047857 !important;
    border-left: 1px solid #047857 !important;
}
</style>""", unsafe_allow_html=True)

# 3. פונקציות קדם-ריצה (Callbacks) לניהול מצב ידני חסין לופים
def cb_set_manual(lev_symbol):
    st.session_state[f"{lev_symbol}_is_manual"] = True

def cb_reset_autopilot(lev_symbol, auto_val):
    st.session_state[f"{lev_symbol}_is_manual"] = False
    st.session_state[f"{lev_symbol}_tranches_value"] = int(auto_val)

# 4. הגדרת נכסים קבועים למטריצה (מנוע סינתטי יציב לחלוטין עבור מדדים מורכבים)
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (FAS)"},
    {"base": "TA35.TA", "leveraged": "TA35-SYNTH", "name": "🇮🇱 ת\"א 35 (3x סינתטי)"},
    {"base": "^TELBANK5", "leveraged": "BANKS-SYNTH", "name": "🏦 מדד הבנקים 5 (3x סינתטי)"},
    {"base": "SPMO", "leveraged": "SPMO-SYNTH", "name": "🚀 מומנטום SPMO (3x סינתטי)"}
]

# 5. הגדרות פרמטרים בראש העמוד
st.markdown("### 🛠️ הגדרות אסטרטגיית גריד")
col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
with col_p1:
    tranche_size = st.number_input("💰 תקציב קבוע למנה (דולר/שקל):", min_value=100, max_value=100000, value=3000, step=500)
with col_p2:
    interval_choice = st.selectbox("📐 מרווח ירידה בין מנות (נכס בסיס):", ["3.5%", "5.0%", "7.0%", "10.0%", "הזן ידנית..."], index=1)
with col_p3:
    if interval_choice == "הזן ידנית...":
        drop_interval = st.number_input("הזן אחוז מרווח אישי:", min_value=0.5, max_value=50.0, value=6.5, step=0.5)
    else:
        drop_interval = float(interval_choice.replace("%", ""))

# הגנה גלובלית מפני מרווח אפס שעלול להקריס את הגריד
if drop_interval <= 0:
    drop_interval = 0.1

# 6. מנגנון משיכת נתונים מהיר מ-Yahoo Finance עם הגנות קריסה
@st.cache_data(ttl=86400)
def get_historical_ath(symbol):
    try:
        df = yf.Ticker(symbol).history(period="max", auto_adjust=False)
        if not df.empty and 'High' in df.columns:
            return float(df['High'].max())
        return 0.0
    except:
        return 0.0

@st.cache_data(ttl=30)
def get_live_market_data(tickers_list):
    try:
        df = yf.download(tickers_list, period="2d", progress=False)
        results = {}
        for t in tickers_list:
            try:
                if isinstance(df['Close'], pd.DataFrame) and t in df['Close'].columns:
                    close_series = df['Close'][t].dropna()
                else:
                    close_series = df['Close'].dropna()
                
                if not close_series.empty:
                    live_price = float(close_series.iloc[-1])
                    if len(close_series) >= 2:
                        prev_close = float(close_series.iloc[-2])
                        # מניעת חילוק באפס בחישוב אחוז השינוי היומי
                        pct_change = ((live_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                    else:
                        pct_change = 0.0
                    results[t] = {"price": live_price, "pct_change": pct_change}
                else:
                    results[t] = {"price": 0.0, "pct_change": 0.0}
            except:
                results[t] = {"price": 0.0, "pct_change": 0.0}
        return results
    except:
        return {}

# משיכת נתוני המדדים והמניות האמתיות בלבד
all_tickers = list(set([p["base"] for p in asset_pairs] + [p["leveraged"] for p in asset_pairs if not p["leveraged"].endswith("-SYNTH")]))
live_quotes = get_live_market_data(all_tickers)

processed_assets = []
any_active_trigger = False
total_portfolio_tranches = 0
total_portfolio_value = 0

# 7. עיבוד ואינטגרציה של הנתונים עם שכבת שריון מפני חילוק באפס
for pair in asset_pairs:
    base = pair["base"]
    lev = pair["leveraged"]
    name = pair["name"]
    
    base_data = live_quotes.get(base, {"price": 0.0, "pct_change": 0.0})
    base_curr = base_data["price"]
    base_change = base_data["pct_change"]
    
    is_synthetic = lev.endswith("-SYNTH")
    currency = "₪" if (base.endswith(".TA") or base.startswith("^TA") or base.startswith("^TEL")) else "$"
    
    override_key = f"{base}_manual_price_input"
    ath_key = f"{base}_manual_ath_input"
    
    # שלב בדיקת כיול ידני מהמשתמש למקרה שיאהו נכשל
    if base_curr == 0 and override_key in st.session_state:
        base_curr = st.session_state[override_key]
        
    base_max_hist = get_historical_ath(base)
    if base_max_hist == 0 and ath_key in st.session_state:
        base_max_hist = st.session_state[ath_key]
        
    # אם יש לנו מחיר תקין - מחשבים מטריצה
    if base_curr > 0:
        base_max = max(base_max_hist if base_max_hist > 0 else base_curr, base_curr)
        
        # הגנה מפני חילוק באפס בחישוב הירידה מהשיא
        base_drop = ((base_curr - base_max) / base_max) * 100 if base_max > 0 else 0.0
        abs_drop = abs(base_drop)
        
        if is_synthetic:
            lev_change = base_change * 3
            lev_max = 100.0
            lev_curr = max(0.01, lev_max * (1 - (abs_drop * 3 / 100)))
        else:
            lev_data = live_quotes.get(lev, {"price": 0.0, "pct_change": 0.0})
            lev_curr = lev_data["price"]
            lev_change = lev_data["pct_change"]
            lev_max_hist = get_historical_ath(lev)
            lev_max = max(lev_max_hist if lev_max_hist > 0 else lev_curr, lev_curr)
            
        auto_tranches = math.floor(abs_drop / drop_interval)
        next_tranche_num = auto_tranches + 1
        next_base_drop_target = next_tranche_num * drop_interval
        next_base_price = base_max * (1 - (next_base_drop_target / 100))
        next_lev_price = lev_max * (1 - ((next_base_drop_target * 3) / 100))
        
        distance_to_next = next_base_drop_target - abs_drop
        trigger_active = distance_to_next <= 0.5
        needs_calibration = False
    else:
        # מצב נכס בהמתנה לכיול ידני
        base_drop = 0.0
        lev_curr = 0.0
        lev_change = 0.0
        auto_tranches = 0
        next_tranche_num = 1
        next_base_drop_target = drop_interval
        next_base_price = 0.0
        next_lev_price = 0.0
        distance_to_next = drop_interval
        trigger_active = False
        needs_calibration = True
        base_max = 0.0
        lev_max = 100.0
        
    if trigger_active:
        any_active_trigger = True
        
    is_manual_key = f"{lev}_is_manual"
    val_key = f"{lev}_tranches_value"
    
    if is_manual_key not in st.session_state:
        st.session_state[is_manual_key] = False
        
    if not st.session_state[is_manual_key]:
        st.session_state[val_key] = int(auto_tranches)
        
    current_tranches = st.session_state[val_key]
    total_portfolio_tranches += current_tranches
    total_portfolio_value += (current_tranches * tranche_size)
    
    processed_assets.append({
        "pair": pair, "base_curr": base_curr, "lev_curr": lev_curr, "lev_change": lev_change,
        "base_max": base_max, "lev_max": lev_max, "base_drop": base_drop,
        "auto_tranches": auto_tranches, "next_tranche_num": next_tranche_num,
        "next_base_price": next_base_price, "next_lev_price": next_lev_price, "next_base_drop_target": next_base_drop_target,
        "distance_to_next": distance_to_next, "trigger_active": trigger_active,
        "is_manual_key": is_manual_key, "val_key": val_key, "current_tranches": current_tranches,
        "is_synthetic": is_synthetic, "currency": currency, "needs_calibration": needs_calibration,
        "override_key": override_key, "ath_key": ath_key, "base_max_hist": base_max_hist
    })

# --- תצוגת הרכיבים על המסך ---
st.markdown(f"""<div class="global-summary-box">
    <h4 style="margin:0 0 10px 0; color:#818cf8;">📊 סיכום הון במטריצה הגלובלית</h4>
    <div style="display:flex; justify-content:space-around; flex-wrap:wrap; gap:10px;">
        <div><span style="color:#9ca3af; font-size:14px;">מנות אקטיביות בתיק:</span><br><b style="font-size:22px; color:#ffffff;">{total_portfolio_tranches}</b></div>
        <div><span style="color:#9ca3af; font-size:14px;">הון מנוצל כולל (יחידות מטבע):</span><br><b style="font-size:22px; color:#34d399;">{total_portfolio_value:,}</b></div>
    </div>
</div>""", unsafe_allow_html=True)

if any_active_trigger:
    st.markdown("""<div class="action-box action-alert">
        <h3 style="margin:0; color:#ffffff;">🚨 טריגר ביצוע אקטיבי!</h3>
        <p style="margin:5px 0 0 0; color:#fca5a5; font-size:15px;">אחד מהנכסים הגיע למדרגת הקנייה שלו. הוראות הביצוע בפנים מסומנות באדום.</p>
    </div>""", unsafe_allow_html=True)

for asset in processed_assets:
    lev = asset["pair"]["leveraged"]
    base = asset["pair"]["base"]
    name = asset["pair"]["name"]
    currency = asset["currency"]
    
    sign = "+" if asset["lev_change"] > 0 else ""
    
    if asset["needs_calibration"]:
        title_text = f"{name} | ⚠️ נדרש כיול שער ידני | ⏳ בהמתנה"
    else:
        price_display = f"{currency}{asset['lev_curr']:.2f} (סינתטי)" if asset["is_synthetic"] else f"{currency}{asset['lev_curr']:.2f}"
        status_label = "🔴 טריגר רכישה!" if asset["trigger_active"] else "⏳ בהמתנה"
        title_text = f"{name} | {price_display} ({sign}{asset['lev_change']:.2f}%) | {status_label}"
    
    with st.expander(title_text, expanded=asset["needs_calibration"] or asset["trigger_active"]):
        
        if asset["needs_calibration"]:
            st.warning(f"⚠️ שרת הבורסה לא החזיר ציטוט אוטומטי עבור {base} (שוק סגור או חסימת שרת).")
            st.number_input(f"הזן מחיר שוק נוכחי של המדד ({base}) מגלובס/ביזפורטל:", min_value=0.0, step=1.0, value=0.0, key=asset["override_key"])
            st.number_input(f"הזן שער שיא כל הזמנים (ATH) של המדד (אם לא ידוע, שים את השער הנוכחי):", min_value=0.0, step=1.0, value=0.0, key=asset["ath_key"])
            st.markdown("<span style='color:#9ca3af; font-size:13px;'>ברגע שתקליד שער ותלחץ Enter, המטריצה כולה תתעורר לחיים ותציג פקודות רכישה ויעדי אקזיט!</span>", unsafe_allow_html=True)
            continue
            
        st.markdown("<h4 style='color:#38bdf8; margin:0 0 10px 0;'>🎯 סטטוס ויעדי קנייה</h4>", unsafe_allow_html=True)
        st.markdown(f"• מרחק נוכחי משיא כל הזמנים של הבסיס: **`{asset['base_drop']:.1f}%`**")
        
        if not asset["trigger_active"]:
            st.markdown(f"• מרחק למדרגה הבאה (מנה {asset['next_tranche_num']}): עוד **`{asset['distance_to_next']:.1f}%`** ירידה בנכס הבסיס.")
        
        # הגנה מפני חילוק באפס בחישוב כמות מניות לקנייה
        shares_to_buy = round(tranche_size / asset['lev_curr']) if asset['lev_curr'] > 0 else 0
        
        if asset["trigger_active"]:
            st.error(f"💥 **פקודת ביצוע מיידית:** רכוש כעת בשווי של **{tranche_size}{currency}** מתוך הנכס הממונף (כ-{shares_to_buy} יחידות).")
        else:
            st.markdown(f"• **פקודה עתידית מתוכננת (מנה {asset['next_tranche_num']}):** קנייה במידה והבסיס יגיע ל-**`{currency}{asset['next_base_price']:.2f}`** (שער יעד משוער לממונף: `{currency}{asset['next_lev_price']:.2f}`).")
        
        st.markdown("<hr style='margin:15px 0; border-color:#374151;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#34d399; margin:0 0 10px 0;'>💼 הפוזיציה הנוכחית ומפת שחרורים</h4>", unsafe_allow_html=True)
        
        st.number_input(
            "מנות אקטיביות בתיק כרגע:", 
            min_value=0, max_value=20, 
            key=asset["val_key"],
            on_change=cb_set_manual,
            args=(lev,)
        )
        
        if st.session_state[asset["is_manual_key"]]:
            st.markdown("<p style='color:#fbbf24; font-size:13px; margin:4px 0;'>⚠️ מצב עריכה ידנית פעיל (הסינכרון האוטומטי מושהה)</p>", unsafe_allow_html=True)
            st.button("🔄 חזור לטייס אוטומטי", key=f"{lev}_reset_btn", on_click=cb_reset_autopilot, args=(lev, asset["auto_tranches"]))
        
        current_active_tranches = st.session_state[asset["val_key"]]
        
        if current_active_tranches > 0:
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
                    <span>🔹 מנה {i} (ירידה: {base_tranche_drop}%)</span>
                    <span>בסיס: <b>{currency}{t_base_price:.2f}</b> | ממונף: <b>{currency}{t_lev_price:.2f}</b></span>
                </div>""", unsafe_allow_html=True)
            
            # הגנה מפני חילוק באפס בחישוב ממוצע משוקלל
            auto_calculated_avg = sum(theoretical_prices) / len(theoretical_prices) if len(theoretical_prices) > 0 else 0.0
            st.markdown(f'<span style="color: #a3a3a3; font-size: 13px; display:block; margin-top:10px;">📐 מחיר ממוצע משוקלל של הגריד: <b>{currency}{auto_calculated_avg:.2f}</b></span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if current_active_tranches == 1: steps, label = [11, 22, 33], "שלישים"
            elif current_active_tranches == 2: steps, label = [10, 20, 30, 40], "רבעים"
            elif current_active_tranches == 3: steps, label = [10, 20, 30, 40, 50, 60], "שישיות"
            elif current_active_tranches == 4: steps, label = [10, 20, 30, 40, 50, 60, 70, 80], "שמיניות"
            else: steps, label = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], "עשיריות"
            
            total_invested_capital = current_active_tranches * tranche_size
            
            # הגנה מפני חילוק באפס בחישוב סך המניות ויעדי המכירה
            total_shares_owned = round(total_invested_capital / auto_calculated_avg) if auto_calculated_avg > 0 else 0
            shares_per_step = max(1, round(total_shares_owned / len(steps))) if len(steps) > 0 else 1
            
            st.markdown(f"<h5 style='color:#fbbf24; margin:15px 0 5px 0;'>🎯 יעדי פקודות מכירה (Take Profit)</h5>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:13px; color:#9ca3af; margin-top:0;'>חלוקת אקזיט: <b>{label}</b> ({shares_per_step} מניות בכל תחנה)</p>", unsafe_allow_html=True)
            
            cumulative_cash_returned = 0
            for i, step in enumerate(steps):
                target_price = auto_calculated_avg * (1 + step / 100)
                step_cash = shares_per_step * target_price
                cumulative_cash_returned += step_cash
                
                # הגנה מפני חילוק באפס בחישוב אחוז החזר הקרן
                return_pct = (cumulative_cash_returned / total_invested_capital) * 100 if total_invested_capital > 0 else 0.0
                
                if return_pct >= 100:
                    st.markdown(f"""<div class="step-card step-card-free">
                        <b>📍 יעד {i+1} (+{step}%):</b> מכור <b>{shares_per_step} מניות</b> בשער <b>{currency}{target_price:.2f}</b><br>
                        <span style='font-size:12px; color:#34d399; font-weight:700;'>🟢 פדיון מצטבר: {currency}{cumulative_cash_returned:,.0f} ({return_pct:.0f}% מהקרן) 🚀 סיכון אפס!</span>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="step-card">
                        <b>📍 יעד {i+1} (+{step}%):</b> מכור <b>{shares_per_step} מניות</b> בשער <b>{currency}{target_price:.2f}</b><br>
                        <span style='font-size:12px; color:#9ca3af;'>💰 פדיון מצטבר: {currency}{cumulative_cash_returned:,.0f} ({return_pct:.0f}% מהקרן)</span>
                    </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#9ca3af; font-size:14px;'>אין מנות פעילות בתיק כרגע. ברגע שהשוק ירד, יעדי המכירה והכניסות יופיעו כאן.</span>", unsafe_allow_html=True)
