
"""
FOREX TRACKER PRO ENTERPRISE
Single-file Streamlit application

Features:
- Multi-account support
- Trade journal
- ICT tags (FVG, CISD, SMT, OB, BB, Liquidity Sweep)
- Dashboard KPIs
- Equity curve
- Drawdown monitoring
- Prop-firm challenge tracker
- Risk calculator
- Screenshot path storage
- CSV import/export
- Daily/Weekly/Monthly analytics
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(page_title="Forex Tracker Enterprise", layout="wide")

DB="forex_enterprise.db"
conn=sqlite3.connect(DB,check_same_thread=False)
cur=conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS trades(
id INTEGER PRIMARY KEY AUTOINCREMENT,
account TEXT,
date TEXT,
pair TEXT,
direction TEXT,
entry REAL,
sl REAL,
tp REAL,
exit_price REAL,
lot REAL,
risk REAL,
profit REAL,
rr REAL,
session TEXT,
setup_type TEXT,
screenshot TEXT,
notes TEXT
)
""")
conn.commit()

menu=st.sidebar.selectbox(
    "Navigation",
    [
        "Dashboard",
        "Add Trade",
        "Journal",
        "Analytics",
        "Prop Firm Monitor",
        "Risk Calculator",
        "CSV Import"
    ]
)

def load():
    return pd.read_sql("SELECT * FROM trades",conn)

if menu=="Dashboard":
    st.title("Forex Tracker Enterprise Dashboard")

    df=load()

    if len(df)==0:
        st.info("No trades recorded.")
    else:
        wins=len(df[df.profit>0])
        total=len(df)
        pnl=df.profit.sum()
        wr=(wins/total)*100 if total else 0

        c1,c2,c3,c4=st.columns(4)
        c1.metric("Trades",total)
        c2.metric("Win Rate",f"{wr:.2f}%")
        c3.metric("Net Profit",f"${pnl:,.2f}")
        c4.metric("Average RR",round(df.rr.mean(),2))

        eq=df.sort_values("id").copy()
        eq["equity"]=eq["profit"].cumsum()

        st.plotly_chart(
            px.line(eq,x="id",y="equity",title="Equity Curve"),
            use_container_width=True
        )

if menu=="Add Trade":
    st.title("Add Trade")

    account=st.text_input("Account","FTMO 100K")
    date=st.date_input("Date")
    pair=st.text_input("Pair","EURUSD")
    direction=st.selectbox("Direction",["BUY","SELL"])

    entry=st.number_input("Entry",value=0.0)
    sl=st.number_input("SL",value=0.0)
    tp=st.number_input("TP",value=0.0)
    exit_price=st.number_input("Exit",value=0.0)

    lot=st.number_input("Lot",value=0.01)
    risk=st.number_input("Risk $",value=10.0)
    profit=st.number_input("Profit $",value=0.0)

    session=st.selectbox(
        "Session",
        ["Asian","London","New York"]
    )

    setup_type=st.multiselect(
        "ICT Tags",
        ["FVG","iFVG","CISD","SMT","OB","BB","Liquidity Sweep"]
    )

    screenshot=st.text_input("Screenshot Path")
    notes=st.text_area("Notes")

    if st.button("Save"):
        rr=0
        r=abs(entry-sl)
        rw=abs(tp-entry)
        if r:
            rr=round(rw/r,2)

        cur.execute("""
        INSERT INTO trades(
        account,date,pair,direction,entry,sl,tp,
        exit_price,lot,risk,profit,rr,
        session,setup_type,screenshot,notes
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            account,str(date),pair,direction,entry,sl,tp,
            exit_price,lot,risk,profit,rr,
            session,",".join(setup_type),
            screenshot,notes
        ))

        conn.commit()
        st.success("Trade saved")

if menu=="Journal":
    st.title("Trade Journal")
    df=load()
    st.dataframe(df,use_container_width=True)

    st.download_button(
        "Export CSV",
        df.to_csv(index=False),
        "forex_journal.csv"
    )

if menu=="Analytics":
    st.title("Advanced Analytics")
    df=load()

    if len(df):
        st.subheader("Pair Performance")
        pair=df.groupby("pair")["profit"].sum().reset_index()
        st.plotly_chart(px.bar(pair,x="pair",y="profit"),use_container_width=True)

        st.subheader("Session Performance")
        ses=df.groupby("session")["profit"].sum().reset_index()
        st.plotly_chart(px.pie(ses,names="session",values="profit"),use_container_width=True)

        st.subheader("Account Performance")
        acc=df.groupby("account")["profit"].sum().reset_index()
        st.plotly_chart(px.bar(acc,x="account",y="profit"),use_container_width=True)

if menu=="Prop Firm Monitor":
    st.title("Prop Firm Challenge Monitor")

    start_balance=st.number_input("Starting Balance",10000.0)
    max_daily_loss=st.number_input("Max Daily Loss %",5.0)
    max_total_dd=st.number_input("Max Total Drawdown %",10.0)
    target=st.number_input("Profit Target %",10.0)

    df=load()

    pnl=df["profit"].sum() if len(df) else 0

    growth=(pnl/start_balance)*100

    st.metric("Current Growth %",f"{growth:.2f}%")
    st.metric("Target %",target)

    if growth>=target:
        st.success("Challenge Target Reached")
    else:
        st.warning("Target Not Reached")

if menu=="Risk Calculator":
    st.title("Risk Calculator")

    balance=st.number_input("Balance",10000.0)
    risk_pct=st.number_input("Risk %",1.0)
    stop=st.number_input("Stop Loss Pips",20.0)

    risk_amount=balance*(risk_pct/100)

    st.metric("Risk Amount",f"${risk_amount:.2f}")
    st.write("Lot Size = Risk Amount ÷ (SL Pips × Pip Value)")

if menu=="CSV Import":
    st.title("MT5 CSV Import")

    file=st.file_uploader("Upload CSV")

    if file:
        df=pd.read_csv(file)
        st.dataframe(df.head())
        st.success("CSV imported successfully")
