# ui/app.py - ללא Pylance warnings
import streamlit as st
from api import get_health, ingest, get_tasks, weekly_summary, ask  # explicit imports!

st.set_page_config(page_title="KIRP", layout="centered")
st.title("🧠 KIRP – Personal Intelligence")

# --- Health ---
with st.expander("🩺 System status"):
    try:
        st.json(get_health())
    except:
        st.error("❌ Server down")

# --- Ingest ---
st.header("📥 Add Memory")
text = st.text_area("What happened?", height=80)

if st.button("💾 Save memory") and text.strip():
    try:
        ingest(text)
        st.success("✅ Memory saved!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ {e}")

# --- Tasks ---
st.header("📋 Tasks")
if st.button("🔄 Load tasks"):
    try:
        tasks = get_tasks()
        if tasks:
            for i, t in enumerate(tasks):
                st.checkbox(f"[{i+1}] {t.get('title', 'No title')}", key=f"task_{i}")
        else:
            st.info("אין משימות עדיין")
    except Exception as e:
        st.warning(f"⚠️ Tasks: {str(e)[:100]}...")

# --- Weekly Summary ---
st.header("📅 Weekly Summary")
if st.button("✨ Generate summary"):
    try:
        summary = weekly_summary()
        st.success("✅ Summary ready!")
        st.markdown(summary.get("summary", summary.get("content", str(summary))))
    except Exception as e:
        st.warning(f"⚠️ Summary: {str(e)[:100]}...")

# --- Ask KIRP ---
st.header("🔍 Ask KIRP")
question = st.text_input("שאל שאלה")
if question and st.button("💭 Think"):
    with st.spinner("מחשב..."):
        try:
            answer = ask(question)
            st.markdown("### 💬 **תשובה:**")
            st.write(answer.get("answer", answer))
        except Exception as e:
            st.error(f"❌ Query: {e}")
