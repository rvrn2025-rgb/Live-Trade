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

# 2. הזרקת עיצוב קסטום (Premium Dark Matrix) ותמיכה ב-RTL
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0b0f19 !important;
        color: #e2e8f0 !important;
        font-family: 'Assistant', sans-serif !important;
        direction: RTL !important;
        text-align: right !important;
    }
    
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* לוח הבקרה העליון */
    .control-panel {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
    }
    
    /* קסטומיזציה לטבלה של סטרימליט */
    [data-testid="stDataFrame"] {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 12px !important;
    }
    
    /* תיבות פלייבוק בתחתית */
    .playbook-card {
        background-color: #111827;
        border-right: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 4px 12px 12px 4px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. כותרת הטרמינל
st.markdown('<h1 style="text-align: center; color: #38bdf8;">⚡ טבלת מעקב ממונפות וליבה – ניהול מנות איסוף</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #94a3b8;">מערכת אלגוריתמית מתקדמת למיצוע הנדסי (DCA) ללא רגש</p>', unsafe_allow_html=True)

# 4. לוח בקרה אינטראקטיבי (סימולטור מותאם אישית לכל משתמש)
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
col_param1, col_param2, col_param3 = st.columns(3)

with col_param1:
    tranche_size = st.number_input("💰 גודל מנה קבועה לרכישה ($):", min_value=100, max_value=100000, value=3000, step=500)

with col_param2:
    drop_interval = st.selectbox("📐 מרווח ירידת הבסיס בין מנות (%):", [3.5, 5.0, 7.0, 10.0], index=0)

with col_param3:
    st.write("")
    st.write("")
    st.markdown(f"<p style='color: #34d399; font-weight: bold; text-align: center;'>מצב סימולציה פעיל // עדכון לייב</p>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 5. הגדרת זוגות המטריצה (בסיס + ממונף)
asset_pairs = [
    {"base": "QQQ", "leveraged": "TQQQ", "name": "📈 נאסד\"ק (QQQ / TQQQ)"},
    {"base": "SOXX", "leveraged": "SOXL", "name": "💻 שבבים (SOXX / SOXL)"},
    {"base": "SPY", "leveraged": "UPRO", "name": "🇺🇸 S&P 500 (SPY / UPRO)"},
    {"base": "XLF", "leveraged": "FAS", "name": "💰 פיננסים (XLF / FAS)"}
]

@st.cache_data(ttl=15)
def get_matrix_data(size, interval):
    rows = []
    for pair in asset_pairs:
        try:
            # שליפת נתוני נכס הבסיס (מבט חצי שנתי למציאת שיא ריאלי)
            base_stock = yf.Ticker(pair["base"])
            base_hist = base_stock.history(period="6mo", interval="1d")
            
            # שליפת מחיר ממונף נוכחי
            lev_stock = yf.Ticker(pair["leveraged"])
            lev_curr = lev_stock.history(period="1d")['Close'].iloc[-1]
            
            if len(base_hist) > 14:
                base_curr = base_hist['Close'].iloc[-1]
                base_max = base_hist['High'].max()
                
                # חישוב אחוז הירידה הריאלי של הבסיס מהטופ
                base_drop = ((base_curr - base_max) / base_max) * 100
                abs_drop = abs(base_drop)
                
                # מתמטיקה של מנות קנייה
                tranches_bought = math.floor(abs_drop / interval)
                total_deployed = tranches_bought * size
                
                # חישוב היעד הבא
                next_tranche_num = tranches_bought + 1
                next_drop_target = next_tranche_num * interval
                next_price_target = base_max * (1 - (next_drop_target / 100))
                
                # חישוב מדדי גיבוי ומומנטום לבסיס
                rsi = ta.momentum.rsi(base_hist['Close'], window=14).iloc[-1]
                stoch = ta.momentum.stoch(base_hist['High'], base_hist['Low'], base_hist['Close'], window=14).iloc[-1]
                mfi = ta.volume.money_flow_index(base_hist['High'], base_hist['Low'], base_hist['Close'], base_hist['Volume'], window=14).iloc[-1]
                
                # יצירת המלצה אוטומטית לפי קרבה ליעד
                distance_to_next = next_drop_target - abs_drop
                if distance_to_next <= 0.5:
                    recommendation = f"🚨 פקודה: רכוש מנה {next_tranche_num}!"
                else:
                    recommendation = f"⏳ ממתין למדרגה {next_tranche_num} ב-{next_drop_target}%"
                
                # מדדי מומנטום משולבים לתצוגה קומפקטית
                indicators_status = f"RSI: {round(rsi,1)} | STOCH: {round(stoch,1)}"
                
                rows.append({
                    "צמד נכסים": pair["name"],
                    "מחיר בסיס": round(base_curr, 2),
                    "מחיר ממונף": round(lev_curr, 2),
                    "ירידת בסיס מהשיא": round(base_drop, 1),
                    "מנות שנרכשו": f"{tranches_bought} מנות",
                    "הון מושקע בפוזיציה": f"${total_deployed:,}",
                    "מדדי מומנטום (בסיס)": indicators_status,
                    "🎯 מחיר יעד למנה הבאה": f"${round(next_price_target, 2)}",
                    "🔮 המלצה לביצוע": recommendation,
                    "is_trigger": distance_to_next <= 0.5  # עזר לצביעה
                })
        except:
            continue
    return pd.DataFrame(rows)

df = get_matrix_data(tranche_size, drop_interval)

if not df.empty:
    # 6. פונקציית צביעה מתוחכמת לשורות המטריצה
    def style_matrix(row):
        styles = [''] * len(row)
        # אם יש פקודת רכישה קרובה - נצבע את תא ההמלצה בזהב מנצנץ
        if row["is_trigger"]:
            styles[df.columns.get_loc("🔮 המלצה לביצוע")] = 'background-color: #78350f; color: #f59e0b; font-weight: bold;'
        else:
            styles[df.columns.get_loc("🔮 המלצה לביצוע")] = 'color: #94a3b8;'
            
        # צביעת אחוז הירידה בגוון כחול/ירוק הייטקסטי עמוק
        styles[df.columns.get_loc("ירידת בסיס מהשיא")] = 'background-color: #0f172a; color: #38bdf8; font-weight: bold;'
        return styles

    styled_df = df.style.apply(style_matrix, axis=1)

    # 7. הצגת טבלת המטריצה הראשית בהתאמה אישית מוחלטת
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_order=["צמד נכסים", "מחיר בסיס", "מחיר ממונף", "ירידת בסיס מהשיא", "מנות שנרכשו", "הון מושקע בפוזיציה", "מדדי מומנטום (בסיס)", "🎯 מחיר יעד למנה הבאה", "🔮 המלצה לביצוע"],
        column_config={
            "ירידת בסיס מהשיא": st.column_config.NumberColumn("ירידת בסיס מהשיא", format="%.1f%%"),
            "מחיר בסיס": st.column_config.NumberColumn("מחיר בסיס", format="$%.2f"),
            "מחיר ממונף": st.column_config.NumberColumn("מחיר ממונף", format="$%.2f"),
        }
    )
else:
    st.warning("מתחבר לשרתי הבורסה לשליפת הנתונים...")

# 8. ספר חוקים הנדסי מותאם לאסטרטגיית איסוף
st.write("")
st.write("---")
st.markdown('### 🛠️ מדריך הפעלה לקבוצה: מתמטיקת המיצועים של הממונפות')

col_guide1, col_guide2 = st.columns(2)

with col_guide1:
    st.markdown("""
    <div class="playbook-card">
        <h4>📐 חוק המנות והמרווח הדינמי</h4>
        <p>במקום לנחש איפה הרצפה, הטבלה מחלקת את השוק לרצועות מחיר קבועות לבחירתך (למשל כל 3.5%). 
        כאשר מדד הבסיס חוצה מדרגה, המערכת רושמת באופן קר שבוצע קניין של מנה נוספת ומחשבת את סך ההון שכבר הושקע בפוזיציה.</p>
    </div>
    """, unsafe_allow_html=True)

with col_guide2:
    st.markdown("""
    <div class="playbook-card" style="border-right-color: #34d399;">
        <h4>🎯 פקודות דולריות מדויקות (No Emotion)</h4>
        <p>עמודת <b>"מחיר יעד למנה הבאה"</b> לוקחת את שיא כל הזמנים הנוכחי ומחשבת עבורך בדיוק באיזה מחיר דולר של נכס הבסיס (למשל QQQ) עליך לפתוח את האפליקציה ולרכוש את המנה הבאה של הממונפת (TQQQ). אם רשום <b>⏳ ממתין</b>, אין שום סיבה לבצע פעולות בשוק.</p>
    </div>
    """, unsafe_allow_html=True)
