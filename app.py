import streamlit as st
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from langchain.prompts import PromptTemplate

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
uploaded_files = []
for file in os.listdir("./LEGAL-DATA"):
    file_path = os.path.join("./LEGAL-DATA", file)
    if os.path.isfile(file_path):
        uploaded_file = genai.upload_file(path=file_path)
        uploaded_files.append(uploaded_file)
uploaded_files_output = uploaded_files

# --- Streamlit UI setup ---
st.set_page_config(page_title="57582R2F2 vs 646039YM3 OS Analyzer", layout="wide")
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
st.markdown("<h3>⚖️ 57582R2F2 vs 646039YM3 OS Analyzer (Please wait for the robot to analyze the 2 big OS files)</h3>", unsafe_allow_html=True)

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
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Predefined Prompts ---
cusip_prompt = """Analyze all provided PDF documents. both related to 57582R2F2 and to 646039YM3. don't miss any of the CUSIP.
Extract the CUSIP list with details from each bond's document.
Present the information clearly, preferably in a table."""
compare_prompt = """Analyze all provided PDF documents, compare the key differences between them.
Present the information clearly, preferably in a table."""

col1, col2 = st.columns(2)
with col1:
    if st.button("📄 Extract CUSIP List"):
        st.session_state.pending_prompt = cusip_prompt
with col2:
    if st.button("🧾 Compare Document Differences"):
        st.session_state.pending_prompt = compare_prompt

# --- Use pending prompt if available ---
if st.session_state.pending_prompt:
    user_input = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
else:
    user_input = st.chat_input("Ask a question related to the 2 Cusips's OS...")

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
