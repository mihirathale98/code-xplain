import streamlit as st
import requests
import uuid
from typing import List, Dict
import json
import time

# API configuration
API_URL = "http://localhost:8000"

def initialize_session_state():
    """Initialize session state variables"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "repo_url" not in st.session_state:
        st.session_state.repo_url = ""
    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False
    if "repo_loaded" not in st.session_state:
        st.session_state.repo_loaded = False

def reset_chat():
    """Reset the chat session"""
    response = requests.delete(f"{API_URL}/chat/{st.session_state.session_id}")
    if response.status_code == 200:
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.success("Chat session reset successfully!")

def send_message(message: str):
    """Send a message to the API and get response"""
    if not message:
        return
    
    st.session_state.is_loading = True
    
    try:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": message})
        
        # Send message to API
        response = requests.post(
            f"{API_URL}/chat/{st.session_state.session_id}",
            json={"role": "user", "content": message}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Add assistant's response to messages
            st.session_state.messages.append({"role": "assistant", "content": data["response"]})
        else:
            st.error(f"Error: {response.text}")
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        st.session_state.is_loading = False

def load_repo(repo_url: str):
    """Load a repository for analysis"""
    if not repo_url:
        st.error("Please enter a repository URL")
        return
    
    st.session_state.is_loading = True
    
    try:
        with st.spinner("Loading repository..."):
            response = requests.post(
                f"{API_URL}/load-repo",
                json={"repo_url": repo_url}
            )
            if response.status_code == 200:
                st.success(f"Repository loaded successfully: {repo_url}")
                st.session_state.repo_url = repo_url
                st.session_state.repo_loaded = True
                # Reset chat after loading new repository
                reset_chat()
            else:
                st.error(f"Error loading repository: {response.text}")
                st.session_state.repo_loaded = False
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.session_state.repo_loaded = False
    finally:
        st.session_state.is_loading = False

def check_repo_status():
    """Check if a repository is currently loaded"""
    try:
        response = requests.get(f"{API_URL}/repo-status")
        if response.status_code == 200:
            data = response.json()
            if data["loaded"]:
                st.session_state.repo_url = data["repo_url"]
                st.session_state.repo_loaded = True
            else:
                st.session_state.repo_loaded = False
            return data["loaded"]
    except Exception:
        st.session_state.repo_loaded = False
    return False

def main():
    st.set_page_config(
        page_title="Code Analysis Chat",
        page_icon="💻",
        layout="wide"
    )
    
    initialize_session_state()
    
    # Check repository status
    check_repo_status()
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Repository URL input section
        st.subheader("📁 Repository")
        repo_url_input = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo.git",
            help="Enter a GitHub repository URL to analyze"
        )
        
        # Load repository button
        col1, col2 = st.columns([2, 1])
        with col1:
            load_button = st.button(
                "🚀 Load Repository",
                disabled=st.session_state.is_loading or not repo_url_input.strip(),
                help="Click to load the repository for analysis"
            )
        with col2:
            if st.button("🔄", help="Refresh status"):
                check_repo_status()
                st.rerun()
        
        # Handle repository loading
        if load_button and repo_url_input.strip():
            load_repo(repo_url_input.strip())
        
        st.divider()
        
        # Chat controls section
        st.subheader("💬 Chat Controls")
        
        # Reset chat button
        if st.button("🗑️ Reset Chat", help="Clear chat history and start fresh"):
            reset_chat()
            st.rerun()
        
        st.divider()
        
        # Status section
        st.subheader("📊 Status")
        
        # Display repository status
        if st.session_state.repo_loaded:
            st.success("✅ Repository Loaded")
            st.info(f"**Current Repository:**\n{st.session_state.repo_url}")
        else:
            st.warning("⚠️ No Repository Loaded")
            st.info("Load a repository to start analyzing code")
        
        # Session info
        with st.expander("🔍 Session Info"):
            st.text(f"Session ID: {st.session_state.session_id}")
            st.text(f"Messages: {len(st.session_state.messages)}")
            st.text(f"Loading: {st.session_state.is_loading}")
    
    # Main chat interface
    st.title("💻 Code Analysis Chat")
    
    # Welcome message when no repository is loaded
    if not st.session_state.repo_loaded:
        st.info("""
        👋 **Welcome to Code-Xplain!**
        
        To get started:
        1. Enter a GitHub repository URL in the sidebar
        2. Click "🚀 Load Repository" 
        3. Start asking questions about the codebase!
        
        **Example repositories to try:**
        - `https://github.com/fastapi/fastapi.git`
        - `https://github.com/streamlit/streamlit.git`
        - `https://github.com/microsoft/vscode.git`
        """)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input(
        "Ask about the codebase..." if st.session_state.repo_loaded else "Load a repository first to start chatting...",
        disabled=st.session_state.is_loading or not st.session_state.repo_loaded
    ):
        send_message(prompt)
        st.rerun()  # Rerun to update the display
    
    # Loading indicator
    if st.session_state.is_loading:
        with st.spinner("Processing..."):
            time.sleep(0.1)  # Small delay to show spinner

if __name__ == "__main__":
    main() 