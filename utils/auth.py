"""
AI Quiz Platform - Authentication
Version: 1.0.0
"""

import streamlit as st
from config.settings import settings
from utils.validators import validate_admin_credentials

def check_admin_authentication():
    """Check if admin is authenticated, show login if not"""
    
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔐 Admin Login")
        st.markdown("---")
        
        with st.form("admin_login"):
            col1, col2, col3, col4 = st.columns([1.7, 1.7, 1.4, 7.2])
            with col1:
                username = st.text_input("Username")
            with col2:
                password = st.text_input("Password", type="password")
            with col3:
                st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
                submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if validate_admin_credentials(
                    username, 
                    password, 
                    settings.ADMIN_USERNAME, 
                    settings.ADMIN_PASSWORD
                ):
                    st.session_state.admin_authenticated = True
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
        
        st.info("💡 Default credentials: admin / admin123")
        return False
    
    return True

def logout_admin():
    """Logout admin"""
    st.session_state.admin_authenticated = False
    st.success("Logged out successfully")
    st.rerun()
