"""User-facing views preserve data, domain identifiers and project boundaries."""
from copy import deepcopy
from ui_labels import *


def test_sources_show_citation_fields_without_internal_metadata():
    source={'metadata':{'source':'/srv/private/ncc/volume.pdf','code':'NCC 2025 Volume One',
        'clause':'C2D2','page':5,'page_end':7,'user_id':123,'project_id':456,
        'managed_version_id':'PRIVATE_VERSION','document_sha256':'PRIVATE_HASH',
        'path':'/root/private','unexpected':{'internal_field':'PRIVATE_NESTED'},'complete_section':True,'selection_reason':'cross-reference','coverage_warnings':['External standard text is not supplied.']},'text':'Verbatim clause excerpt'}
    original=deepcopy(source);view=dict(source_details(source))
    assert view['Document']=='volume.pdf' and view['Clause']=='C2D2' and view['Page']=='5'
    assert view['Full clause included']=='Yes'
    assert view['Why included']=='Referenced by another provision'
    assert view['Coverage note']=='External standard text is not supplied.'
    assert not any(value in str(view) for value in ('PRIVATE_','/srv/','user_id','project_id','sha256'))
    assert source==original


def test_bim_views_preserve_element_identity_dimensions_and_filter_keys():
    row={'rule':'DIMENSION','severity':'warning','entity_id':42,'global_id':'IFC-IDENTIFIER',
         'ifc_class':'IfcDoor','name':'Entry door','detail':'OverallWidth is not supplied.'}
    dimensions=[{'entity_id':42,'global_id':'IFC-IDENTIFIER','ifc_class':'IfcDoor','OverallWidth_metres':.9}]
    original=deepcopy((row,dimensions))
    view=finding_rows([row])[0]
    assert view['Check']=='Overall dimensions' and view['Finding']=='Overall width is not supplied.'
    assert view['Element number']==42 and view['IFC identifier']=='IFC-IDENTIFIER'
    assert view['IFC element type']=='Door (IfcDoor)'
    assert dimension_rows(dimensions)[0]['Overall width (m)']==.9
    assert dimension_rows(dimensions)[0]['Overall height (m)']=='Not available'
    assert (row,dimensions)==original


def test_friendly_status_errors_and_authored_results():
    assert status_label('insufficient_evidence')=='More evidence needed'
    assert kind_label('business')=='Project document'
    assert role_label('admin')=='Administrator'
    assert confidence_label(.85)=='85%' and confidence_label(None)=='Not available'
    assert 'NCC_DOCUMENT_ROOT' not in friendly_error('Configure NCC_DOCUMENT_ROOT')
    assert '/root/' not in friendly_error('[Errno 2] /root/private/file.pdf')
    assert friendly_error('Monthly document quota reached.')=='Monthly document quota reached.'
    assert friendly_error('{"internal_field":"value"}').startswith('This action')
    authored={'result':'Keep the author’s exact source clauses, C2D2, and quoted data.'}
    assert report_text(authored)==authored['result']


from test_document_management import system, legacy_system

def test_saved_report_evidence_is_readable_and_project_scoped(system,monkeypatch):
    from test_ui_workflows import signed_app
    import report_store
    owner,_,project,other,_=system
    report=report_store.save_report(owner['id'],project['id'],{'query':'Readable evidence','result':'ORIGINAL_REPORT_BODY',
        'status':'insufficient_evidence','sources':[{'text':'ORIGINAL_SOURCE_EXCERPT','sha256':'HIDDEN_SNAPSHOT_HASH',
        'metadata':{'source':'evidence.pdf','page':2,'clause':'C2D2','user_id':owner['id'],
                    'project_id':project['id'],'managed_version_id':'HIDDEN_VERSION_ID','storage_path':'/root/hidden'}}]})
    before=deepcopy(report_store.get_report(owner['id'],project['id'],report['id']))
    app,_,_,_=signed_app(system,monkeypatch)
    app.button(key='quick_nav_Reports').click().run()
    assert not app.exception and not app.get('json')
    text=' '.join(item.value for item in app.text)
    assert 'Document: evidence.pdf' in text and 'Clause: C2D2' in text and 'Page: 2' in text
    assert 'ORIGINAL_SOURCE_EXCERPT' in text
    assert not any(v in text for v in ('user_id','project_id','HIDDEN_', '/root/hidden'))
    assert any('More evidence needed' in item.value for item in app.caption)
    assert report_store.get_report(owner['id'],project['id'],report['id'])==before
    app.selectbox(key='workspace_project_'+str(owner['id'])).select(other['id']).run()
    assert not any('ORIGINAL_SOURCE_EXCERPT' in item.value for item in app.text)


def test_document_labels_preserve_versions_originals_and_stored_values(system,monkeypatch):
    from test_ui_workflows import signed_app
    from core import document_store
    owner,_,project,_,_=system
    version=document_store.upload(owner['id'],project['id'],'evidence.txt',b'Original evidence remains unchanged',kind='business')
    app,_,_,_=signed_app(system,monkeypatch)
    app.button(key='quick_nav_Documents').click().run()
    assert not app.exception and not app.get('json')
    row=app.dataframe[0].value.iloc[0]
    assert row['Status']=='Ready' and row['Type']=='Project document'
    assert not any('SHA-256' in item.value for item in app.caption)
    assert any('Status: Ready' in item.value for item in app.text)
    assert document_store.get_version(owner['id'],project['id'],version['file_id'],version['id'])['status']=='ready'
    assert document_store.original(owner['id'],project['id'],version['file_id'],version['id'])==b'Original evidence remains unchanged'
