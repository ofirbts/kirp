import streamlit as st
from app.agent.agent import agent

st.title("🧠 KIRP – Your Personal Intelligence Layer")
st.caption("Memory • Decisions • Reflection")

question = st.text_input("What’s on your mind?")

if question:
    with st.spinner("Thinking..."):
        result = st.run(agent.agent_query(question))
    st.markdown("### 💬 Agent Answer")
    st.success(result["answer"])
    st.caption(f"Confidence: {round(result.get('confidence',0),2)}")
