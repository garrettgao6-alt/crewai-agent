"""Authenticated private NCC import and per-project matching context."""
import streamlit as st
from ui_labels import friendly_error
from core import ncc_library, ncc_catalog


def render_private_library_controls(user_id, project):
    st.subheader('Import NCC PDFs into your private library')
    st.caption('Files stay in your account library. Indexing uses local text search, without AI processing. Guest AI cannot access this library. Up to 75 MB per PDF and 200 MB per import.')
    if st.session_state.get('ncc_import_message'):
        st.success(st.session_state.pop('ncc_import_message'))
    uploads = st.file_uploader('NCC library PDFs', type=['pdf'], accept_multiple_files=True, key=f"private_ncc_upload_{st.session_state.get('ncc_upload_version', 0)}")
    metadata = []
    for file in uploads or []:
        default_year = '2022' if '2022' in file.name else '2025'
        default_kind = 'Housing Provisions' if 'housing' in file.name.lower() else 'Volume Two' if 'two' in file.name.lower() else 'Volume One'
        year = st.selectbox(f'Edition: {file.name}', ['2025', '2022'], index=['2025', '2022'].index(default_year), key=f'ncc_year_{file.name}')
        kind = st.selectbox(f'Volume: {file.name}', list(ncc_catalog.KINDS), index=list(ncc_catalog.KINDS).index(default_kind), key=f'ncc_kind_{file.name}')
        metadata.append((file, year, kind))
    if st.button('Import and activate private NCC library', disabled=not uploads, key='import_private_ncc'):
        try:
            with st.spinner('Reading PDF pages and building the private search index. No AI tokens are used…'):
                result = ncc_catalog.import_pdfs(user_id, [(file.name, file.getvalue(), year, kind) for file, year, kind in metadata])
            st.session_state["ncc_import_message"] = f"Activated {result['files']} PDFs with {result['chunks']:,} searchable passages. Your previous collection was preserved."
            st.session_state["ncc_upload_version"] = st.session_state.get("ncc_upload_version", 0) + 1
            st.rerun()
        except (ValueError, OSError, ncc_library.NCCReferenceError) as exc:
            st.error(friendly_error(exc))
    st.subheader('Project context for automatic NCC matching')
    if not project:
        st.info('Select a project to save its building class, NCC edition and state/territory. These details can also be supplied in the analysis question.')
        return
    saved = ncc_library.load_project_context(user_id, project['id'])
    st.caption(f"Project: {project['name']}. Source selection uses the declared edition and building class. State adoption and approval-date applicability must be verified separately.")
    with st.form(f"ncc_context_{project['id']}"):
        editions = ['', '2025', '2022']
        classes = ['', '1a', '1b', '2', '3', '4', '5', '6', '7a', '7b', '8', '9a', '9b', '9c', '10a', '10b', '10c']
        jurisdictions = ['', 'VIC', 'NSW', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT']
        edition = st.selectbox('Project NCC edition', editions, index=editions.index(saved.get('edition', '')), format_func=lambda v: v or 'Not specified')
        cls = st.selectbox('Building class', classes, index=classes.index(saved.get('building_class', '')) if saved.get('building_class', '') in classes else 0, format_func=lambda v: f'Class {v}' if v else 'Not specified')
        state = st.selectbox('State or territory', jurisdictions, index=jurisdictions.index(saved.get('jurisdiction', '')), format_func=lambda v: {'VIC':'Victoria','NSW':'New South Wales','QLD':'Queensland','SA':'South Australia','WA':'Western Australia','TAS':'Tasmania','NT':'Northern Territory','ACT':'Australian Capital Territory'}.get(v,'Not specified'))
        if st.form_submit_button('Save project NCC context'):
            ncc_library.save_project_context(user_id, project['id'], edition, cls, state)
            st.success('Saved. Future NCC analyses will match this project context automatically.')
