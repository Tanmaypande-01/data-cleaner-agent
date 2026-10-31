"""Builds an extremely dirty Excel workbook to stress-test every cleaning step."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(11)
n = 500

cities = ["New York", "NY", "N.Y.", "new york", "NEW YORK ", "Mumbai", "mumbai", " Mumbai", "MUMBAI", "Pune", "pune",
          "PUNE ", "Delhi", "delhi", "New Delhi", "Bangalore", "Bangalor", "bangalore", "Hyderabad", "Hyderbad", "Chennai", "chennai "]
first = ["rahul", "PRIYA", "Amit", "sneha", "Vikram", "neha", "KARAN", "anita", "Rohan", "pooja", "Sanjay", "meera"]
last = ["shah", "PATIL", "Kulkarni", "joshi", "Rao", "desai", "mehta", "NAIR", "Iyer", "Jain", "Pawar", "kale"]
products = ["Laptop", "laptop ", "LAPTOP", "Mobile", "mobile", "Tablet", "Headphones", "Head Phones", "Monitor", "Keyboard", "keyboard."]
channels = ["Online", "online", "ONLINE ", "Store", "store", "In-Store", "Instore", "Phone", "phone"]

order = pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 700, n), unit="D")
ship = order + pd.to_timedelta(rng.integers(1, 10, n), unit="D")
formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%d.%m.%Y", "%d %B %Y", "%b %d, %Y"]
order_txt = [d.strftime(formats[i % len(formats)]) for i, d in enumerate(order)]
ship_txt = [d.strftime(formats[(i + 2) % len(formats)]) for i, d in enumerate(ship)]

qty = rng.integers(1, 15, n)
unit_price = rng.integers(300, 4000, n)
price_txt = []
for i, p in enumerate(unit_price):
    price_txt.append([f"₹{p:,}", f"Rs {p}", f"${p}", f"{p:,}.00", str(p), f" {p} "][i % 6].replace("Rs ", "₹"))
revenue = qty * unit_price
cost = (revenue * rng.uniform(0.5, 0.9, n)).round(0)

df = pd.DataFrame({
    " Order ID ": [f"ORD-{20000 + i}" for i in range(n)],
    "Customer ID": rng.integers(1, 41, n),
    "Order Date": order_txt,
    "SHIP date": ship_txt,
    "Full Name": [f"{first[i % 12]} {last[(i * 7) % 12]}" for i in range(n)],
    "City": [cities[(i * 5) % len(cities)] for i in range(n)],
    "E-mail": [f"User{i}@Mail.COM" if i % 3 else f"user{i}@mail.com " for i in range(n)],
    "Phone": [f"09{rng.integers(100000000, 999999999)}" for _ in range(n)],
    "Pin Code": [f"{rng.integers(1, 9)}{rng.integers(10000, 99999)}" if i % 9 else f"0{rng.integers(1000, 9999)}" for i in range(n)],
    "Product": [products[i % len(products)] for i in range(n)],
    "Channel": [channels[(i * 3) % len(channels)] for i in range(n)],
    "Quantity": qty.astype(object),
    "Unit Price": price_txt,
    "Revenue": [f"{r:,}" for r in revenue],
    "Cost": cost.astype(object),
    "Age": rng.integers(18, 75, n).astype(object),
    "Is Member?": [["Yes", "no", "TRUE", "false", "YES", "No"][i % 6] for i in range(n)],
    "Country": "India",
    "Remarks": [None] * n,
    "Feedback Score": [rng.integers(1, 6) if i % 5 == 0 else None for i in range(n)],
})

fake_blank = ["N/A", "n/a", "-", "--", "NULL", "none", "?", "missing", "  ", ""]
for col in ["Quantity", "Unit Price", "Age", "City", "Full Name", "Revenue", "Cost", "Product", "Channel"]:
    idx = rng.choice(n, 18, replace=False)
    df.loc[idx, col] = [fake_blank[i % len(fake_blank)] for i in range(len(idx))]
for col in ["Order Date", "SHIP date", "E-mail"]:
    df.loc[rng.choice(n, 10, replace=False), col] = None

# nasty values
df.loc[[3, 44, 99, 250], "Quantity"] = [-5, -20, 0, -1]
df.loc[[7, 120], "Unit Price"] = ["-1500", "-300"]
df.loc[[15, 160, 300], "Age"] = [999, -4, 150]
df.loc[[21, 321], "Unit Price"] = ["9999999", "8,500,000"]
df.loc[[33, 400], "Quantity"] = [5000, 9000]
df.loc[[55, 56, 57, 58], "E-mail"] = ["no-at-sign.com", "bad@@mail.com", "x@y", "@nouser.com"]
df.loc[[70, 71, 72], "SHIP date"] = ["2020-01-01", "01/01/2019", "15-Feb-2018"]
df.loc[[80, 81], "Order Date"] = ["not a date", "31/02/2024"]

# duplicates: exact, and "near" duplicates that differ only by case/spaces
df = pd.concat([df, df.iloc[[2, 2, 2, 9, 9, 30, 100, 101]]], ignore_index=True)
near = df.iloc[[5, 6, 7]].copy()
near["City"] = near["City"].astype(str).str.upper() + "  "
near["Full Name"] = near["Full Name"].astype(str).str.lower()
df = pd.concat([df, near], ignore_index=True)

# fully empty rows scattered around
for pos in (50, 200, 420, 480):
    df = pd.concat([df.iloc[:pos], pd.DataFrame([{}]), df.iloc[pos:]], ignore_index=True)
df = df.sample(frac=1, random_state=3).reset_index(drop=True)   # shuffle everything

# second sheet: customer master (with its own mess and repeated keys)
customers = pd.DataFrame({
    "customer id": list(range(1, 41)) + [5, 12, 12],
    "Segment ": (["Gold", "silver", "BRONZE", "Gold", "Silver"] * 8) + ["Gold", "Silver", "gold"],
    "Loyalty Points": [f"{rng.integers(0, 3000):,}" for _ in range(43)],
    "Joined On": [(pd.Timestamp("2018-01-01") + pd.Timedelta(days=int(d))).strftime(formats[i % 4])
                  for i, d in enumerate(rng.integers(0, 2000, 43))],
    "Region": ["West", "west ", "North", "South", "East"] * 8 + ["West", "North", "N/A"],
})

# third sheet: wide monthly table for the unpivot test
wide = pd.DataFrame({
    "Store": ["Pune", "pune ", "Mumbai", "Delhi", "Chennai", "Delhi"],
    "Jan Sales": ["₹1,200", "1500", "2,000", "N/A", "900", "2,000"],
    "Feb Sales": ["1,100", "1700", "2,300", "1,000", "-", "2,300"],
    "Mar Sales": ["1,400", "1,600", "2,100", "1,200", "950", "2,100"],
    "Apr Sales": ["1,350", "1800", "2,500", "1,100", "1,000", "2,500"],
})

with pd.ExcelWriter("extreme_messy_data.xlsx", engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Sales_Orders", index=False)
    customers.to_excel(writer, sheet_name="Customers", index=False)
    wide.to_excel(writer, sheet_name="Monthly_Wide", index=False)
print("rows in Sales_Orders:", len(df))
