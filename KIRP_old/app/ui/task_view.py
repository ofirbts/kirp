import streamlit as st
import requests
from app.core.persistence import PersistenceManager

def render_task_pipeline():
    st.subheader("📋 Task Pipeline")
    st.caption("Tasks automatically identified from your conversations")
    
    # שליפת משימות שמחכות לאישור מה-DB
    pending_tasks = PersistenceManager.get_pending_approvals()
    
    if not pending_tasks:
        st.info("No active tasks in pipeline.")
        return

    for task in pending_tasks:
        col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
        
        with col1:
            # Checkbox לסימון (כמו בתמונה)
            is_selected = st.checkbox("", key=f"check_{task['id']}")
            
        with col2:
            st.markdown(f"**{task['data'].get('task')}**")
            st.caption(f"🕒 {task['timestamp']}")
            
        with col3:
            # כפתור אישור שמפעיל את ה-API שבנינו קודם
            if st.button("Approve", key=f"btn_{task['id']}"):
                response = requests.post(
                    "http://localhost:8000/governance/approve", 
                    json={"event_id": task['id']}
                )
                if response.status_code == 200:
                    st.success("Sent to Notion!")
                    st.rerun()

    st.divider()
    if st.button("🔄 Sync with Google Calendar (Real)"):
        st.write("Syncing tasks to Calendar...")
        # כאן יבוא החיבור ל-GoogleCalendarClient שלך
