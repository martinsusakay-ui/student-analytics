import pandas as pd

df = pd.read_csv("logs_interacoes_anon.csv", 
                 usecols=['eventname', 'action', 'component', 'timecreated'],
                 nrows=200000)

print("=== Top 20 Event ===")
print(df['eventname'].value_counts().head(20))

print("\n=== Top 10 Action ===")
print(df['action'].value_counts().head(10))

print("\n=== Top 10 Component ===")
print(df['component'].value_counts().head(10))

print("\n=== Rentang Waktu ===")
print(f"Dari: {pd.to_datetime(df['timecreated'].min(), unit='s')}")
print(f"Sampai: {pd.to_datetime(df['timecreated'].max(), unit='s')}")