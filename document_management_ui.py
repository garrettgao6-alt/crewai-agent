"""Persistent, project-owned file management; all mutations authorize again in the store."""
import streamlit as st
from datetime import datetime,timezone
from core import document_store as store
from private_download import render as private_download

def _action(owner,project,function,*args):
    try:function(owner,project,*args);notice=('success','File library updated.')
    except (ValueError,PermissionError) as exc:notice=('error',str(exc))
    except Exception:notice=('error','The file action could not complete. Existing data is preserved.')
    st.session_state[f'dm_notice_{owner}_{project}']=notice


def library(owner,project,only_bim=False):
    scope=f'{owner}_{project}'
    notice=st.session_state.pop(f'dm_notice_{owner}_{project}',None)
    if notice:getattr(st,notice[0])(notice[1])
    archived=st.checkbox('Show archived files',key=f'dm_archived_{scope}_{only_bim}')
    files=store.list_files(owner,project,archived)
    if only_bim:files=[f for f in files if f.get('kind')=='bim']
    if not files:
        st.info('No archived files. Archived originals remain recoverable here.' if archived else 'Your project library is empty. Upload a document above to retain the original and make its text searchable.')
        return
    search=st.text_input('Find a file',placeholder='Search filenames',key=f'dm_search_{scope}_{only_bim}')
    total=len(files)
    files=[item for item in files if search.casefold() in item['name'].casefold()]
    st.caption(f'{len(files)} of {total} files · Only this project is shown')
    if not files:
        st.info('No matching files. Clear the search to see your library.');return
    st.dataframe([{'File':f['name'],'Active version':f.get('version'),'Status':f.get('status'),'Type':f.get('kind'),'Size KB':round((f.get('size') or 0)/1024,1),'Search chunks':f.get('chunks') or 0} for f in files],hide_index=True,use_container_width=True)
    chosen=st.selectbox('Manage file',files,format_func=lambda f:f['name'],key=f'dm_file_{scope}_{archived}_{only_bim}')
    history=store.versions(owner,project,chosen['id'])
    selected=st.selectbox('Retained version',history,format_func=lambda v:f"v{v['version']} · {v['status']} · {datetime.fromtimestamp(v['created'],timezone.utc).strftime('%d %b %Y, %H:%M UTC')}",key=f"dm_version_{scope}_{chosen['id']}_{only_bim}")
    with st.expander('File details and integrity'):
        st.caption('Original SHA-256: '+selected['sha'])
        st.write({'Version':selected['version'],'Status':selected['status'],'Size KB':round(selected['size']/1024,1)})
    if selected['error']:st.warning(selected['error'])
    available=False
    try:
        available=store.path_for(selected).is_file()
        if not available:raise OSError()
        private_download('Download original',owner,project,'original',selected['id'])
    except (OSError,RuntimeError):st.error('The retained original is unavailable or failed its checksum. Contact an administrator before restoring it.')
    if available and selected['status']=='ready' and (archived or selected['id']!=chosen['active_version']):
        st.button('Restore this version',key=f"dm_restore_{scope}_{selected['id']}_{only_bim}",on_click=_action,args=(owner,project,store.activate_version,chosen['id'],selected['id']))
    if archived:
        st.button('Unarchive file',key=f"dm_unarchive_{scope}_{chosen['id']}_{only_bim}",on_click=_action,args=(owner,project,store.set_archived,chosen['id'],False))
    else:
        st.caption('Archiving removes this file from new searches. Retained originals, versions and existing reports remain recoverable.')
        st.button('Archive file',key=f"dm_archive_{scope}_{chosen['id']}_{only_bim}",on_click=_action,args=(owner,project,store.set_archived,chosen['id']))

def render(owner,project):
    st.caption('Originals and versions are private to this project. PDF/TXT/DOCX/XLSX are searchable. Use BIM Model Checks for IFC.')
    with st.expander('Supported formats and processing limits'):
        st.caption('Limits: 50 MB/file, 80 KB extracted text and 60 search chunks; 600 MB and 1,000 retained versions/account. Scans need OCR first. Office tables/cells are read; spreadsheet formulas are not recalculated. DOCX/XLSX section numbers are not PDF page numbers.')
    scope=f'{owner}_{project}'
    file=st.file_uploader('Upload a document',type=['pdf','txt','docx','xlsx'],key=f'dm_upload_{scope}')
    st.caption('PDF, TXT, DOCX or XLSX · Indexing limit: 50 MB per file, 80 KB of extracted text.')
    oversized=file is not None and file.size>50*1024**2
    if oversized:st.error('This document exceeds 50 MB. Split it before indexing.')
    kind=st.selectbox('Document type',['Auto-detect','Business','NCC','Housing'],key=f'dm_kind_{scope}')
    st.caption('Project notes and reports remain project evidence even when they mention NCC. Select NCC or Housing only for a code publication, with its actual edition and volume.')
    edition=st.text_input('Reference edition / volume',placeholder='For NCC references, enter the actual edition and volume',key=f'dm_edition_{scope}')
    if kind in ('NCC','Housing') and not edition.strip():st.caption('Enter an edition and volume to enable indexing.')
    if st.button('Upload and index',type='primary',disabled=file is None or oversized or (kind in ('NCC','Housing') and not edition.strip()),key=f'dm_submit_{scope}'):
        try:
            with st.status('Storing and indexing this document…',expanded=True) as progress:
                st.write('Validating the original and building the project search index.')
                result=store.upload(owner,project,file.name,file.getvalue(),None if kind=='Auto-detect' else kind.lower(),edition)
                progress.update(label='Document ready',state='complete',expanded=False)
            st.success(f"Version {result['version']} is ready: {result['chunks']} searchable chunks. Repeating the identical active upload does not charge again.")
        except (ValueError,PermissionError) as exc:st.error(str(exc))
        except Exception:st.error('Document processing could not complete. Existing active documents and reports remain available.')
    st.subheader('Project file library')
    try:
        library(owner,project)
        legacy=store.legacy_indexes(owner,project)
        if legacy:
            with st.expander('Earlier indexes without retained originals'):
                st.dataframe(legacy,hide_index=True,use_container_width=True)
                st.caption('Existing indexes are preserved. Their original files cannot be reconstructed; re-upload the source to start a managed version history.')
    except Exception as exc:
        import logging,traceback
        logging.getLogger(__name__).error('File library rendering failed (%s) at %s',type(exc).__name__,[(item.name,item.lineno) for item in traceback.extract_tb(exc.__traceback__)])
        st.error('The file library could not be loaded. Please retry or contact the administrator.')
