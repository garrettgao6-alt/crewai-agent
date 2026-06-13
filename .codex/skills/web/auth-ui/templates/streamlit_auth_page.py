import streamlit as st


def render_auth_page(authenticate_user, create_user, set_authenticated_user) -> None:
    st.markdown(
        """
        <div class="hub-hero">
            <h1>Gao Intelligence Hub</h1>
            <h2 class="hero-subtitle">Business, Construction &amp; Executive AI Intelligence Platform</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sign_in_tab, create_account_tab = st.tabs(["Sign In", "Create Account"])
    with sign_in_tab:
        with st.form("sign_in_form"):
            identifier = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
        if submitted:
            user = authenticate_user(identifier, password)
            if user is None:
                st.error("Invalid username/email or password.")
            else:
                set_authenticated_user(user)
                st.rerun()

    with create_account_tab:
        with st.form("create_account_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
            user = create_user(username, email, password)
            set_authenticated_user(user)
            st.rerun()
