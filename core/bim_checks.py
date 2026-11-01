"""Deterministic IFC data checks. No geometric clashes or NCC approval conclusions are inferred."""
from collections import Counter
from pathlib import Path
import csv,hashlib,io,json,math,re,uuid

RULES={
 'PROJECT':'Exactly one IfcProject should define this inspection context.',
 'UNITS':'The project must declare a length unit before dimensions are converted.',
 'GLOBAL_ID':'IfcRoot identifiers must be valid, unique IFC GUIDs.',
 'NAME':'Named elements are easier to trace in an issue workflow.',
 'CONTAINER':'An IfcElement should have a spatial container.',
 'REPRESENTATION':'Geometry availability is reported; geometry is not tessellated or clash-tested.',
 'DIMENSION':'IfcDoor/IfcWindow overall dimensions, when present, must be positive.',
 'PLACEMENT':'Local/project placement coordinates must be finite. Large offsets require review.'}

def inspect_file(path):
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.util.unit
    import ifcopenshell.util.placement
    data=Path(path).read_bytes()
    if len(data)>20*1024*1024:raise ValueError('IFC models are limited to 20 MB.')
    if not data.lstrip().startswith(b'ISO-10303-21;'):raise ValueError('Upload an IFC STEP (.ifc) file. IFCZIP, IFCXML, RVT and NWD are not supported.')
    if len(re.findall(rb'#\d+\s*=',data))>100000:raise ValueError('The model exceeds 100,000 IFC entities. Export a smaller model.')
    try:model=ifcopenshell.open(str(path),format='.ifc')
    except Exception:raise ValueError('The IFC STEP file could not be parsed.') from None
    projects=model.by_type('IfcProject');roots=model.by_type('IfcRoot');elements=model.by_type('IfcElement')
    if len(elements)>20000:raise ValueError('The model exceeds 20,000 elements. Export a smaller model.')
    issues=[];total=0
    def issue(rule,entity=None,detail='',severity='warning'):
        nonlocal total
        total+=1
        if len(issues)>=1000:return
        issues.append({'rule':rule,'severity':severity,'entity_id':entity.id() if entity else 0,'global_id':str(getattr(entity,'GlobalId','') or '')[:100] if entity else '', 'ifc_class':entity.is_a() if entity else 'IfcProject','name':str(getattr(entity,'Name','') or '')[:150] if entity else '', 'detail':detail[:300]})
    if len(projects)!=1:issue('PROJECT',detail=f'Found {len(projects)} projects; expected one.',severity='error')
    scale=None
    if len(projects)==1:
        assignment=projects[0].UnitsInContext
        if assignment and any(getattr(unit,'UnitType',None)=='LENGTHUNIT' for unit in assignment.Units):
            try:
                scale=float(ifcopenshell.util.unit.calculate_unit_scale(model))
                if not math.isfinite(scale) or scale<=0:scale=None
            except Exception:scale=None
    if scale is None:issue('UNITS',detail='Length units are unavailable or invalid; no metre conversion or dimensional compliance claim was made.',severity='error')
    seen={}
    for entity in roots:
        guid=getattr(entity,'GlobalId',None)
        try:
            if not guid or len(guid)!=22 or not re.fullmatch('[0-3][0-9A-Za-z_$]{21}',guid):raise ValueError()
            ifcopenshell.guid.expand(guid)
        except Exception:issue('GLOBAL_ID',entity,'Invalid or missing GlobalId.','error')
        if guid in seen:issue('GLOBAL_ID',entity,f'Duplicate GlobalId also used by entity #{seen[guid]}.','error')
        seen[guid]=entity.id()
    counts=Counter();represented=0;dimensions=[]
    for entity in elements:
        counts[entity.is_a()]+=1
        if not getattr(entity,'Name',None):issue('NAME',entity,'Element has no name.')
        try:container=ifcopenshell.util.element.get_container(entity)
        except Exception:container=None
        if container is None and not entity.is_a('IfcOpeningElement'):issue('CONTAINER',entity,'No spatial container could be resolved.')
        if getattr(entity,'Representation',None):represented+=1
        else:issue('REPRESENTATION',entity,'No shape representation is attached; geometry checks were not run.')
        if entity.is_a('IfcDoor') or entity.is_a('IfcWindow'):
            row={'entity_id':entity.id(),'global_id':str(entity.GlobalId or ''),'ifc_class':entity.is_a()}
            for attribute in ('OverallWidth','OverallHeight'):
                value=getattr(entity,attribute,None)
                if value is None:issue('DIMENSION',entity,attribute+' is not supplied.')
                elif not math.isfinite(float(value)) or value<=0:issue('DIMENSION',entity,attribute+' is not a positive finite value.','error')
                elif scale is not None:row[attribute+'_metres']=float(value)*scale
            if len(dimensions)<1000:dimensions.append(row)
        placement=getattr(entity,'ObjectPlacement',None)
        if placement:
            try:
                matrix=ifcopenshell.util.placement.get_local_placement(placement)
                coordinates=[float(matrix[i,3]) for i in range(3)]
                if not all(math.isfinite(v) for v in coordinates):issue('PLACEMENT',entity,'Placement has non-finite coordinates.','error')
                elif scale and max(abs(v)*scale for v in coordinates)>1000000:issue('PLACEMENT',entity,'Project-space position is over 1,000 km from the origin; check georeferencing and units.')
            except Exception:issue('PLACEMENT',entity,'Placement could not be resolved safely.','error')
    return {'schema':model.schema,'model_sha256':hashlib.sha256(data).hexdigest(),'element_count':len(elements),'ifc_class_counts':dict(sorted(counts.items())),'length_unit_to_metres':scale,'elements_with_representation':represented,'issue_count':total,'issues':issues,'issues_truncated':total>len(issues),'dimension_samples':dimensions,'rules':RULES,'limitations':['Data-quality inspection only; not NCC certification or a compliance conclusion.','No tessellation, geometric clash detection, quantity take-off or Revit/Navisworks parsing.','Door/window overall dimensions are not verified clear-opening dimensions.','Issue rows and dimension samples are limited to 1,000; all inspected elements contribute to counts.'],'ai_tokens_used':0}

