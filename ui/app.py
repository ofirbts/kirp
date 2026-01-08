import streamlit as st
from api import get_health, ingest, get_tasks, weekly_summary, ask, get_status

st.set_page_config(page_title="KIRP", layout="centered")
st.title("🧠 KIRP – Personal Intelligence")
col1, col2 = st.columns([3,1])
try:
    status = get_status()
except:
    status = {"memories_loaded": "API DOWN"}

col1.metric("🧠 Memories Loaded", status.get("memories_loaded", 0))
col2.metric("📋 Tasks", status.get("tasks_count", 0))


# --- Health ---
with st.expander("🩺 System status"):
    try:
        health = get_health()
        st.json(health)
        st.json(status)
        st.success("✅ Server LIVE")
    except:
        st.error("❌ Server down")

# --- Ingest ---
st.header("📥 Add Memory")
text = st.text_area("What happened?", height=80, placeholder="הכנס זיכרון חדש כאן...")

if st.button("💾 Save Memory") and text.strip():
    try:
        result = ingest(text)
        chunks = result.get("chunks_added", 1)
        st.success(f"✅ Added {chunks} memory chunks!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ API Error: {e}")

# --- Tasks ---
st.header("📋 Tasks")
if st.button("🔄 Load Tasks"):
    try:
        response = get_tasks()

        # תיקון: שימוש במפתח ישיר במקום get()
        tasks = response["tasks"]

        if tasks:
            for task in tasks:
                title = task.get("title", "No title")
                status = task.get("status", "unknown")
                st.write(f"• **{title}** — {status}")
        else:
            st.info("📭 No tasks found")

    except Exception as e:
        st.error(f"❌ Tasks error: {e}")

# --- Weekly Summary ---
st.header("📅 Weekly Summary")
if st.button("✨ Generate Summary"):
    try:
        summary = weekly_summary()
        st.success("✅ Summary ready!")
        st.json(summary)
    except Exception as e:
        st.error(f"❌ Summary error: {e}")

# --- Ask KIRP ---
st.header("🔍 Ask KIRP")
question = st.text_input("שאל שאלה", placeholder="הכנס כאן שאלה ..")

if question and st.button("💭 Ask"):
    with st.spinner("KIRP חושב..."):
        try:
            answer = ask(question)
            st.markdown("### 💬 **תשובה:**")
            st.write(answer.get("answer", str(answer)))
        except Exception as e:
            st.error(f"❌ KIRP error: {e}")
