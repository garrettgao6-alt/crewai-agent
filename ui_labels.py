"""Read-only presentation helpers. Never change stored records or authorization values."""
from pathlib import PurePosixPath
import re

STATUS = {'ready':'Ready','processing':'Processing','failed':'Could not process','draft':'Draft',
          'complete':'Completed','completed':'Completed','success':'Completed','saved':'Saved',
          'insufficient_evidence':'More evidence needed','archived':'Archived','pending':'Waiting',
          'active':'Active','inactive':'Inactive','error':'Needs attention','warning':'Review needed','info':'Information'}
KINDS = {'business':'Project document','general':'Project document','ncc':'NCC reference',
         'housing':'Housing reference','bim':'IFC model','auto':'Automatic selection'}
CHECKS = {'PROJECT':'Project definition','UNITS':'Model units','GLOBAL_ID':'IFC identifiers',
          'NAME':'Element names','CONTAINER':'Spatial containment','REPRESENTATION':'Shape information',
          'DIMENSION':'Overall dimensions','PLACEMENT':'Element placement'}
ROLES = {'admin':'Administrator','user':'Member','guest':'Guest','member':'Member'}


def status_label(value):return STATUS.get(str(value).lower(),'Not available')
def kind_label(value):return KINDS.get(str(value).lower(),'Document')
def check_label(value):return CHECKS.get(str(value),'Model data check')
def severity_label(value):return {'error':'Error','warning':'Warning','info':'Information'}.get(str(value).lower(),'Not specified')
def role_label(value):return ROLES.get(str(value).lower(),'Member')


def ifc_label(value):
    name=str(value or '')
    if not name:return 'Not supplied'
    words=re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',name.removeprefix('Ifc'))
    return f'{words} ({name})' if name.startswith('Ifc') else 'Model element'


def confidence_label(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool) and 0<=value<=1:return f'{value:.0%}'
    if str(value).lower() in {'high','medium','low'}:return str(value).title()
    return 'Not available'


def model_text(value):
    text=str(value or '')
    for old,new in [('OverallWidth_metres','Overall width (m)'),('OverallHeight_metres','Overall height (m)'),
                    ('OverallWidth','Overall width'),('OverallHeight','Overall height'),('GlobalId','IFC identifier')]:
        text=text.replace(old,new)
    return text


def finding_rows(rows):
    return [{'Check':check_label(row.get('rule')),'Severity':severity_label(row.get('severity')),
             'Element number':row.get('entity_id') or 'Project','IFC identifier':row.get('global_id') or 'Not supplied',
             'IFC element type':ifc_label(row.get('ifc_class')),'Element name':row.get('name') or 'Not supplied',
             'Finding':model_text(row.get('detail'))} for row in rows]


def dimension_rows(rows):
    return [{'Element number':row.get('entity_id'),'IFC identifier':row.get('global_id') or 'Not supplied',
             'IFC element type':ifc_label(row.get('ifc_class')),
             'Overall width (m)':row.get('OverallWidth_metres') if row.get('OverallWidth_metres') is not None else 'Not available',
             'Overall height (m)':row.get('OverallHeight_metres') if row.get('OverallHeight_metres') is not None else 'Not available'} for row in rows]


def source_details(source):
    """Allowlist readable citation fields; exclude owner IDs, hashes, paths and nested data."""
    metadata=source.get('metadata') or {}
    if not isinstance(metadata,dict):return []
    details=[]
    fields=[('source','Document'),('code','Publication / edition'),('edition','Edition'),
            ('clause','Clause'),('section','Section'),('page','Page'),('page_end','Last page'),
            ('jurisdiction','Project jurisdiction'),('source_jurisdiction','Publication jurisdiction')]
    for key,label in fields:
        value=metadata.get(key)
        if value is None or value=='' or not isinstance(value,(str,int,float)):continue
        if key=='source':value=PurePosixPath(str(value).replace('\\','/')).name
        details.append((label,str(value)))
    kinds={'server_local_ncc':'Private NCC library','project_ncc':'Project NCC reference','ifc_model':'IFC model'}
    if metadata.get('reference_kind') in kinds:details.append(('Evidence type',kinds[metadata['reference_kind']]))
    if isinstance(metadata.get('complete_section'),bool):details.append(('Full clause included','Yes' if metadata['complete_section'] else 'No — review the complete publication'))
    reasons={'primary':'Matched to the review question','cross-reference':'Referenced by another provision','page':'Page excerpt'}
    if metadata.get('selection_reason') in reasons:details.append(('Why included',reasons[metadata['selection_reason']]))
    for warning in metadata.get('coverage_warnings',[]) if isinstance(metadata.get('coverage_warnings'),list) else []:
        if isinstance(warning,str):details.append(('Coverage note',warning))
    return details


def report_text(entry):
    """Readable view of generated BIM findings; all other authored analysis stays verbatim."""
    analysis=entry.get('bim_analysis')
    if not isinstance(analysis,dict):return str(entry.get('result',''))
    lines=[str(entry.get('query') or 'IFC model data review'),f"Model format: {analysis.get('schema','Not supplied')}",
           f"Elements inspected: {analysis.get('element_count',0):,}",f"Findings: {analysis.get('issue_count',0):,}"]
    for row in analysis.get('issues',[]):
        element=f"Element {row['entity_id']}" if row.get('entity_id') else 'Project'
        if row.get('global_id'):element+=f" · IFC identifier: {row['global_id']}"
        lines.append(f"{check_label(row.get('rule'))} — {element}: {model_text(row.get('detail'))}")
    lines.extend(str(v) for v in analysis.get('limitations',[]) if isinstance(v,str))
    return '\n\n'.join(lines)


def friendly_error(error, fallback='This action could not be completed. Please retry or contact the administrator.'):
    text=str(error)
    if 'NCC_DOCUMENT_ROOT' in text:return 'The server NCC library has not been configured. Ask the administrator to enable it.'
    # Do not turn operating-system/provider details into a product message.
    if any(token in text for token in ('[Errno','Traceback','sqlite3.','SELECT ','INSERT ','/root/','/srv/','/var/','/Users/','api_key','API_KEY','Bearer ')):
        return fallback
    if text.lstrip().startswith(('{','[')):return fallback
    return text or fallback
