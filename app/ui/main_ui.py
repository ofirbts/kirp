import streamlit as st
import requests
import pandas as pd
import time

# הגדרת כתובת ה-Backend בתוך רשת ה-Docker
API_URL = "http://kirp-api:8000"

# הגדרות תצורה של Streamlit
st.set_page_config(
    page_title="KIRP Intelligence OS",
    page_icon="🧠",
    layout="wide"
)

# פונקציית עזר לשליחת בקשות API בצורה בטוחה
def call_api(method, endpoint, data=None):
    try:
        url = f"{API_URL}/{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        return None

# --- מנגנון LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🧠 KIRP Intelligence OS")
    st.subheader("מערכת ניהול ידע ותובנות אוטונומית")
    
    with st.container(border=True):
        user_id = st.text_input("מזהה משתמש (User ID)", placeholder=" שלח/י מזהה ייחודי")
        password = st.text_input("סיסמה", type="password")
        
        if st.button("התחבר למערכת", use_container_width=True):
            if user_id: # כאן אפשר להוסיף לוגיקת אימות מול DB בעתיד
                st.session_state.user_id = user_id
                st.session_state.logged_in = True
                st.success("מתחבר...")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("נא להזין מזהה משתמש")
    st.stop() # עוצר את הרצת שאר הדף עד להתחברות

# --- SIDEBAR (תפריט ניווט) ---
with st.sidebar:
    st.title("🧠 KIRP OS")
    st.write(f"👤 מחובר כ: **{st.session_state.user_id}**")
    st.divider()
    
    # בחירת עמוד
    page = st.radio(
        "ניווט",
        ["דף הבית (Dashboard)", "שאילתת ידע (Query)", "תובנות עסקיות (Insights)", "ניהול סוכנים (Agents)"]
    )
    
    st.divider()
    if st.button("🔄 רענן נתונים", use_container_width=True):
        st.rerun()

# --- דף הבית: DASHBOARD & MONITORING ---
if page == "דף הבית (Dashboard)":
    st.title("📊 מערכת ניטור ובקרה")
    
    # שליפת נתוני בריאות מה-API
    health_data = call_api("GET", "health")
    
    if health_data:
        # הצגת כרטיסי מדדים (Metrics)
        col1, col2, col3 = st.columns(3)
        
        # בדיקת סטטוס מונגו
        mongo_status = health_data.get("mongodb", {}).get("status", "error")
        col1.metric("MongoDB Status", "🟢 תקין" if mongo_status == "healthy" else "🔴 שגיאה")
        
        # בדיקת סטטוס קוואדרנט
        qdrant_status = health_data.get("qdrant", {}).get("status", "error")
        col2.metric("Qdrant Status", "🟢 תקין" if qdrant_status == "healthy" else "🔴 שגיאה")
        
        # השהיית מערכת
        latency = health_data.get("mongodb", {}).get("latency", "N/A")
        col3.metric("System Latency", latency)
        
        st.divider()
        st.subheader("🖥️ פרטי שרתים")
        st.json(health_data) # מציג את כל הפירוט הטכני בצורה נקייה
    else:
        st.error("לא ניתן להתחבר לשרת ה-API. וודא שקונטיינר kirp-api רץ.")
# --- דף שאילתת ידע ---
elif page == "שאילתת ידע (Query)":
    st.title("🔍 שאילתת ידע חכמה (RAG)")
    st.write("שאל את המערכת כל דבר המבוסס על מאגר הנתונים שלך.")
    
    with st.container(border=True):
        query_input = st.text_input("הקלד את שאלתך כאן:", placeholder="למשל: מה היו הבעיות המרכזיות בלוגים אתמול?")
        col1, col2 = st.columns([1, 5])
        if col1.button("שלח שאילתה", use_container_width=True):
            if query_input:
                with st.spinner("הסוכן סורק את מאגרי הידע..."):
                    result = call_api("POST", "query", {"query": query_input, "user_id": st.session_state.user_id})
                    if result and "answer" in result:
                        st.chat_message("assistant").write(result["answer"])
                    else:
                        st.error("הסוכן לא הצליח לגבש תשובה.")
            else:
                st.warning("נא להזין שאלה.")

# --- דף תובנות עסקיות ---
elif page == "תובנות עסקיות (Insights)":
    st.title("💡 תובנות מנוע הבינה")
    st.write("תובנות אלו נוצרות אוטומטית על ידי סריקה תקופתית של המערכת.")
    
    insights = call_api("GET", f"insights/{st.session_state.user_id}")
    
    if insights:
        for ins in insights:
            with st.expander(f"📌 {ins.get('title', 'תובנה חדשה')}"):
                c1, c2 = st.columns([3, 1])
                c1.write(ins.get("description", "אין תיאור זמין"))
                
                # תצוגת Confidence/Impact
                confidence = ins.get("confidence", 0)
                c2.metric("Confidence", f"{int(confidence*100)}%")
                
                st.caption(f"סוג: {ins.get('type')} | השפעה צפויה: {ins.get('impact_score', 'N/A')}/10")
    else:
        st.info("עדיין לא נוצרו תובנות. המתן לסריקה הבאה של המנוע.")
# --- דף ניהול סוכנים ---
elif page == "ניהול סוכנים (Agents)":
    st.title("🤖 Agent Architect")
    st.write("הגדר סוכן חדש למשימה ספציפית בתוך המערכת.")
    
    with st.form("new_agent_form"):
        st.subheader("יצירת סוכן משימה")
        agent_name = st.text_input("שם הסוכן", placeholder="למשל: LogAnalyzer_Agent")
        agent_goal = st.text_area("הגדרת מטרה", placeholder="למשל: סרוק לוגים של MongoDB והתראה על איטיות מעל 100ms")
        
        # כפתור שליחה - תיקון השגיאה הקודמת מ-form_submit_state ל-form_submit_button
        submit_agent = st.form_submit_button("הפעל ארכיטקט סוכנים", use_container_width=True)
        
        if submit_agent:
            if agent_name and agent_goal:
                with st.spinner("בונה תצורת סוכן..."):
                    res = call_api("POST", "agents/generate", {"name": agent_name, "goal": agent_goal})
                    if res:
                        st.success(f"הסוכן {agent_name} נוצר בהצלחה ונכנס לתהליך פריסה.")
                        st.json(res)
            else:
                st.error("נא למלא את כל השדות.")

# עיצוב תחתון (Footer)
st.sidebar.markdown("---")
st.sidebar.caption("KIRP OS v1.0.0 | Enterprise Knowledge Engine")
