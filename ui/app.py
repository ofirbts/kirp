import requests
import streamlit as st

API = "http://localhost:8000"

st.title("🧠 KIRP AI")

question = st.text_input("Ask KIRP")

if st.button("Ask"):
    res = requests.post(f"{API}/query/", json={"question": question})
    st.write(res.json()["answer"])

st.divider()

if st.button("Weekly Summary"):
    res = requests.post(f"{API}/intelligence/weekly-summary")
    st.json(res.json())
