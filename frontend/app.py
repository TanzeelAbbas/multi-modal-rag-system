import os
import sys
import streamlit as st
import requests
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

load_dotenv()

FASTAPI_BACKEND_URL = os.getenv("FASTAPI_BACKEND_URL", "http://api:8080")

def main():
    st.set_page_config(
        page_title="RAG System", 
        page_icon="📄", 
        layout="wide"
    )

    st.sidebar.header("🔑 Gemini API Configuration")
    api_key = st.sidebar.text_input(
        "Paste Gemini API Key", 
        type="password",
        help="Get your API key from https://makersuite.google.com/app/apikey"
    )

    if api_key:
        if 'api_key' not in st.session_state or st.session_state.api_key != api_key:
            st.session_state.api_key = api_key
            try:
                response = requests.post(
                    f"{FASTAPI_BACKEND_URL}/ask",
                    json={"query": "Hello, can you confirm the API is working?"},
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if response.status_code == 200:
                    st.sidebar.success("API Key Validated Successfully!")
                else:
                    st.sidebar.error("Invalid API Key. Please check and retry.")
            except Exception as e:
                st.sidebar.error(f"API Key Validation Error: {e}")
    else:
        st.sidebar.warning("Please enter your Gemini API Key to proceed.")

    st.sidebar.header("📤 Document Upload")
    uploaded_files = st.sidebar.file_uploader(
        "Upload Document", 
        type=['pdf', 'txt', 'png', 'jpg', 'jpeg'],
        help="Supported formats: PDF, TXT, PNG, JPG, JPEG",
        accept_multiple_files=True  
    )

    st.title("🤖 RAG System")

    if uploaded_files and 'api_key' in st.session_state:
        for uploaded_file in uploaded_files:
            try:
                files = {"files": (uploaded_file.name, uploaded_file.getvalue())}
                response = requests.post(
                    f"{FASTAPI_BACKEND_URL}/upload/batch",
                    files=files,
                    headers={"Authorization": f"Bearer {st.session_state.api_key}"}
                )
                if response.status_code == 200:
                    st.sidebar.success(f"Processed {uploaded_file.name}")
                else:
                    st.error(f"Document Processing Error for {uploaded_file.name}: {response.text}")
            except Exception as e:
                st.error(f"Document Processing Error for {uploaded_file.name}: {e}")

    st.header("💬 Ask a Question")
    query = st.text_input("Enter your question about the document:")

    if query and 'api_key' in st.session_state:
        try:
            response = requests.post(
                f"{FASTAPI_BACKEND_URL}/ask",
                json={"query": query},
                headers={"Authorization": f"Bearer {st.session_state.api_key}"}
            )
            if response.status_code == 200:
                result = response.json()
                st.subheader("🤖 Answer")
                st.write(result.get("answer", "No answer found."))
                
                with st.expander("📍 Context Sources"):
                    for i, ctx in enumerate(result.get("sources", []), 1):
                        st.text(f"Source {i}: {ctx.get('text', '')[:300]}...")
            else:
                st.error(f"Question Answering Error: {response.text}")
        except Exception as e:
            st.error(f"Question Answering Error: {e}")
    elif query:
        st.warning("Please enter a valid API key to enable question answering.")

if __name__ == "__main__":
    main()