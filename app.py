import streamlit as st
import yfinance as yf
import pandas as pd
import ta
from streamlit_autorefresh import st_autorefresh

# הגדרת דף אינטרנט רחב ונקי
st.set_page_config(page_title="Live Trading Screener", layout="wide")

# רענון אוטומטי של הדף בכל 30 שניות בשביל הלייב
st_autorefresh(interval=30000, key="datarefresh")

st.title("📊 מערכת מסחר מתקדמת - אישורי כניסה לממונפות")

# --- תיבת בחירת אינטרוול (טיימפריים) לדיוק כניסות ---
tf_choice = st.selectbox(
    "בחר מסגרת זמן לניתוח המדדים (Timeframe):",
    ["יומי (Daily)", "שעתי (1 Hour)", "מהיר (15 Minutes)"]
)

# מיפוי הבחירה להגדרות של Yahoo Finance
if tf_choice == "יומי (Daily)":
    period, interval = "3mo", "1d"
elif tf_choice == "שעתי (1 Hour)":
    period, interval = "1mo", "1h"
else:
    period, interval = "1wk", "15m"

st.write(f"הנתונים מחושבים כעת לפי נרות של: **{tf_choice}** (עדכון אוטומטי כל 30 שק')")

# מבנה נתונים חכם שמחבר בין נכס הבסיס לממונף שלו
ticker_details = [
    {"ticker": "QQQ", "category": "📈 נאסד\"ק", "type": "בסיס x1"},
    {"ticker": "TQQQ", "category": "📈 נאסד\"ק", "type": "ממונף x3"},
    {"ticker": "SOXX", "category": "💻 שבבים", "type": "בסיס x1"},
    {"ticker": "SOXL", "category": "💻 שבבים", "type": "ממונף x3"},
    {"ticker": "SPY", "category": "🇺🇸 S&P 500", "type": "בסיס x1"},
    {"ticker": "UPRO", "category": "🇺🇸 S&P 500", "type": "ממונף x3"},
    {"ticker": "XLF", "category": "💰 פיננסים", "type": "בסיס x1"},
    {"ticker": "FAS", "category": "💰 פיננסים", "type": "ממונף x3"},
]

@st.cache_data(ttl=15)
def get_live_data(p, i):
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
                
                # חישוב המדדים (מעוגלים מראש ל-1 ספרות אחרי הנקודה)
                rsi = round(ta.momentum.rsi(hist['Close'], window=14).iloc[-1], 1)
                stoch = round(ta.momentum.stoch(hist['High'], hist['Low'], hist['Close'], window=14).iloc[-1], 1)
                mfi = round(ta.volume.money_flow_index(hist['High'], hist['Low'], hist['Close'], hist['Volume'], window=14).iloc[-1], 1)
                drop_printed = round(drop_from_max, 1)
                
                # בדיקת תנאי ה"גם וגם וגם" של המשתמש
                cond_drop = drop_printed <= -15
                cond_rsi = rsi <= 30
                cond_stoch = stoch <= 20
                cond_mfi = mfi <= 20
                
                # סכימת כמות האישורים שנדלקו
                score = sum([cond_drop, cond_rsi, cond_stoch, cond_mfi])
                signal = "🔥 כניסה! (4/4)" if score == 4 else f"⏳ ממתין ({score}/4)"
                
                data_list.append({
                    "סימבול": ticker,
                    "מדד/סקטור": item["category"],
                    "סוג": item["type"],
                    "מחיר אחרון": round(current_price, 2),
                    "ירידה מהשיא": drop_printed,
                    "RSI (14)": rsi,
                    "Stochastic": stoch,
                    "MFI (14)": mfi,
                    "🎯 סיגנל משולב": signal
                })
        except Exception as e:
            continue
    return pd.DataFrame(data_list)

# שליפת הדאטה לפי הטיימפריים הנבחר
df = get_live_data(period, interval)

# פונקציית עיצוב צבעים חכמה
def style_row(row):
    # צבעי ברירת מחדל
    styles = [''] * len(row)
    
    # צבע ירוק פסטל עדין לאינדיקטורים בודדים שהגיעו ליעד
    green_cell = 'background-color: #d1fae5; color: #065f46; font-weight: bold;'
    
    if row["ירידה מהשיא"] <= -15:
        styles[df.columns.get_loc("ירידה מהשיא")] = green_cell
    if row["RSI (14)"] <= 30:
        styles[df.columns.get_loc("RSI (14)")] = green_cell
    if row["Stochastic"] <= 20:
        styles[df.columns.get_loc("Stochastic")] = green_cell
    if row["MFI (14)"] <= 20:
        styles[df.columns.get_loc("MFI (14)")] = green_cell
        
    # אם יש 4/4 אישורים - צובעים את תא הסיגנל בזהב/ירוק חזק ומנצנץ
    if row["🎯 סיגנל משולב"] == "🔥 כניסה! (4/4)":
        styles[df.columns.get_loc("🎯 סיגנל משולב")] = 'background-color: #059669; color: white; font-weight: bold;'
    else:
        styles[df.columns.get_loc("🎯 סיגנל משולב")] = 'color: #6b7280;' # אפור לממתין
        
    return styles

if not df.empty:
    # החלת העיצוב
    styled_df = df.style.apply(style_row, axis=1)
    
    # תצוגת הטבלה החדשה בסדר עמודות נכון ומדויק
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_order=["סימבול", "מדד/סקטור", "סוג", "מחיר אחרון", "ירידה מהשיא", "RSI (14)", "Stochastic", "MFI (14)", "🎯 סיגנל משולב"],
        column_config={
            "ירידה מהשיא": st.column_config.NumberColumn("ירידה מהשיא", format="%.1f%%", help="אחוז ירידה מהטופ של התקופה המוגדרת"),
            "מחיר אחרון": st.column_config.NumberColumn("מחיר אחרון", format="$%.2f"),
            "RSI (14)": st.column_config.NumberColumn("RSI (14)", help="מתחת ל-30: מכירת יתר קיצונית"),
            "Stochastic": st.column_config.NumberColumn("Stochastic", help="מתחת ל-20: מחיר ברצפת הטווח"),
            "MFI (14)": st.column_config.NumberColumn("MFI (14)", help="מתחת ל-20: מחזור כספים מצביע על היפוך קרוב")
        }
    )
else:
    st.warning("ממתין לקבלת נתונים מהבורסה...")
