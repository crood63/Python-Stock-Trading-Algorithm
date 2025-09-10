import yfinance as yf
import pandas as pd

name = 'SPY'

try:
    print(f"Fetching {name}...")
    data = yf.download(f"{name}", period="20y")
    if not data.empty:
        data.to_csv(f"./EOD/{name}.csv")
    else:
        print(f"No data for {name}")
except Exception as e:
    print(f"{name} ===> {e}")