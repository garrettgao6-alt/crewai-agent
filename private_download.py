"""Authorized server download links; no original bytes or account session tokens in public media URLs."""
import html,os
import streamlit as st
import download_service

def render(label,owner,project,kind,identifier):
    session=st.session_state.get('auth_session_token')
    if not session:
        st.warning('Sign in again to prepare a private download.');return
    key=(int(owner),int(project),kind,identifier)
    tickets=st.session_state.setdefault('private_download_tickets',{})
    token=tickets.get(key)
    try:
        if not token or not download_service.reusable(session,token,project,kind,identifier):
            token=download_service.issue(session,project,kind,identifier);tickets[key]=token
        base=os.getenv('PRIVATE_DOWNLOAD_BASE_URL','').rstrip('/')
        href=base+'/private-download/'+token
        st.markdown('<a target="_self" rel="noreferrer" href="'+html.escape(href,quote=True)+'" style="display:inline-block;padding:10px 15px;border:1px solid #516888;border-radius:8px;color:#93c5fd;text-decoration:none">'+html.escape(label)+'</a>',unsafe_allow_html=True)
    except (ValueError,PermissionError) as exc:st.warning(str(exc))
    st.caption('Private download links expire after five minutes and can be used once. Refresh this page for a new link.')
