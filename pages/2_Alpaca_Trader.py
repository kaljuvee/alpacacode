import streamlit as st
import os
st.set_page_config(page_title="Alpaca Trader", page_icon="🦙", layout="wide")
st.title("🦙 Alpaca Trader")
st.info("Paper and live trading with Alpaca Markets API")
st.markdown("Configure ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY in .env file.")
if not os.getenv("ALPACA_PAPER_API_KEY"):
    st.warning("Alpaca API keys not configured. Please set in .env file.")
