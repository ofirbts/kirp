import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="KIRP Intelligence", layout="wide")

BASE_URL = "http://localhost:8000"

def call_api(method, endpoint, json=None):
    try:
        if method == "GET":
            return requests.get(f"{BASE_URL}/{endpoint}").json()
        return requests.post(f"{BASE_URL}/{endpoint}", json=json).json()
    except:
        return None

st.title("🧠 KIRP Control Center")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Ingest")
    txt = st.text_input("מידע חדש:")
    if st.button("שמור"):
        call_api("POST", "ingest/", json={"text": txt})
        st.success("נשמר!")

with col2:
    st.subheader("🔍 Query")
    q = st.text_input("שאלה:")
    if st.button("שאל"):
        res = call_api("POST", "query/", json={"query": q})
        if res:
            st.info(f"Answer: {res.get('answer_text')}")
            # תצוגת Intent ו-Effects (משימה 7)
            with st.expander("Show Logic (Intent & Effects)"):
                st.json(res)

st.divider()
st.subheader("📜 Recent Events")
events = call_api("GET", "debug/events")
if events:
    st.table(pd.DataFrame(events).tail(5))
