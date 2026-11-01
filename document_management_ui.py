"""Persistent, project-owned file management; all mutations authorize again in the store."""
import streamlit as st
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
        st.info('No archived files.' if archived else 'No managed files yet.')
        return
    st.dataframe([{'File':f['name'],'Active version':f.get('version'),'Status':f.get('status'),'Type':f.get('kind'),'Size KB':round((f.get('size') or 0)/1024,1),'Search chunks':f.get('chunks') or 0} for f in files],hide_index=True,use_container_width=True)
    chosen=st.selectbox('Manage file',files,format_func=lambda f:f['name'],key=f'dm_file_{scope}_{archived}_{only_bim}')
    history=store.versions(owner,project,chosen['id'])
    selected=st.selectbox('Retained version',history,format_func=lambda v:f"v{v['version']} · {v['status']} · {v['created']}",key=f"dm_version_{scope}_{chosen['id']}_{only_bim}")
    st.caption('Original SHA-256: '+selected['sha'])
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
    st.caption('Limits: 50 MB/file, 80 KB extracted text and 60 search chunks; 600 MB and 1,000 retained versions/account. Scans need OCR first. Office tables/cells are read; spreadsheet formulas are not recalculated. DOCX/XLSX section numbers are not PDF page numbers.')
    scope=f'{owner}_{project}'
    file=st.file_uploader('Upload a document',type=['pdf','txt','docx','xlsx'],key=f'dm_upload_{scope}')
    kind=st.selectbox('Document type',['Auto-detect','Business','NCC','Housing'],key=f'dm_kind_{scope}')
    edition=st.text_input('Reference edition / volume',placeholder='Required when the content is an NCC reference',key=f'dm_edition_{scope}')
    if st.button('Upload and index',type='primary',disabled=file is None,key=f'dm_submit_{scope}'):
        try:
            with st.spinner('Storing original and indexing this project version…'):
                result=store.upload(owner,project,file.name,file.getvalue(),None if kind=='Auto-detect' else kind.lower(),edition)
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
    except Exception:st.error('The file library could not be loaded. Please retry or contact the administrator.')
