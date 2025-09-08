import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Renewal Insight Agent", page_icon="🔁", layout="wide")

# ---- SESSION STATE ----
if 'history' not in st.session_state:
    st.session_state.history = []
if 'loading_state' not in st.session_state:
    st.session_state.loading_state = False
if 'current_question' not in st.session_state:
    st.session_state.current_question = ""

main_col, right_col = st.columns([5, 1])

# ---- CSS ----
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');
html, body, [class*="css"]  { font-family: 'Inter', sans-serif !important; }
.stButton>button {
    background-color: #0078D4 !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 6px 14px !important;
    width: 100%;
    margin-bottom: 8px;
    font-size: 1rem !important;
}
.stButton>button:hover {
    background-color: #005bb5 !important;
}
.stExpander { margin-top: 0 !important; }
[data-testid="stElementToolbar"] { display: none !important; }
.loading-spinner {
  position: fixed;
  top: 42%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  font-size:2rem;
  background: rgba(255,255,255,0.98);
  padding:40px 60px 30px 60px;
  border-radius: 18px;
  color: #0078D4;
  z-index: 9999;
  box-shadow: 0 5px 30px rgba(0,0,0,0.12);
}
</style>
""", unsafe_allow_html=True)

# ---- RIGHT: Sample Questions ----
with right_col:
    with st.expander("Sample Questions", expanded=True):
        sample_questions = [
            "Show high risk accounts for this quarter",
            "Analyze the highest ACV account for this quarter",
            "What is the Close Lost amount for this quarter",
            "Which accounts are Up For Renewal in the next quarter",
            "Which accounts have close dates overdue or past due but are still open?"
        ]
        for idx, question in enumerate(sample_questions):
            if st.button(question, key=f"quickq_{idx}"):
                if not st.session_state.loading_state:
                    st.session_state.current_question = question
                    st.session_state.loading_state = True
                    st.rerun()

# ---- CENTER: Main chat, input form, answers ----
with main_col:
    st.title("🔁 Renewal Insight Agent")
    st.markdown(
        "<b>Analyzes Customer Success renewal data including close dates, ACV, stages, and risk indicators to forecast renewal likelihood, flag risks, and recommend proactive CSM actions.</b>",
        unsafe_allow_html=True,
    )

    # Q&A CARD LIST - only markdown, never dataframe, so table isn't repeated
    for idx, chat in enumerate(st.session_state.history):
        with st.expander(f"Q{idx+1}: {chat['q'][:60]}{'...' if len(chat['q']) > 60 else ''}"):
            st.markdown(f"**Question:** {chat['q']}")
            st.markdown("**Answer:**")
            # Only show the raw markdown with tables
            st.markdown(chat['a'], unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Ask a Question")

    # ---- INPUT FORM ----
    if not st.session_state.loading_state:
        with st.form("question_form", clear_on_submit=True):
            qbox_default = st.session_state.current_question
            user_question = st.text_input("Type your question here...", value=qbox_default, key="input_bar")
            submitted = st.form_submit_button("Submit")
        if submitted and user_question.strip():
            st.session_state.current_question = user_question.strip()
            st.session_state.loading_state = True
            st.rerun()
    else:
        st.text_input("Type your question here...", value=st.session_state.current_question, disabled=True, key="input_bar_loading")

    # ---- LOADING SPINNER (centered) ----
    if st.session_state.loading_state:
        st.markdown(
            """<div class="loading-spinner">
            <div style='font-size:2.2rem; margin-bottom:15px;'>⏳</div>
            <div><b>Answer is loading, please wait...</b></div>
            <div style='font-size:1rem; margin-top:7px;color:gray;'>This could take a few seconds.</div>
            </div>""",
            unsafe_allow_html=True,
        )

        question_text = st.session_state.current_question
        url = "https://elastic.snaplogic.com/api/1/rest/slsched/feed/ConnectFasterInc/Akriti%20Singhal/Renewal%20Insight%20Agent/AgentDriver%20-%20Project%20Akriti%20Task"
        payload = [{"Question": question_text}]
        headers = {
            "Authorization": "Bearer tp5smZiJNKa0u5oqvKiz8Y0rO1x6PFhW",
            "Content-Type": "application/json"
        }

        # Only execute once per rerun for a given q
        if len(st.session_state.history) == 0 or st.session_state.history[-1]['q'] != question_text:
            try:
                resp = requests.post(url, headers=headers, data=json.dumps(payload))
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and data and "response" in data[0]:
                        answer = data[0]["response"]
                    elif isinstance(data, dict) and "response" in data:
                        answer = data["response"]
                    else:
                        answer = f"⚠️ Unexpected API response: {data}"
                else:
                    answer = f"⚠️ API error {resp.status_code}: {resp.text}"
            except Exception as e:
                answer = f"❌ API call failed: {str(e)}"

            st.session_state.history.append({
                "q": question_text,
                "a": answer
            })
            st.session_state.current_question = ""
            st.session_state.loading_state = False
            st.rerun()



