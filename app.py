import streamlit as st
import yfinance as yf
import pandas as pd
import ta
from streamlit_autorefresh import st_autorefresh

# 1. הגדרת דף ברוחב מלא
st.set_page_config(page_title="PRO-Terminal // Leveraged Tracker", layout="wide")

# רענון אוטומטי מובנה (כל 30 שניות)
st_autorefresh(interval=30000, key="datarefresh")

# 2. הזרקת קוד עיצוב הייטקסטי (Dark Cyber Theme) כולל תמיכה מלאה ב-RTL
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    
    /* עיצוב כללי של האפליקציה */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #090d16 !important;
        color: #f0f4f8 !important;
        font-family: 'Assistant', sans-serif !important;
        direction: RTL !important;
        text-align: right !important;
    }
    
    /* עיצוב כותרות */
    h1 {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-shadow: 0px 0px 15px rgba(0, 200, 255, 0.3);
        border-bottom: 2px solid #1e293b;
        padding-bottom: 15px;
    }
    
    /* כרטיסיות הייטק מותאמות אישית */
    .kpi-card {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        margin-bottom: 20px;
    }
    .kpi-title { color: #9ca3af; font-size: 14px; font-weight: 600; }
    .kpi-value { color: #38bdf8; font-size: 24px; font-weight: 700; margin-top: 5px; }
    
    /* התאמת הטבלה של סטרימליט למראה חשוך ונקי */
    [data-testid="stDataFrame"] {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 12px !important;
        padding: 10px !important;
    }
    
    /* תיבות מידע בתחתית */
    .playbook-box {
        background-color: #0f172a;
        border-right: 4px solid #38bdf8;
        padding: 15px;
        border-radius: 4px 12px 12px 4px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. כותרת עליונה מעוצבת וממורכזת
st.markdown('<h1 style="text-align: center;">⚡ טבלת מעקב ממונפות וליבה | PRO TERMINAL</h1>', unsafe_allow_html=True)
st.write("")

# 4. סרגל כלים מתקדם (שליטה במסגרת הזמן)
col_control1, col_control2 = st.columns([2, 2])
with col_control1:
    tf_choice = st.selectbox(
        "⚡ בחר אינטרוול זמן לדיוק אישורי כניסה:",
        ["יומי (Daily) - אסטרטגי לקפיצים ארוכים", "שעתי (1 Hour) - סווינג מהיר", "15 דקות (15m) - תזמון נקודת תפנית נקודתית"]
    )

if tf_choice.startswith("יומי"):
    period, interval = "3mo", "1d"
elif tf_choice.startswith("שעתי"):
    period, interval = "1mo", "1h"
else:
    period, interval = "1wk", "15m"

# 5. רשימת הנכסים המובנית
ticker_details = [
    {"ticker": "QQQ", "category": "📈 נאסד\"ק (Nasdaq)", "type": "בסיס (x1)"},
    {"ticker": "TQQQ", "category": "📈 נאסד\"ק (Nasdaq)", "type": "ממונף (x3)"},
    {"ticker": "SOXX", "category": "💻 שבבים (Semiconductors)", "type": "בסיס (x1)"},
    {"ticker": "SOXL", "category": "💻 שבבים (Semiconductors)", "type": "ממונף (x3)"},
    {"ticker": "SPY", "category": "🇺🇸 S&P 500", "type": "בסיס (x1)"},
    {"ticker": "UPRO", "category": "🇺🇸 S&P 500", "type": "ממונף (x3)"},
    {"ticker": "XLF", "category": "💰 פיננסים (Finance)", "type": "בסיס (x1)"},
    {"ticker": "FAS", "category": "💰 פיננסים (Finance)", "type": "ממונף (x3)"},
]

@st.cache_data(ttl=15)
def fetch_terminal_data(p, i):
    data_list = []
    for item in ticker_details:
        ticker = item["ticker"]
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=p, interval=i)
            
            if len(hist) > 14:
                current_price = hist['Close'].iloc[-1]
                max_price = hist['High'].max()
                drop_from_max = ((current_price - max_price) / max_price) * 100
                
                # חישוב אינדיקטורים טכניים
                rsi = round(ta.momentum.rsi(hist['Close'], window=14).iloc[-1], 1)
                stoch = round(ta.momentum.stoch(hist['High'], hist['Low'], hist['Close'], window=14).iloc[-1], 1)
                mfi = round(ta.volume.money_flow_index(hist['High'], hist['Low'], hist['Close'], hist['Volume'], window=14).iloc[-1], 1)
                drop_printed = round(drop_from_max, 1)
                
                # בדיקת תנאי הסף הקשוחים לאיתות
                c_drop = drop_printed <= -15
                c_rsi = rsi <= 30
                c_stoch = stoch <= 20
                c_mfi = mfi <= 20
                
                score = sum([c_drop, c_rsi, c_stoch, c_mfi])
                
                # המרה לשפת מסחר חדה ומובנת
                if score == 0:
                    signal = "⚪ שוק רגיל (0/4)"
                elif score == 1:
                    signal = "🟡 גישושים ראשונים (1/4)"
                elif score == 2:
                    signal = "🟠 במעקב צמוד (2/4)"
                elif score == 3:
                    signal = "🚨 כוננות שיא (3/4)"
                else:
                    signal = "🔥 הדק נלחץ! (4/4)"
                
                data_list.append({
                    "סימבול": ticker,
                    "סקטור / מדד": item["category"],
                    "סוג הנייר": item["type"],
                    "מחיר אחרון": round(current_price, 2),
                    "ירידה מהשיא": drop_printed,
                    "RSI (14)": rsi,
                    "Stochastic": stoch,
                    "MFI (14)": mfi,
                    "🚦 סטטוס איתות משולב": signal,
                    "score_raw": score # עמודה מוסתרת לחישובים בלבד
                })
        except:
            continue
    return pd.DataFrame(data_list)

df = fetch_terminal_data(period, interval)

if not df.empty:
    # 6. יצירת כרטיסיות הייטק (KPIs) בראש העמוד
    total_alerts = len(df[df["score_raw"] >= 3])
    most_dropped = df.loc[df["ירידה מהשיא"].idxmin()]["סימבול"]
    max_drop_val = df["ירידה מהשיא"].min()
    
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">🚨 נכסים בכוננות / כניסה (3 ומעלה)</div><div class="kpi-value">{total_alerts} נכסים</div></div>', unsafe_allow_html=True)
    with kpi_col2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">📉 ההנחה הגדולה ביותר מהשיא</div><div class="kpi-value">{most_dropped} ({max_drop_val}%)</div></div>', unsafe_allow_html=True)
    with kpi_col3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">🔄 קצב עדכון דאטה סינתטי</div><div class="kpi-value">לייב (30 שניות)</div></div>', unsafe_allow_html=True)

    # 7. פונקציית צביעה מתקדמת - מותאמת ל-Dark Theme
    def color_terminal(row):
        styles = [''] * len(row)
        
        # צבעים רכים ופוספורסנטיים שלא שורפים את העין ברקע כהה
        alert_green = 'background-color: #064e3b; color: #34d399; font-weight: bold;'
        trigger_gold = 'background-color: #78350f; color: #fbbf24; font-weight: bold;'
        perfect_strike = 'background-color: #047857; color: #ffffff; font-weight: bold; border: 1px solid #34d399;'
        
        if row["ירידה מהשיא"] <= -15:
            styles[df.columns.get_loc("ירידה מהשיא")] = alert_green
        if row["RSI (14)"] <= 30:
            styles[df.columns.get_loc("RSI (14)")] = alert_green
        if row["Stochastic"] <= 20:
            styles[df.columns.get_loc("Stochastic")] = alert_green
        if row["MFI (14)"] <= 20:
            styles[df.columns.get_loc("MFI (14)")] = alert_green
            
        # צביעת עמודת הסטטוס על פי חומרת האיתות
        status = row["🚦 סטטוס איתות משולב"]
        if "4/4" in status:
            styles[df.columns.get_loc("🚦 סטטוס איתות משולב")] = perfect_strike
        elif "3/4" in status:
            styles[df.columns.get_loc("🚦 סטטוס איתות משולב")] = trigger_gold
            
        return styles

    # החלת העיצוב והסתרת עמודת העזר
    styled_df = df.style.apply(color_terminal, axis=1)
    
    # 8. הצגת הטבלה המרכזית הגדולה והמורחבת
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_order=["סימבול", "סקטור / מדד", "סוג הנייר", "מחיר אחרון", "ירידה מהשיא", "RSI (14)", "Stochastic", "MFI (14)", "🚦 סטטוס איתות משולב"],
        column_config={
            "סימבול": st.column_config.TextColumn("סימבול", help="טיקר הנכס בבורסה"),
            "מחיר אחרון": st.column_config.NumberColumn("מחיר אחרון", format="$%.2f"),
            "ירידה מהשיא": st.column_config.NumberColumn("ירידה מהשיא", format="%.1f%%", help="הנחה באחוזים מהפסגה הגבוהה ביותר שנמדדה לאורך התקופה."),
            "RSI (14)": st.column_config.NumberColumn("RSI (14)", help="מדד עוצמה יחסית. מתחת ל-30 מצביע על קפיץ מתוח ומכירות יתר קיצוניות."),
            "Stochastic": st.column_config.NumberColumn("Stochastic", help="מדד המיקום בטווח המחירים. מתחת ל-20 מראה שהמחיר שוכב על הרצפה הסטטיסטית שלו."),
            "MFI (14)": st.column_config.NumberColumn("MFI (14)", help="זרימת כסף משולבת נפח. מתחת ל-20 מעיד על בריחת נזילות רגעית לפני היפוך חזק."),
            "🚦 סטטוס איתות משולב": st.column_config.TextColumn("🚦 סטטוס איתות משולב", help="סיכום תנאי הברזל: כמה אינדיקטורים מתוך ה-4 נדלקו במקביל.")
        }
    )
else:
    st.warning("מערכת הנתונים בטעינה ראשונית...")

# 9. ספר החוקים האלגוריתמי בתחתית העמוד (למטה, מעוצב ומקצועי)
st.write("")
st.write("---")
st.markdown('### 📚 ספר החוקים של הטרמינל – איך מדייקים כניסות מנצחות?')

col_info1, col_info2 = st.columns(2)

with col_info1:
    st.markdown("""
    <div class="playbook-box">
        <h4>🎯 חוק הקונפלואנס (Confluence) - למה צריך 4/4?</h4>
        <p>מסחר בממונפות (x3) הוא חיה מסוכנת שמפרקת חשבונות אם נכנסים מוקדם מדי. הציון המשולב מונע ממך "לנחש" תחתית. 
        רק כאשר כל <b>ארבעת האלמנטים</b> (מחיר, מומנטום, מיקום בטווח, ונפח כסף) מסכימים פה אחד שהנכס נשחט לרצפה - הסטטוס הופך ל-<b>🔥 הדק נלחץ!</b>. זוהי נקודת הכניסה בעלת הסתברות ההצלחה הגבוהה ביותר.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="playbook-box" style="border-right-color: #a7f3d0;">
        <h4>💸 פילוסופיית המדדים בקצר וקולע</h4>
        <ul>
            <li><b>ירידה מהשיא:</b> מוודאת שאתה קונה במבצע, לא בשיא כל הזמנים.</li>
            <li><b>RSI:</b> מוודא שהמוכרים הגיעו לאפיסת כוחות מלאה.</li>
            <li><b>Stochastic:</b> מאתר את ה"רצפה הטכנית" של הימים האחרונים.</li>
            <li><b>MFI:</b> עוקב אחרי הכסף הגדול של המוסדיים – כשהוא מתחת ל-20, הוא מאותת שהם סיימו למכור.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col_info2:
    st.markdown("""
    <div class="playbook-box" style="border-right-color: #fbbf24;">
        <h4>⏱️ טקטיקת "הטיימפריים הכפול" לפריצה מושלמת</h4>
        <p>רוצה לשפר את הדיוק לרמת הפיקסל? השתמש בכפתור החלפת הזמן בראש העמוד בצורה הבאה:</p>
        <ol>
            <li>זהה בגרף <b>היומי (Daily)</b> נכס שנמצא בסטטוס מתקדם כמו <b>🚨 כוננות שיא (3/4)</b>.</li>
            <li>העבר את המערכת לגרף <b>שעתי (1 Hour)</b> או <b>15 דקות</b>.</li>
            <li>חכה שהגרף המהיר ידלק על <b>4/4</b> – זהו הניצוץ המדויק שמקדים את היפוך המגמה בגרף הגדול!</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
