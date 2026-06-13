# Streamlit Auth Patterns

## Auth State

```python
def set_authenticated_user(user):
    st.session_state.authenticated = True
    st.session_state.user_id = user["id"]
    st.session_state.username = user["username"]
    st.session_state.role = user["role"]
```

## Sign Out

Clear app-level selection state as well as user state:

```python
st.session_state.authenticated = False
st.session_state.current_user = None
st.session_state.active_project_id = None
st.session_state.selected_history = None
```

## Form Errors

Use specific validation messages for password mismatch, short passwords, duplicate accounts, and account limit reached.
