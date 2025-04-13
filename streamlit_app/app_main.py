import os
import torch
import streamlit as st
from langchain_chroma import Chroma
import sys
sys.path.append("../")
from retrieval.pipeline import Pipeline


# Environment setup
os.environ["STREAMLIT_WATCHER_EXCLUDE"] = "torch"
os.environ["STREAMLIT_WATCHER"] = "false"

# Import our modules
from study_setup import initialize_study, run_study_interface
from app_utils import setup_page_config, download_and_unzip_data

# Check for available device
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# Caching functions
@st.cache_resource
def load_pipeline(chroma_path, keyword_index_path):
    return Pipeline(chroma_path, keyword_index_path)

@st.cache_resource
def load_vectorstore(chroma_path):
    return Chroma(persist_directory=chroma_path)

def main():
    """Main application entry point"""
    # Setup page configuration
    setup_page_config()
    download_and_unzip_data()
    # Load resources
    chroma_path = "data/data_embedded"
    keyword_index_path = "data/data_indexed"
    pipeline = load_pipeline(chroma_path, keyword_index_path)
    vectorstore = load_vectorstore(chroma_path)
    
    # Initialize session state for the study
    initialize_study()
    
    # Run the study interface
    run_study_interface(pipeline, vectorstore)

if __name__ == "__main__":
    main()