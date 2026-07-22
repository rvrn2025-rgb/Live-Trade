import streamlit as st
import yfinance as yf
import pandas as pd
import ta
from streamlit_autorefresh import st_autorefresh

# הגדרת דף אינטרנט רחב ונקי
st.set_page_config(page_title="Live Trading Screener", layout="wide")

# רענון אוטומטי של הדף בכל 30 שניות בשביל הלייב
st_autorefresh(interval=30000, key="datarefresh")

# עיצוב כותרות וטבלה מימין לשמאל
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    th { text-align: right !important; }
    td { text-align: right !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 מערכת מסחר מתקדמת - אישורי כניסה לממונפות")
st.write("הנתונים מתעדכנים אוטומטית בכל 30 שניות. רחף עם העכבר מעל כותרות העמודות (סימן השאלה) כדי לראות הסבר על המדד.")

# מבנה נתונים חכם שמחבר בין נכס הבסיס לממונף שלו
ticker_details = [
    {"ticker": "QQQ", "category": "📈 נאסד\"ק (Nasdaq)", "type": "נכס בסיס (x1)"},
    {"ticker": "TQQQ", "category": "📈 נאסד\"ק (Nasdaq)", "type": "ממונף (x3)"},
    {"ticker": "SOXX", "category": "💻 שבבים (Semiconductors)", "type": "נכס בסיס (x1)"},
    {"ticker": "SOXL", "category": "💻 שבבים (Semiconductors)", "type": "ממונף (x3)"},
    {"ticker": "SPY", "category": "🇺🇸 S&P 500", "type": "נכס בסיס (x1)"},
    {"ticker": "UPRO", "category": "🇺🇸 S&P 500", "type": "ממונף (x3)"},
    {"ticker": "XLF", "category": "💰 פיננסים (Finance)", "type": "נכס בסיס (x1)"},
    {"ticker": "FAS", "category": "💰 פיננסים (Finance)", "type": "ממונף (x3)"},
]

@st.cache_data(ttl=15)
def get_live_data():
    data_list = []
    for item in ticker_details:
        ticker = item["ticker"]
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo", interval="1d")
            
            if len(hist) > 14:
                current_price = hist['Close'].iloc[-1]
                max_price = hist['High'].max()
                drop_from_max = ((current_price - max_price) / max_price) * 100
                
                # חישוב המדדים
                rsi = ta.momentum.rsi(hist['Close'], window=14).iloc[-1]
                stoch = ta.momentum.stoch(hist['High'], hist['Low'], hist['Close'], window=14).iloc[-1]
                mfi = ta.volume.money_flow_index(hist['High'], hist['Low'], hist['Close'], hist['Volume'], window=14).iloc[-1]
                
                data_list.append({
                    "סקטור / מדד": item["category"],
                    "סימבול": ticker,
                    "סוג": item["type"],
                    "מחיר אחרון": round(current_price, 2),
                    "ירידה מהשיא": round(drop_from_max, 1),
                    "RSI (14)": round(rsi, 1),
                    "Stochastic": round(stoch, 1),
                    "MFI (14)": round(mfi, 1)
                })
        except Exception as e:
            continue
    return pd.DataFrame(data_list)

# פונקציית צביעה - ירוק פסטל מקצועי ויוקרתי (Tailwind Emerald)
def color_picker(val, column_name):
    green_style = 'background-color: #d1fae5; color: #065f46; font-weight: bold;'
    if column_name == "ירידה מהשיא" and val <= -15:
        return green_style
    elif column_name == "RSI (14)" and val <= 30:
        return green_style
    elif column_name == "Stochastic" and val <= 20:
        return green_style
    elif column_name == "MFI (14)" and val <= 20:
        return green_style
    return ''

df = get_live_data()

if not df.empty:
    # החלת סגנון צבעים
    styled_df = df.style.apply(lambda x: [color_picker(v, x.name) for v in x], axis=0)
    
    # הצגת הטבלה עם הגדרות תצוגה מתקדמות, הסברים בריחוף והעלמת אינדקס
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ירידה מהשיא": st.column_config.NumberColumn("ירידה מהשיא", format="%.1f%%", help="אחוז הירידה הנוכחי מהמחיר הגבוה ביותר ב-3 החודשים האחרונים."),
            "מחיר אחרון": st.column_config.NumberColumn("מחיר אחרון", format="$%.2f"),
            "RSI (14)": st.column_config.NumberColumn("RSI (14)", help="מדד העוצמה היחסית (Relative Strength Index). ערך מתחת ל-30 מעיד על מכירת יתר קיצונית בגרף היומי."),
            "Stochastic": st.column_config.NumberColumn("Stochastic", help="מתנד סטוכסטי (Stochastic Oscillator). ערך מתחת ל-20 מראה שהמחיר נמצא כרגע בקרקעית של טווח התנועה האחרון שלו."),
            "MFI (14)": st.column_config.NumberColumn("MFI (14)", help="מדד זרימת הכסף (Money Flow Index). משלב נפח מסחר יחד עם מחיר. ערך מתחת ל-20 מעיד על יציאת כספים קיצונית ופוטנציאל גבוה להיפוך למעלה.")
        }
    )
else:
    st.warning("ממתין לקבלת נתונים מהבורסה...")
