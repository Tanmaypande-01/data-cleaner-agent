"""Builds a deliberately messy sales file so the cleaner has something to chew on."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 150

cities = ["New York", "NY", "N.Y.", "new york", "Mumbai", "mumbai ", "Pune", "PUNE", "Delhi", "Delhi", "Bangalore", "Bangalor"]
names = ["rahul shah", "PRIYA PATIL", "Amit  Kulkarni", "sneha joshi", "Vikram Rao", "neha desai", "Karan Mehta", "Anita Nair"]
order_dates = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 300, n), unit="D")
ship_dates = order_dates + pd.to_timedelta(rng.integers(1, 8, n), unit="D")

fmt_choices = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]
order_text = [d.strftime(fmt_choices[i % 3]) for i, d in enumerate(order_dates)]
ship_text = [d.strftime("%Y-%m-%d") for d in ship_dates]

qty = rng.integers(1, 20, n).astype(object)
price = rng.integers(200, 2500, n).astype(object)
price = [f"₹{p:,}" if i % 4 == 0 else (f"${p}" if i % 7 == 0 else str(p)) for i, p in enumerate(price)]
cost = (rng.integers(100, 1500, n)).astype(object)

df = pd.DataFrame({
    "Order ID": [f"ORD{1000 + i}" for i in range(n)],
    "Customer ID": rng.integers(1, 9, n),
    "Order Date": order_text,
    "Ship Date": ship_text,
    "Customer Name": [names[i % len(names)] for i in range(n)],
    "City ": [cities[i % len(cities)] for i in range(n)],
    "Email": [f"user{i}@mail.com" for i in range(n)],
    "Quantity": qty,
    "Unit Price": price,
    "Cost": cost,
    "Age": rng.integers(18, 70, n).astype(object),
    "Is Member": ["Yes" if i % 3 else "no" for i in range(n)],
    "Country": "India",
    "Notes": np.nan,
})

# sprinkle in the usual problems
df.loc[[5, 17, 40], "Quantity"] = [None, "N/A", None]
df.loc[[8, 60], "Age"] = [None, 250]
df.loc[12, "Quantity"] = -4
df.loc[30, "Unit Price"] = "99999"
df.loc[[22, 90], "Email"] = ["not-an-email", "bad@@mail"]
df.loc[3, "Ship Date"] = "2023-12-01"
df.loc[[10, 70], "Customer Name"] = [None, "-"]
df = pd.concat([df, df.iloc[[2, 2, 9]]], ignore_index=True)       # exact duplicates
df = pd.concat([df, pd.DataFrame([{}])], ignore_index=True)        # one fully empty row
df.to_csv("sample_data/messy_sales.csv", index=False)

segments = pd.DataFrame({
    "customer id": range(1, 9),
    "segment": ["Gold", "Silver", "Gold", "Bronze", "Silver", "Gold", "Bronze", "Silver"],
    "Loyalty Points": [900, 450, 1200, 80, 500, 1500, 60, 430],
})
segments.to_csv("sample_data/customer_segments.csv", index=False)
print("sample files written:", len(df), "rows")
