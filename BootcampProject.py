import streamlit as st
import pandas as pd
import requests
import json
import re
from io import StringIO, BytesIO
import zipfile

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Renewal Insight Agent", page_icon="🔁", layout="wide")

# ---- SESSION STATE ----
if 'history' not in st.session_state:
    st.session_state.history = []  # list of dict {q,a,answer_tables,loading}
if 'selected_history' not in st.session_state:
    st.session_state.selected_history = None  # index of Q/A to expand
if 'question_bar' not in st.session_state:
    st.session_state.question_bar = ""
if 'input_cleared' not in st.session_state:
    st.session_state.input_cleared = False

# ---- LAYOUT: left sidebar for history, center main, right sidebar for quick questions ----
left, main, right = st.columns([1, 4, 1])

# ---- CSS STYLE WITH REMOVED EXTRA SPACE BELOW HISTORY AND STANDARDIZED FONT ----
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');
html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif !important;
}
.side-scroll {
    height: 85vh;
    overflow-y: auto;
    background-color: #f8f9fa;
    padding: 8px 8px 8px 8px; /* removed smaller bottom padding */
    border-radius: 8px;
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
.highlight-urgent {
    background-color: #fff3cd !important;
}
.stExpander {
  margin-top: 0px !important;
}
</style>
""", unsafe_allow_html=True)

# ---- LEFT: Conversation History ----
with left:
    st.header("🗂️ Conversation History")
    container = st.container()
    container.markdown('<div class="side-scroll">', unsafe_allow_html=True)

    if st.session_state.history:
        for idx, chat in enumerate(st.session_state.history):
            label = f"Q: {chat['q'][:30]}{'...' if len(chat['q'])>30 else ''}"
            if st.button(label, key=f'hist_{idx}'):
                st.session_state.selected_history = idx
    else:
        st.info("No conversation history yet.")
    container.markdown('</div>', unsafe_allow_html=True)

# ---- RIGHT: Quick Questions vertical stacked buttons ----
with right:
    st.subheader("Sample Questions")
    quickqs = [
        "Show high risk accounts for this quarter",
        "Analyze the highest ACV account for this quarter",
        "What is the Close Lost amount for this quarter",
        "Which accounts are Up For Renewal in the next quarter",
        "Which accounts have close dates overdue or past due but are still open?"
    ]
    for i, qq in enumerate(quickqs):
        if st.button(qq, key=f"quickq_{i}"):
            st.session_state.question_bar = qq
            st.session_state.input_cleared = False

# ---- CENTER: Main chat area ----
with main:
    st.title("🔁 Renewal Insight Agent")
    st.markdown(
        """<b>Analyzes Customer Success renewal data including close dates, ACV, stages, 
        and risk indicators to forecast renewal likelihood, flag risks, and recommend proactive CSM actions.</b>""",
        unsafe_allow_html=True,
    )

    def style_table(df):
        import datetime
        def highlight_urgent(row):
            try:
                if 'Close Date' in df.columns:
                    cd = pd.to_datetime(row['Close Date'], errors='coerce')
                    if pd.notnull(cd):
                        days = (cd - datetime.datetime.now()).days
                        if days <= 30:
                            return ['highlight-urgent'] * len(row)
            except:
                pass
            return [''] * len(row)

        if 'Status' in df.columns:
            icons = df['Status'].map({
                "Closed Won": "✅",
                "Closed Lost": "❌",
                "At Risk": "⚠️"
            }).fillna("")

            if "Status (icon)" not in df.columns:
                df.insert(0, "Status (icon)", icons)
        return df.style.apply(highlight_urgent, axis=1)

    # Show all Q&As as collapsible cards
    for idx, chat in enumerate(st.session_state.history):
        expanded = (st.session_state.selected_history == idx)
        with st.expander(f"Q{idx+1}: {chat['q'][:60]}{'...' if len(chat['q'])>60 else ''}", expanded=expanded):
            st.markdown(f"**Question:** {chat['q']}")
            if chat.get('loading', False):
                st.info("Answer is loading...")
            else:
                st.markdown("**Answer:**")
                st.markdown(chat['a'], unsafe_allow_html=True)
            tables = chat.get('answer_tables', [])
            if tables:
                # Show only tables once (no repeated same tables)
                for i, df in enumerate(tables):
                    # show each table once without extra download buttons for each
                    st.markdown(f"**Table {i+1}**")
                    st.dataframe(style_table(df), use_container_width=True)
                # Only provide download button once below first table in this answer
                first_table_csv = tables[0].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Export First Table as CSV",
                    data=first_table_csv,
                    file_name="answer_first_table.csv",
                    mime="text/csv",
                    key=f"dl_first_{idx}"
                )

    st.markdown("---")
    st.markdown("### Ask a Question")

    # Controlled input clearing to avoid sticky text field
    if not st.session_state.input_cleared:
        default_val = st.session_state.pop('question_bar', '') or ''
    else:
        default_val = ''

    user_question = st.text_input("Type your question and press Enter to submit", value=default_val, key="input_bar")

    if user_question and user_question.strip() and not st.session_state.input_cleared:
        st.session_state.history.append({
            "q": user_question.strip(),
            "a": "",
            "answer_tables": [],
            "loading": True
        })
        st.session_state.selected_history = len(st.session_state.history) - 1
        st.session_state.input_cleared = True

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

        # Parse tables from markdown response
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
