import streamlit as st
st.set_page_config(page_title="Muni OS Analyzer", layout="wide")

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from langchain.prompts import PromptTemplate
import time
# --- Load environment variables ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    st.error(f"Failed to configure GenAI API: {e}")
    st.stop()

# --- Upload files (each run) ---
uploaded_files_output = []

CUSIPS = [
    "57582R2F2",
    "646039YM3",
    "93974EVY9",
    "8827236V6",
    "64966MXN4",
    "13063D7Q5",
]

CUSIP_DESCRIPTIONS = {
    "57582R2F2": "MASSACHUSETTS ST",
    "646039YM3": "NEW JERSEY ST",
    "93974EVY9": "WASHINGTON ST",
    "64966MXN4": "NEW YORK N Y",
    "8827236V6": "TEXAS ST",
    "13063D7Q5": "CALIFORNIA ST",
}

if "uploaded_file_ids" not in st.session_state:
    st.session_state.uploaded_file_ids = {}

MAX_SELECTED = 2

if "selected_order" not in st.session_state:
    st.session_state.selected_order = []


def handle_checkbox_change(cusip: str) -> None:
    """Maintain selection order and enforce a maximum of two selections."""
    if st.session_state[cusip]:
        if cusip not in st.session_state.selected_order:
            st.session_state.selected_order.append(cusip)
        if len(st.session_state.selected_order) > MAX_SELECTED:
            first = st.session_state.selected_order.pop(0)
            st.session_state[first] = False
    else:
        if cusip in st.session_state.selected_order:
            st.session_state.selected_order.remove(cusip)

st.sidebar.header("Select 1-2 CUSIPs")
for c in CUSIPS:
    st.sidebar.checkbox(
        f"{c} ({CUSIP_DESCRIPTIONS.get(c, '')})",
        key=c,
        on_change=handle_checkbox_change,
        args=(c,),
    )

selected_cusips = [c for c in CUSIPS if st.session_state.get(c)]

uploaded_files = []

for cusip in selected_cusips:
    file = f"{cusip}.pdf"
    file_path = os.path.join("./DATA", file)
    if os.path.isfile(file_path) and file not in st.session_state.uploaded_file_ids:
        for attempt in range(5):
            try:
                uploaded_file = genai.upload_file(path=file_path)
                st.session_state.uploaded_file_ids[file] = uploaded_file.name
                uploaded_files.append(uploaded_file)
                break  # Exit retry loop on success
            except Exception as e:
                st.warning(f"Attempt {attempt+1} to upload '{file}' failed: {e}")
                time.sleep(2)
        else:
            st.error(f"❌ Failed to upload '{file}' after 5 attempts.")
    elif file in st.session_state.uploaded_file_ids:
        try:
            uploaded_files.append(genai.get_file(name=st.session_state.uploaded_file_ids[file]))
        except Exception as e:
            st.warning(f"⚠️ Could not retrieve cached file '{file}': {e}")

uploaded_files_output = uploaded_files

# --- Streamlit UI setup ---

st.markdown("""<style>
    div.stButton > button:first-child {
        background-color: #ffd0d0;
    }
    div.stButton > button:active {
        background-color: #ff6262;
    }
    #MainMenu, footer, .stDeployButton, #stDecoration, button[title="View fullscreen"] {
        visibility: hidden;
    }
</style>""", unsafe_allow_html=True)
header_cusips = " vs ".join(selected_cusips) if selected_cusips else "Muni OS"
st.markdown(
    f"<h3>⚖️ {header_cusips} OS Analyzer (Please wait while the system analyzes the selected OS documents.)</h3>",
    unsafe_allow_html=True,
)

# --- Session state ---
def reset_conversation():
    st.session_state.messages = []
    st.session_state.pending_prompt = None

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# --- Prompt Template ---
prompt_template = """
<s>[INST]Analyze all provided PDF documents. You are a Municipal bonds documents analyzer chat bot. 
Your goal is to deliver professional, precise, and contextually relevant information pertaining to all of the uploaded files.
CHAT HISTORY: {chat_history}
QUESTION: {question}
ANSWER:
</s>[INST]
"""
prompt = PromptTemplate(template=prompt_template, input_variables=["question", "chat_history"])

# --- Model Setup ---
#model = genai.GenerativeModel("gemini-2.0-flash")
model = genai.GenerativeModel("gemini-2.5-pro-preview-05-06")

# --- Predefined Prompts ---
if selected_cusips:
    joined_cusips = " and ".join(selected_cusips) if len(selected_cusips) <= 2 else ", ".join(selected_cusips)
    cusip_prompt = f"""Analyze all uploaded PDF documents related to the following CUSIPs: {joined_cusips}.
Ensure no CUSIP is overlooked. Extract a comprehensive list of CUSIPs mentioned in each bond’s documents, including relevant details.
Present the extracted information clearly, preferably in a table format."""
    compare_prompt = f"""Analyze all provided PDF documents related to {joined_cusips} and compare the key differences between them.
Summarize the findings clearly, preferably in a table format."""
else:
    cusip_prompt = """Analyze all uploaded PDF documents. Ensure no CUSIP is overlooked. Extract a comprehensive list of CUSIPs mentioned, including relevant details. Present the extracted information clearly, preferably in a table format."""
    compare_prompt = """Analyze all provided PDF documents and compare the key differences between them. Summarize the findings clearly, preferably in a table format."""

col1, col2 = st.columns(2)
with col1:
    if st.button("📄 Extract CUSIP List"):
        st.session_state.pending_prompt = cusip_prompt
with col2:
    if st.button("🧾 Compare Document Differences"):
        st.session_state.pending_prompt = compare_prompt

chat_box_input = st.chat_input("Ask a question related to the selected CUSIPs' OS...")

if st.session_state.pending_prompt:
    user_input = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
elif chat_box_input:
    user_input = chat_box_input
else:
    user_input = None

# --- Display chat history ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Process input ---
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.status("Analyzing Muni OS documents..."):
            try:
                chat_history = "\n".join([
                    f"{msg['role'].capitalize()}: {msg['content']}"
                    for msg in st.session_state.messages if msg["role"] != "assistant"
                ])
                formatted_prompt = prompt.format(question=user_input, chat_history=chat_history)
                contents = [formatted_prompt] + uploaded_files_output
                response = model.generate_content(contents)
                reply = response.text
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Error generating response: {e}")

    st.button("🔁 Reset All Chat 🗑️", on_click=reset_conversation)
