import streamlit as st
import hmac

def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


def check_email():
    allowed_domain = "@" + st.secrets["companyDomain"]

    # Check if email is already stored in session state
    if "user_email" not in st.session_state:
        user_email = st.text_input("Enter your company email:", key="email_input")
        user_email = user_email.strip().lower()

        # Validate email when user enters something
        if user_email.endswith(allowed_domain):
            st.session_state["user_email"] = user_email  # Store valid email
            st.session_state["password_correct"] = True
            st.success(f"✅ Email validated: {user_email}")
            st.rerun()

        else:
            st.error(f"🚨 Please enter a valid company email 🚨")
            print("Stopping the script until email is validated.")
            st.stop()
        return False
    return True
