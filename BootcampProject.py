import streamlit as st
import pandas as pd
import requests
import json
import re
from io import StringIO
from datetime import datetime

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Renewal Insight Agent", page_icon="🔁", layout="wide")

# ---- SESSION STATE ----
if 'history' not in st.session_state:
    st.session_state.history = []
if 'selected_history' not in st.session_state:
    st.session_state.selected_history = None
if 'question_bar' not in st.session_state:
    st.session_state.question_bar = ""
if 'input_cleared' not in st.session_state:
    st.session_state.input_cleared = False

# ---- LAYOUT: center main and right sidebar for quick questions ----
main_col, right_col = st.columns([5, 1])

# ---- CSS STYLE ----
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');
html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif !important;
}
.card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
    box-shadow: 0 1px 6px rgb(32 33 36 / 12%);
}
.stButton>button, .quick-btn {
    background-color: #0078D4 !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 6px 14px !important;
    width: 100%;
    margin-bottom: 12px;
    cursor: pointer;
    border: none;
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
}
.stButton>button:hover, .quick-btn:hover {
    background-color: #005bb5 !important;
}
table.dataframe tbody tr:nth-child(odd) {
    background-color: #f8f9fa;
}
.stExpander {
  margin-top: 0px !important;
}
</style>
""", unsafe_allow_html=True)

# ---- RIGHT: Quick Questions ----
with right_col:
    st.subheader("Sample Questions")
    sample_questions = [
        "Show high risk accounts for this quarter",
        "Analyze the highest ACV account for this quarter",
        "What is the Close Lost amount for this quarter",
        "Which accounts are Up For Renewal in the next quarter",
        "Which accounts have close dates overdue or past due but are still open?"
    ]
    for idx, question in enumerate(sample_questions):
        if st.button(question, key=f"quickq_{idx}"):
            st.session_state.question_bar = question

# ---- CENTER: Main chat area ----
with main_col:
    st.title("🔁 Renewal Insight Agent")
    st.markdown(
        """<b>Analyzes Customer Success renewal data including close dates, ACV, stages, 
        and risk indicators to forecast renewal likelihood, flag risks, and recommend proactive CSM actions.</b>""",
        unsafe_allow_html=True,
    )

    def style_table(df):
        def highlight_urgent(row):
            try:
                if 'Close Date' in df.columns:
                    cd = pd.to_datetime(row['Close Date'], errors='coerce')
                    if pd.notnull(cd):
                        days_left = (cd - datetime.now()).days
                        if days_left <= 30:
                            return ['background-color: #fff3cd;']*len(row)
            except:
                pass
            return ['']*len(row)

        if 'Status' in df.columns:
            icons = df['Status'].map({
                "Closed Won": "✅",
                "Closed Lost": "❌",
                "At Risk": "⚠️"
            }).fillna("")
            if "Status (icon)" not in df.columns:
                df.insert(0, "Status (icon)", icons)
        return df.style.apply(highlight_urgent, axis=1)

    # Show all Q&As with answers and tables, with collapsible cards
    for idx, chat in enumerate(st.session_state.history):
        expanded = (st.session_state.selected_history == idx)
        with st.expander(f"Q{idx+1}: {chat['q'][:60]}{'...' if len(chat['q']) > 60 else ''}", expanded=expanded):
            st.markdown(f"**Question:** {chat['q']}")
            if chat.get('loading', False):
                st.info("Answer is loading...")
            else:
                st.markdown("**Answer:**")
                st.markdown(chat['a'], unsafe_allow_html=True)
            tables = chat.get('answer_tables', [])
            if tables:
                for i, df in enumerate(tables):
                    st.markdown(f"**Table {i+1}**")
                    st.dataframe(style_table(df), use_container_width=True)

    st.markdown("---")
    st.markdown("### Ask a Question")

    # Use form for reliable submit and automatic clearing
    with st.form("question_form", clear_on_submit=True):
        default_val = st.session_state.pop('question_bar', '') if 'question_bar' in st.session_state else ''
        user_question = st.text_input("Type your question here...", value=default_val, key="input_bar")
        submitted = st.form_submit_button("Submit")

    if submitted and user_question.strip():
        st.session_state.history.append({
            "q": user_question.strip(),
            "a": "",
            "answer_tables": [],
            "loading": True
        })
        st.session_state.selected_history = len(st.session_state.history) - 1

        url = "https://emea.snaplogic.com/api/1/rest/slsched/feed/ConnectFasterInc/snapLogic4snapLogic/Bootcamp_EMEA_August_2025/AgentDriver_CSMProject_Task_Akriti"
        payload = [{"Question": user_question.strip()}]
        headers = {
            "Authorization": "Bearer JL92Zk10vbmChaJW6dwdii5FQJ2JAmEB",
            "Content-Type": "application/json"
        }

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

        # Parse tables from markdown
        tables = []
        matches = re.findall(r"((?:\|.*\n)+)", answer)
        for match in matches:
            lines = match.strip().split('\n')
            if len(lines) > 1 and re.match(r"^\|?[\s\-:|]+$", lines[1]):
                try:
                    df = pd.read_csv(StringIO(match), sep="|", engine="python", skipinitialspace=True, skiprows=[1])
                    df.columns = [c.strip() for c in df.columns]
                    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                    tables.append(df)
                except:
                    continue

        st.session_state.history[-1].update({
            "a": answer,
            "answer_tables": tables,
            "loading": False
        })

        st.rerun()
