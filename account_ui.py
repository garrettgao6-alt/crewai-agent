"""Account forms; credentials remain password inputs and are never displayed."""
import streamlit as st
import account_recovery
import user_store


def render_recovery():
    st.caption('Receive an email verification code, then set a new password. Codes expire after 10 minutes.')
    with st.form('request_password_code'):
        email = st.text_input('Account email', key='recovery_send_email')
        send = st.form_submit_button('Send verification code')
    if send:
        try:
            st.success(account_recovery.request_code(email))
        except (ValueError, user_store.UserStoreError) as exc:
            st.error(str(exc))
    with st.form('reset_password_with_code', clear_on_submit=True):
        email = st.text_input('Account email', key='recovery_reset_email')
        code = st.text_input('8-digit verification code', max_chars=8)
        password = st.text_input('New password', type='password', max_chars=256)
        confirm = st.text_input('Confirm new password', type='password', max_chars=256)
        reset = st.form_submit_button('Reset password')
    if reset:
        if password != confirm:
            st.error('Passwords do not match.')
        else:
            try:
                account_recovery.reset_password(email, code, password)
                st.success('Password updated. All previous sessions have been signed out. Sign in with your new password.')
            except (ValueError, user_store.UserStoreError) as exc:
                st.error(str(exc))


def render_username_settings(user):
    if not user or not user.get('id'):
        return None
    st.subheader('Change username')
    st.caption('Your projects, documents and reports remain attached to your account.')
    with st.form('change_username', clear_on_submit=True):
        username = st.text_input('New username', max_chars=40)
        password = st.text_input('Current password', type='password', max_chars=256)
        submit = st.form_submit_button('Save username')
    if submit:
        try:
            updated = account_recovery.change_username(user['id'], password, username)
            st.success('Username updated.')
            return updated
        except (ValueError, user_store.UserStoreError) as exc:
            st.error(str(exc))
    return None
