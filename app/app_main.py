import sys
import os
if os.environ.get("STREAMLIT_ENV") == "cloud":
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
import os
import streamlit as st
from langchain_chroma import Chroma
from retrieval.pipeline import Pipeline
from study_setup import initialize_study, run_study_interface
from app_utils import setup_page_config

os.environ["STREAMLIT_WATCHER_EXCLUDE"] = "torch"
os.environ["STREAMLIT_WATCHER"] = "false"


device = "cuda"
@st.cache_resource
def load_pipeline(chroma_path, keyword_index_path):
    return Pipeline(chroma_path, keyword_index_path)

@st.cache_resource
def load_vectorstore(chroma_path):
    return Chroma(persist_directory=chroma_path)

def main():
    """Main application entry point"""
    setup_page_config()
    chroma_path = os.path.join(BASE_DIR, "data", "data_embedded")
    keyword_index_path = os.path.join(BASE_DIR, "data", "data_indexed")
    pipeline = load_pipeline(chroma_path, keyword_index_path)
    vectorstore = load_vectorstore(chroma_path)
    
    initialize_study()
    
    run_study_interface(pipeline, vectorstore)

if __name__ == "__main__":
    main()