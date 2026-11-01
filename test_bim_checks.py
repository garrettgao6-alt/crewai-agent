from io import BytesIO
from pathlib import Path
import json
import pytest
import ifcopenshell
from test_document_management import system,legacy_system
from core import bim_checks,document_store
import report_store,subscription_store


def model_bytes(duplicate=False,units=True):
    model=ifcopenshell.file(schema='IFC4')
    unit=model.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Prefix='MILLI',Name='METRE')
    assignment=model.create_entity('IfcUnitAssignment',Units=[unit]) if units else None
    model.create_entity('IfcProject',GlobalId=ifcopenshell.guid.new(),Name='Synthetic project',UnitsInContext=assignment)
    storey=model.create_entity('IfcBuildingStorey',GlobalId=ifcopenshell.guid.new(),Name='Level 1')
    door=model.create_entity('IfcDoor',GlobalId=ifcopenshell.guid.new(),Name='Door',OverallWidth=900.,OverallHeight=2100.)
    wall=model.create_entity('IfcWall',GlobalId=door.GlobalId if duplicate else ifcopenshell.guid.new(),Name='=Spreadsheet injection')
    model.create_entity('IfcRelContainedInSpatialStructure',GlobalId=ifcopenshell.guid.new(),RelatedElements=[door,wall],RelatingStructure=storey)
    return model.to_string().encode()


def test_real_ifc_parser_dimensions_and_element_linked_findings(tmp_path):
    file=tmp_path/'model.bin';file.write_bytes(model_bytes(duplicate=True))
    result=bim_checks.inspect_file(file)
    assert result['schema']=='IFC4' and result['element_count']==2
    assert result['length_unit_to_metres']==0.001
    assert result['dimension_samples'][0]['OverallWidth_metres']==pytest.approx(.9)
    issue=next(i for i in result['issues'] if i['rule']=='GLOBAL_ID')
    assert issue['entity_id']>0 and issue['global_id']
    assert result['ai_tokens_used']==0 and any('clash' in text for text in result['limitations'])


def test_missing_units_never_invent_dimension_conversions(tmp_path):
    file=tmp_path/'model.ifc';file.write_bytes(model_bytes(units=False))
    result=bim_checks.inspect_file(file)
    assert result['length_unit_to_metres'] is None
    assert not any('OverallWidth_metres' in row for row in result['dimension_samples'])
    assert any(issue['rule']=='UNITS' for issue in result['issues'])


def test_ifc_pipeline_retains_original_saves_once_and_denies_other_projects(system):
    a,b,p,q,_=system;data=model_bytes()
    version,report=bim_checks.import_model(a['id'],p['id'],'model.ifc',data)
    again,second=bim_checks.import_model(a['id'],p['id'],'model.ifc',data)
    assert report['id']==second['id'] and version['id']==again['id']
    assert subscription_store.get_usage(a['id'])['current_document_count']==1
    assert document_store.original(a['id'],p['id'],version['file_id'],version['id'])==data
    with pytest.raises(PermissionError):report_store.get_report(b['id'],p['id'],report['id'])
    with pytest.raises(PermissionError):document_store.original(a['id'],q['id'],version['file_id'],version['id'])
    assert report_store.get_report(a['id'],p['id'],report['id'])['bim_analysis']['element_count']==2


def test_bad_ifc_is_not_successful_or_charged(system):
    a,_,p,_,_=system
    with pytest.raises(ValueError):bim_checks.import_model(a['id'],p['id'],'bad.ifc',b'Not an IFC file')
    assert not report_store.list_reports(a['id'],p['id'])
    assert subscription_store.get_usage(a['id'])['current_document_count']==0
    assert document_store.list_files(a['id'],p['id'])[0]['status']=='failed'


def test_issue_csv_neutralizes_formula_injection():
    data=bim_checks.issues_csv({'issues':[{'name':'=HYPERLINK("x")','detail':'+1','rule':'TEST','severity':'warning'}]}).decode('utf-8-sig')
    assert "'=HYPERLINK" in data and "'+1" in data


def test_bim_page_restores_private_inspection_and_exports(system,monkeypatch):
    from streamlit.testing.v1 import AppTest
    import project_store,template_store,user_store
    a,_,p,_,_=system;bim_checks.import_model(a['id'],p['id'],'model.ifc',model_bytes())
    monkeypatch.setattr(template_store,'DB_PATH',Path(project_store.DB_PATH).with_name('templates.db'))
    token=user_store.create_session(a['id'])
    source=Path('streamlit_app.py').read_text().replace('auth_cookies = initialize_cookie_manager()',f'auth_cookies = {{"session_token": {token!r}}}')
    app=AppTest.from_string(source,default_timeout=30).run()
    app.session_state['active_project_id']=p['id'];app.session_state['active_section']='BIM';app.run()
    assert not app.exception
    html=' '.join(item.value for item in app.markdown)
    assert 'Download issues CSV' in html and 'Download inspection JSON' in html and 'Download original' in html
    assert '/media/' not in html


def test_bim_report_listing_is_project_scoped_metadata_only(system):
    a,b,p,q,_=system;_,report=bim_checks.import_model(a['id'],p['id'],'model.ifc',model_bytes())
    rows=report_store.list_report_summaries(a['id'],p['id'],category='bim')
    assert rows[0]['id']==report['id'] and 'bim_analysis' not in rows[0] and 'result' not in rows[0]
    assert report_store.list_report_summaries(a['id'],q['id'],category='bim')==[]
    with pytest.raises(PermissionError):report_store.list_report_summaries(b['id'],p['id'],category='bim')
