import streamlit as st
import yfinance as yf
import pandas as pd
import ta
from streamlit_autorefresh import st_autorefresh

# הגדרת דף אינטרנט רחב ונקי
st.set_page_config(page_title="Live Trading Screener", layout="wide")

# רענון אוטומטי של הדף בכל 30 שניות בשביל הלייב
st_autorefresh(interval=30000, key="datarefresh")

st.title("📊 מערכת מסחר חכמה - אישורי כניסה לממונפות")
st.write("הנתונים מתעדכנים אוטומטית בכל 30 שניות. תאים בירוק מצביעים על הזדמנות (מכירת יתר).")

# רשימת הסימבולים (נכס בסיס וממונף)
tickers = ['QQQ', 'TQQQ', 'SOXX', 'SOXL', 'SPY', 'UPRO', 'XLF', 'FAS']

@st.cache_data(ttl=15)  # שומר את הדאטה בזיכרון ל-15 שניות כדי למנוע חסימות
def get_live_data():
    data_list = []
    for ticker in tickers:
        try:
            # משיכת נתונים יומיים של ה-3 חודשים האחרונים בשביל אינדיקטורים של 14 יום
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo", interval="1d")
            
            if len(hist) > 14:
                current_price = hist['Close'].iloc[-1]
                max_price = hist['High'].max()
                drop_from_max = ((current_price - max_price) / max_price) * 100
                
                # חישוב אינדיקטורים מתקדמים בעזרת ספריית ta
                rsi = ta.momentum.rsi(hist['Close'], window=14).iloc[-1]
                stoch = ta.momentum.stoch(hist['High'], hist['Low'], hist['Close'], window=14).iloc[-1]
                mfi = ta.volume.money_flow_index(hist['High'], hist['Low'], hist['Close'], hist['Volume'], window=14).iloc[-1]
                
                data_list.append({
                    "סימבול": ticker,
                    "מחיר אחרון": round(current_price, 2),
                    "ירידה מהשיא": round(drop_from_max, 1),
                    "RSI (14)": round(rsi, 1),
                    "Stochastic": round(stoch, 1),
                    "MFI (14)": round(mfi, 1)
                })
        except Exception as e:
            continue
    return pd.DataFrame(data_list)

# פונקציית צביעה לרמזור חכם (משנה את הרקע לירוק אם התנאי מבשיל)
def color_picker(val, column_name):
    if column_name == "ירידה מהשיא" and val <= -15:  # ירידה של 15% ומעלה
        return 'background-color: #2ecc71; color: white; font-weight: bold;'
    elif column_name == "RSI (14)" and val <= 30:     # RSI מתחת ל-30
        return 'background-color: #2ecc71; color: white; font-weight: bold;'
    elif column_name == "Stochastic" and val <= 20:   # סטוכסטיק מתחת ל-20
        return 'background-color: #2ecc71; color: white; font-weight: bold;'
    elif column_name == "MFI (14)" and val <= 20:     # זרימת כסף מתחת ל-20
        return 'background-color: #2ecc71; color: white; font-weight: bold;'
    return ''

df = get_live_data()

if not df.empty:
    # החלת פונקציית הרמזור על הטבלה
    styled_df = df.style.apply(lambda x: [color_picker(v, x.name) for v in x], axis=0)
    styled_df = styled_df.format({"ירידה מהשיא": "{:.1f}%"})
    
    # הצגת הטבלה המעוצבת
    st.dataframe(styled_df, use_container_width=True)
else:
    st.warning("ממתין לקבלת נתונים מהבורסה...")