def import_model(owner,project,name,data):
    from core import document_store
    import report_store
    from core.file_processing import run
    if Path(name).suffix.lower()!='.ifc':raise ValueError('Upload an .ifc model.')
    if len(data)>20*1024*1024:raise ValueError('IFC models are limited to 20 MB.')
    version=document_store.upload(owner,project,name,data,kind='bim',local_processor=lambda path:run('ifc',path,name))
    analysis=json.loads(version['analysis']);report_id=uuid.uuid5(uuid.NAMESPACE_URL,'gao-bim:'+version['id']).hex
    lines=[f"IFC data-quality inspection: {name}",f"Schema: {analysis['schema']}",f"Elements inspected: {analysis['element_count']}",f"Data-quality findings: {analysis['issue_count']}"]
    lines.extend(f"{issue['rule']} — entity #{issue['entity_id']} ({issue['global_id']}): {issue['detail']}" for issue in analysis['issues'])
    lines.extend(analysis['limitations'])
    report=report_store.save_report(owner,project,{'query':'Inspect IFC model data: '+name,'mode':'BIM Model Checks','category':'bim','result':'\n\n'.join(lines),'status':'draft','version':'BIM data checks 1.0','bim_analysis':analysis,'document_file_id':version['file_id'],'document_version_id':version['id'],'sources':[{'text':'IFC model inspected locally; see the element-linked issue records.','metadata':{'source':name,'document_sha256':version['sha'],'reference_kind':'ifc_model','user_id':str(owner),'project_id':int(project)}}]},report_id=report_id)
    return version,report

def issues_csv(analysis):
    fields=['rule','severity','entity_id','global_id','ifc_class','name','detail'];output=io.StringIO();writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for item in analysis.get('issues',[]):
        clean={k:("'"+str(item.get(k,'')) if str(item.get(k,'')).lstrip().startswith(('=','+','-','@')) else item.get(k,'')) for k in fields};writer.writerow(clean)
    return output.getvalue().encode('utf-8-sig')
