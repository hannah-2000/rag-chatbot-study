import streamlit as st
import json
import requests
import base64
from datetime import datetime


def setup_page_config():
    """Configure the Streamlit page"""
    st.set_page_config(page_title="Study: Chatbot Evaluation", layout="wide")

def log_entry(entry: dict):
    """Add a timestamped log entry to the session state logs"""
    timestamp = datetime.now().isoformat()
    entry["timestamp"] = timestamp
    entry["study_id"] = st.session_state.study_id
    st.session_state.logs.append(entry)


def export_logs_github():
    """Export logs to GitHub"""
    print("SAVED TO GITHUB")
    logs = st.session_state.get("logs", [])
    if not logs:
        return
    log_str = json.dumps(logs, indent=2)
    upload_to_github(log_str)

def save_participation_code(code: str):
    """Append only the anonymous participation code to a shared GitHub file"""
    log_line = f"{code}\n"
    filename = "all_participation_codes.txt"

    # Upload line to GitHub (should support appending)
    upload_to_github(log_line, filename=filename, time=False, append=True)

def upload_to_github(log_data: str, filename="log", time=True, append=False):
    """Upload data to GitHub repository"""
    print("in upload to github in log utils")
    token = st.secrets["github"]["token"]
    repo = st.secrets["github"]["repo"]
    path = st.secrets["github"].get("path", "")
    if time:
        filename = f"{path}{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    else:
        filename = f"{path}{filename}"

    url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    sha = None
    if append:
        get_response = requests.get(url, headers=headers)
        if get_response.status_code == 200:
            file_info = get_response.json()
            sha = file_info["sha"]
            current_content = base64.b64decode(file_info["content"]).decode("utf-8")
            log_data = current_content + log_data
        elif get_response.status_code != 404:
            print("Failed to fetch existing file:", get_response.json())
            st.error("Failed to fetch existing log file from GitHub.")
            return

    content = base64.b64encode(log_data.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Add log {filename}",
        "content": content
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(url, json=payload, headers=headers)
    if response.status_code in [200, 201]:
        print(" Log uploaded successfully.")
    else:
        print("Upload failed:", response.json())
        st.error("Failed to upload log to GitHub.")