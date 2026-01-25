import streamlit as st

def render_insight_card(title, content, icon="💡"):
    st.markdown(f"""
        <div style='background: rgba(56, 189, 248, 0.1); border-left: 4px solid #38bdf8; 
                    padding: 15px; border-radius: 10px; margin: 10px 0;'>
            <div style='display: flex; align-items: center; gap: 10px;'>
                <span>{icon}</span>
                <b style='color: #38bdf8;'>{title}</b>
            </div>
            <div style='margin-top: 5px; font-size: 0.95rem;'>{content}</div>
        </div>
    """, unsafe_allow_html=True)

def render_concept_tag(concept, strength):
    st.markdown(f"""
        <span style='background: #1e293b; border: 1px solid #38bdf8; color: #38bdf8;
                     padding: 4px 12px; border-radius: 999px; font-size: 0.8rem; margin-right: 5px;'>
            {concept} ({strength})
        </span>
    """, unsafe_allow_html=True)