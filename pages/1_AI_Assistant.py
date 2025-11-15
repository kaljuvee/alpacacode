import streamlit as st
import os
st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 AI Strategy Assistant")
st.info("AI Assistant powered by XAI - Define and test strategies on the fly.")
st.markdown("Set XAI_API_KEY environment variable to enable AI features.")
if not os.getenv("XAI_API_KEY"):
    st.warning("XAI_API_KEY not set. Please configure in .env file.")
