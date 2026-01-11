import streamlit as st
import requests

API_URL = "http://localhost:8000/agent/query"

st.set_page_config(page_title="KIRP", layout="centered")

st.title("🧠 KIRP – Personal Intelligence")
st.caption("Memory • Decisions • Reflection")

question = st.text_input("Ask something meaningful")

if question:
    with st.spinner("Thinking..."):
        res = requests.post(API_URL, json={"question": question}).json()

    if res.get("status") == "error":
        st.error(res.get("detail"))
    else:
        st.markdown("### 💬 Answer")
        st.success(res.get("answer", "No answer"))

        st.metric("Confidence", res.get("confidence", 0))

        with st.expander("🔍 Full Trace"):
            st.json(res)
