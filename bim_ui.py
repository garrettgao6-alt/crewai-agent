import json
import streamlit as st
from core import bim_checks,document_store
import report_store
from ui_theme import saved_time
from private_download import render as private_download
from document_management_ui import library

def render(owner,project):
    st.caption('Inspect real IFC model data locally: identifiers, units, containment, representation availability, door/window dimensions and placements. No AI tokens are used. One monthly document allowance is used for each new successful model version.')
    st.info('These are model data-quality checks. Geometric clashes, quantities, RVT/NWD files and NCC certification are not evaluated.')
    file=st.file_uploader('IFC STEP model',type=['ifc'],key=f'bim_upload_{owner}_{project}')
    st.caption('Limits: 20 MB, 100,000 entities, 20,000 elements and a 40-second parser deadline. Issue exports are capped at 1,000 rows and disclose truncation.')
    oversized=file is not None and file.size>20*1024**2
    if oversized:st.error('This model exceeds 20 MB. Export a smaller IFC model before inspection.')
    if st.button('Inspect IFC and save report',type='primary',disabled=file is None or oversized,key=f'bim_run_{owner}_{project}'):
        try:
            with st.status('Inspecting IFC model…',expanded=True) as progress:
                st.write('Checking model structure, units, identifiers and element data locally.')
                version,report=bim_checks.import_model(owner,project,file.name,file.getvalue())
                progress.update(label='Inspection saved',state='complete',expanded=False)
            st.success('Model checks saved to Reports. Original and version history are retained in this project.')
        except (ValueError,PermissionError) as exc:st.error(str(exc))
        except Exception:st.error('The model inspection could not complete. The preceding active version is preserved; retry to recover a saved inspection.')
    reports=report_store.list_report_summaries(owner,project,category='bim')
    if reports:
        selected=st.selectbox('Saved model inspection',reports,format_func=lambda r:(r.get('query') or 'IFC inspection')+' · '+saved_time(r['created_at']),key=f'bim_report_{owner}_{project}')
        report=report_store.get_report(owner,project,selected['id'])
        analysis=report['bim_analysis']
        with st.container(key="bim_metrics"):
            metrics=st.columns(3)
            for column,label,value in zip(metrics,('Elements inspected','Findings','AI tokens'),(analysis['element_count'],analysis['issue_count'],0)):
                column.metric(label,value)
        st.caption('Schema: '+analysis['schema']+' · Length-unit scale to metres: '+str(analysis['length_unit_to_metres']))
        st.dataframe([{'IFC class':k,'Count':v} for k,v in analysis['ifc_class_counts'].items()],hide_index=True,use_container_width=True)
        if analysis['issues_truncated']:st.warning('The issue table is truncated to 1,000 rows. Total findings: '+str(analysis['issue_count']))
        if analysis['issues']:
            st.subheader('Element findings')
            severity=st.multiselect('Severity',sorted({row['severity'] for row in analysis['issues']}),default=sorted({row['severity'] for row in analysis['issues']}),key=f'bim_severity_{owner}_{project}_{report["id"]}')
            rule=st.selectbox('Check', ['All checks']+sorted({row['rule'] for row in analysis['issues']}),key=f'bim_rule_{owner}_{project}_{report["id"]}')
            query=st.text_input('Find an element',placeholder='Name, GlobalId or entity number',key=f'bim_find_{owner}_{project}_{report["id"]}')
            visible=[row for row in analysis['issues'] if row['severity'] in severity and (rule=='All checks' or row['rule']==rule) and query.casefold() in (' '.join(str(row.get(key,'')) for key in ('name','global_id','entity_id','ifc_class'))).casefold()]
            st.caption(f'{len(visible)} of {len(analysis["issues"])} retained findings shown. Downloads contain the full saved inspection.')
            if visible:st.dataframe(visible,hide_index=True,use_container_width=True)
            else:st.info('No findings match these filters. Clear the search or change the severity and check.')
        else:st.info('No findings from the implemented data checks. This is not a compliance or clash-free certificate.')
        if analysis['dimension_samples']:
            with st.expander('Recorded overall dimensions in metres'):
                st.dataframe(analysis['dimension_samples'],hide_index=True,use_container_width=True)
                st.caption('Overall dimensions are not verified clear openings.')
        private_download('Download issues CSV',owner,project,'bim_csv',report['id'])
        private_download('Download inspection JSON',owner,project,'bim_json',report['id'])
    st.subheader('Retained IFC originals and versions')
    library(owner,project,only_bim=True)
