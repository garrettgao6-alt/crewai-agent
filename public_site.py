"""Deterministic public product pages. Never imports application stores or secrets."""
from html import escape as e
import json
from pathlib import Path
import sys
from urllib.parse import urlencode, quote

ORIGIN='https://www.gaointelligence.com'
REVIEWED='2026-11-03'
PAGES={
'':('Construction AI, NCC references and IFC checks','Gao Intelligence helps Australian construction teams review project evidence, retrieve NCC references, check IFC models and save reports.',[
('What is Gao Intelligence?','Gao Intelligence (GaoIntelligence, also written gaointelligence), available at gaointelligence.com, is a construction analysis workspace for NCC reference retrieval, document management, IFC model quality checks and saved reports. It helps teams organise evidence and draft reviews for professional assessment.'),
('Try a real workflow','Open the workspace to try public synthetic examples without registering. Guest AI analysis has server-enforced daily request and token limits. Sign in to manage private projects and documents.'),
('Evidence before conclusions','Review the cited publication, clause and PDF page alongside each finding. Missing information and reference coverage can affect the result. Outputs support professional judgement; they do not certify compliance.')]),
'ncc-review':('NCC 2025 reference retrieval and review','Find relevant NCC 2025 references using project context, then inspect clause citations and source pages in Gao Intelligence.',[
('How does NCC reference matching work?','Provide the building class, jurisdiction, project circumstances and question. The workspace retrieves relevant passages from the configured NCC library and uses them to support a draft analysis, with source references for review.'),
('Which NCC publications are used?','The configured 2025 collection includes Volume One, Volume Two and Housing Provisions. Building class helps determine relevant volumes. Confirm the applicable edition, state or territory adoption rules and approval date before relying on a provision.'),
('What can be missing?','A retrieved passage is not proof that every applicable requirement has been checked. Referenced external standards, project evidence, exceptions and jurisdictional variations may require further review. Inspect coverage warnings and the original publication.'),
('Is this a compliance certificate?','No. AI analysis is a draft aid and can be incomplete or incorrect. A qualified professional must verify applicable requirements, evidence and conclusions.')]),
'ifc-model-checks':('IFC model quality checks for construction','Check IFC model identifiers, units, containment and selected element properties, with clear limits and saved findings.',[
('What does the IFC checker inspect?','The checker parses IFC STEP files and examines identifiers, units, spatial containment, representation availability, placements and selected door and window dimensions. Findings help identify model information that needs review.'),
('Does it detect geometric clashes?','No. These are model data quality checks, not geometric clash detection, quantity takeoff or compliance certification. Native RVT and NWD files are not supported by this checker.'),
('What are the model limits?','The checker accepts IFC files up to 20 MB and applies entity, element and processing-time limits. Truncation is disclosed. The parser checks do not consume AI tokens; account document allowances still apply.')]),
'document-management':('Project document management and version history','Retain project document originals, review versions and retrieve searchable evidence within an authenticated project workspace.',[
('Which files can I search?','PDF, TXT, DOCX and XLSX documents can provide searchable text. Scanned PDFs need OCR before reliable text retrieval. Spreadsheet formula results are not recalculated during extraction.'),
('Are original files retained?','Managed documents retain originals and version history within their project. Authenticated download access is checked against the current account and project. Archive and recovery controls help manage revisions.'),
('Are extraction limits visible?','Project uploads have a 50 MB per-file limit and bounded text extraction and chunk counts. A large document can be retained while only part of its text is searchable. Review extraction notices; the private NCC library uses a separate import workflow.'),
('Can the website read a desktop path?','A server cannot read a path on your computer. Upload the file to your private project, or configure the supported server-side NCC library workflow with an authorised server directory.')]),
'reports':('Saved construction analysis reports and evidence','Save project-scoped analysis reports with source snapshots so findings remain linked to the evidence used for the review.',[
('What is saved in a report?','Reports preserve the analysis result and the source evidence snapshot used for that result. Saved reports belong to a specific project and require authorised access.'),
('Does replacing a document rewrite old reports?','No. A previous source snapshot does not silently update when the original document changes. Run a fresh analysis against the relevant revision and review the new findings.'),
('How should reports be used?','Check citations, document revisions and missing evidence before sharing conclusions. Reports are review aids and require professional judgement; they are not approval documents or compliance certificates.')]),
'data-boundaries':('Guest access and private project data boundaries','Understand guest examples, authenticated project access and AI processing boundaries in Gao Intelligence.',[
('Can guests read customer projects?','Guest analysis uses public synthetic evidence. Guests do not receive access to private project documents, saved customer reports or private NCC library paths. Private workflows require an authenticated account and authorised project.'),
('Where does AI processing happen?','When a private AI analysis is requested, relevant project excerpts may be sent to the configured AI provider. Consider the sensitivity of uploaded material and your organisation’s requirements before using the service.'),
('How are costs bounded?','Guest AI has server-enforced daily request and token budgets. The workspace shows current availability. Limits may prevent further requests until reset. IFC parser checks do not use AI tokens.'),
('Where is the account notice?','The Account and Email Privacy notice explains account and recovery-email handling. Read it before using account recovery. This product guide describes feature boundaries and is not a replacement for that notice.')])}
FAQ=[
('Can I try Gao Intelligence without registering?','Yes. Open the workspace for public synthetic examples and real guest AI within daily request and token limits. Private project uploads and saved customer reports require sign-in.'),
('Can guests access real customer documents?','No. Guest analysis uses public synthetic evidence and does not grant access to private projects, customer reports or private NCC library paths.'),
('How is the correct NCC reference selected?','Provide the building class, jurisdiction and project context. Relevant passages are retrieved from the configured collection. Verify the applicable edition, adoption date, exceptions and cited source pages.'),
('Does Gao Intelligence certify NCC compliance?','No. Outputs are draft review aids. A qualified professional must verify the applicable requirements, evidence and conclusions.'),
('Does BIM analysis include clash detection?','No. The IFC checker examines model information quality and selected properties. It does not perform geometric clash detection or support native RVT or NWD files.'),
('Do file revisions update saved reports automatically?','No. Saved reports retain their evidence snapshots. Run a new analysis against the revised documents to produce a new review.'),
('Does IFC checking spend AI tokens?','The IFC parser checks do not consume AI tokens. Account document allowances and processing limits still apply.'),
('Can the cloud workspace read my local file path?','No. Upload the file to your private project or use an authorised server-side library directory. A desktop path alone is not accessible to the server.')]
DEVICE_ANSWER=('Can I use Gao Intelligence on a phone, tablet or computer?','Yes. Gao Intelligence runs in a web browser at gaointelligence.com/workspace/ on phones, tablets and computers. Sign in to the same account and select the authorised project to open its saved documents and reports. Guest sample reports belong to the current browser session and do not automatically follow you to another device. Upload a file from a device that can access it; a desktop file path is not a cloud upload.')
CITATION_ANSWER=('How should I verify and cite a Gao Intelligence answer?','For an AI review, preserve the project, document revision, cited publication, clause or source page, and saved report evidence snapshot. Check the original source before using the conclusion. For a public product guide, cite its canonical page URL and displayed review date. A product guide is not an NCC provision, and neither the guide nor a draft AI answer is a compliance certificate.')
BRAND_ANSWER=('What does gaointelligence mean?','GaoIntelligence, also written gaointelligence, is the joined spelling of Gao Intelligence. The official website is gaointelligence.com. It is a construction AI platform for Australian teams reviewing NCC references, project documents, IFC model information and saved evidence-linked reports. Geospatial intelligence is a different term and is not the product described by this guide.')
FAQ.extend([DEVICE_ANSWER,CITATION_ANSWER,BRAND_ANSWER])
PAGES['faq']=('Gao Intelligence FAQ: NCC, BIM, documents and privacy','Answers about guest AI, NCC reference retrieval, IFC checks, document versions, saved reports and private project boundaries.',FAQ)

PAGES['']=('Construction AI platform for NCC and IFC reviews','Gao Intelligence (GaoIntelligence) is a construction AI platform for Australian teams: NCC 2025 reference search, document review, IFC model checks and saved reports.',PAGES[''][2])
PAGES['ncc-review']=('NCC AI tool for reference search and review','Use the Gao Intelligence NCC AI tool to find NCC 2025 references by project context. Review cited clauses, source pages and missing evidence before saving a report.',PAGES['ncc-review'][2])
PAGES['construction-ai-tools']=('Construction AI tools for Australian project teams','Choose a construction AI tool by task: NCC reference search, document review, IFC model data checks or evidence-linked reports. Explore the Gao Intelligence platform.',[
('What is a construction AI platform?','A construction AI platform brings project information and assisted review workflows into a shared workspace. Gao Intelligence connects project documents, NCC reference retrieval, IFC data quality checks and saved draft reports. Each workflow has different inputs, processing limits and review requirements.'),
('Which construction AI tool fits my task?','Use NCC reference search when you need to locate provisions for a specific building class and jurisdiction. Use construction document review to question retained project evidence. Use IFC model checks to inspect model information quality. Use saved reports to retain findings and their evidence snapshots.'),
('How should I evaluate an AI construction platform?','Test the same representative project question in each workflow. Check whether the result identifies the original document, revision and source page; whether missing evidence is disclosed; and whether a report can be reopened in the correct project. Assess project access controls and AI processing boundaries before uploading sensitive files.'),
('Does every construction AI tool need a language model?','No. The IFC parser performs bounded data checks locally without AI tokens. AI-assisted document and NCC reviews use the configured model and retrieval system. A shared platform does not make every check an AI judgement or an automated compliance approval.'),
('Can I try construction AI tools without signing up?','Gao Intelligence offers public synthetic examples and capped real guest AI. Sign in for private project uploads and saved customer reports. Guest access does not expose customer documents or private NCC paths.'),
('What is outside the current platform?','The IFC checker does not provide geometric clash detection, native RVT or NWD analysis, or compliance certification. The platform does not replace a quantity surveyor, building surveyor or other qualified reviewer. Confirm that your intended task is supported before relying on an output.')])
PAGES['ncc-review'][2].append(('What does an NCC AI tool do?','An NCC AI tool helps locate and explain National Construction Code references for a project question. Gao Intelligence retrieves passages from its configured NCC 2025 collection and links the draft review to source evidence. It is an NCC reference assistant, not an official ABCB service or a certification tool.'))
PAGES['document-management'][2].append(('How does AI construction document review use these files?','Retain the relevant originals in the intended project, review extraction notices, then ask a focused question in Copilot. The AI review uses retrieved excerpts, so inspect citations and missing evidence. Document storage and version history alone do not mean every page has been analysed.'))
PAGES['ifc-model-checks'][2].append(('Is an IFC checker the same as a BIM AI tool?','BIM AI tools cover many different tasks. The Gao Intelligence IFC checker specifically examines model data with a bounded parser; it does not use a language model for these checks. Choose it for identifiers, units, containment and selected properties, rather than geometric clash detection.'))

# Public, product-specific answers. No customer examples or application imports.
PAGES[''][2].append(('Who is Gao Intelligence for?','Gao Intelligence is for Australian construction teams reviewing documents, NCC references and IFC model information. It is an independent construction software workspace; it is not the Australian Building Codes Board or the U.S. Government Accountability Office.'))
PAGES[''][2].append(DEVICE_ANSWER)
PAGES[''][2].append(BRAND_ANSWER)
PAGES['construction-ai-tools'][2].append(DEVICE_ANSWER)
PAGES['ncc-review'][2].append(('What should I provide for an NCC review?','Start with the building class, state or territory, project approval date, applicable NCC edition and a specific review question. Add relevant drawings or specifications in your private project. Review the retrieved source pages and any missing evidence before using the draft report.'))
PAGES['ifc-model-checks'][2].append(('How do I review an IFC model?','Export an IFC STEP file from your modelling software, sign in, select the intended project and upload the model in BIM. Run the data checks, inspect findings by element and severity, then save the inspection report. The retained findings summary is not a measure of overall compliance.'))
PAGES['reports'][2].append(('What makes a result traceable?','Check the project, document revision, cited passage and source page together. A saved evidence snapshot records the material used for that analysis; it does not prove that all relevant provisions or documents were retrieved.'))

PAGES['about']=('About Gao Intelligence (GaoIntelligence)',
    'Gao Intelligence, also written GaoIntelligence or gaointelligence, is the construction AI workspace at gaointelligence.com. Read its purpose, supported workflows and evidence boundaries.',[
    ('What is the official Gao Intelligence website?',
     'Gao Intelligence (GaoIntelligence, also written gaointelligence) is the construction AI platform at gaointelligence.com. Its public product guides describe the same workspace available at gaointelligence.com/workspace/. The product helps Australian construction teams review NCC references, project documents, IFC model information and saved evidence-linked reports.'),
    ('Where should I start?',
     'Read the construction AI tools guide to choose a supported workflow. Open the workspace for public synthetic examples or sign in for authorised private projects. The product guides explain inputs, outputs and limitations; saved customer documents and reports remain inside the authorised project.'),
    ('How can I check an answer?',
     'For a public product description, use the canonical guide URL and its displayed review date. For an AI review, inspect the original publication, document revision, cited clause or page and saved evidence snapshot. A product guide is not an NCC provision, and a generated review is not a compliance certificate.'),
    ('Is Gao Intelligence a geospatial intelligence service?',
     'Gao Intelligence is an independent construction software workspace. Geospatial intelligence is a different field. The software described here supports construction document review, NCC reference retrieval, IFC data quality checks and saved reports.'),
    DEVICE_ANSWER])

SEO_TITLES={
    'about':'About Gao Intelligence (GaoIntelligence) | Official Product Guide',
    'construction-ai-tools':'Construction AI Tools & Platform Guide | Gao Intelligence',
    '':'Gao Intelligence | Construction AI Platform & NCC AI Tool',
    'ncc-review':'NCC AI Tool & NCC 2025 Reference Search | Gao Intelligence',
    'ifc-model-checks':'IFC Model Data Quality Checks | Gao Intelligence',
    'document-management':'Construction Document Management | Gao Intelligence',
    'reports':'Construction Reports & Evidence | Gao Intelligence',
    'data-boundaries':'Guest AI & Project Privacy | Gao Intelligence',
    'faq':'Construction AI, NCC & BIM FAQ | Gao Intelligence',
}
REFERENCES={
    'ncc-review':[('Australian Building Codes Board — National Construction Code','https://www.abcb.gov.au/'),('NCC online publications and resources','https://ncc.abcb.gov.au/')],
    'ifc-model-checks':[('buildingSMART — Industry Foundation Classes (IFC)','https://technical.buildingsmart.org/standards/IFC/')],
}

def section_id(index):return 'answer-'+str(index+1)

def workflow_comparison():
    rows=[
        ('NCC AI reference search','ncc-review','Building class, jurisdiction and a specific question','Cited passages and draft review','Uses AI for the requested review'),
        ('AI construction document review','document-management','Extractable project documents and a focused question','Evidence-linked draft findings','Uses AI for the requested review'),
        ('IFC model data checks','ifc-model-checks','IFC STEP model, up to 20 MB','Element findings and inspection report','Parser checks use no AI tokens'),
        ('Saved project reports','reports','Completed analysis in the authorised project','Retained result and evidence snapshot','Opening a saved report makes no new AI request'),
    ]
    body=''.join('<tr><th scope="row"><a href="'+url(slug)+'">'+e(name)+'</a></th><td>'+e(inputs)+'</td><td>'+e(output)+'</td><td>'+e(processing)+'</td></tr>' for name,slug,inputs,output,processing in rows)
    return '<section aria-labelledby="workflow-comparison-title"><h2 id="workflow-comparison-title">Choose a workflow by task</h2><div class="comparison-scroll" role="region" aria-label="Construction workflow comparison" tabindex="0"><table><caption>Gao Intelligence workflows, inputs and processing</caption><thead><tr><th scope="col">Workflow</th><th scope="col">What to provide</th><th scope="col">What to review</th><th scope="col">Processing</th></tr></thead><tbody>'+body+'</tbody></table></div></section>'


def answer_content(slug,sections):
    links=''.join(f'<li><a href="#{section_id(i)}">{e(q)}</a></li>' for i,(q,_) in enumerate(sections))
    contents='<nav class="guide-contents" aria-label="On this page"><strong>On this page</strong><ul>'+links+'</ul></nav>'
    answers=''.join((f'<details id="{section_id(i)}"><summary>{e(q)}</summary><p>{e(a)}</p></details>' if slug=='faq' else f'<section id="{section_id(i)}"><h2>{e(q)}</h2><p>{e(a)}</p></section>') for i,(q,a) in enumerate(sections))
    references=''
    if slug in REFERENCES:
        references='<section class="official-references"><h2>Official reference sources</h2><p>Use the publisher’s original material to verify terminology and requirements. These links do not imply endorsement of Gao Intelligence.</p><ul>'+''.join(f'<li><a href="{href}" rel="noopener noreferrer" target="_blank">{e(label)}</a></li>' for label,href in REFERENCES[slug])+'</ul></section>'
    return contents+(workflow_comparison() if slug=='construction-ai-tools' else '')+answers+references


def url(slug): return ORIGIN+('/discover/'+slug+'/' if slug else '/')
SOCIAL_CARDS={
    'about':('Gao Intelligence.','Construction evidence.'),
    'construction-ai-tools':('The right tool.','The right evidence.'),
    '':('Construction evidence,','connected.'),
    'ncc-review':('NCC references.','Project context.','Clearer review.'),
    'ifc-model-checks':('Better model data.','Clearer IFC findings.'),
    'document-management':('Every document.','Its original.','Its history.'),
    'reports':('Save the review.','Keep the evidence.'),
    'data-boundaries':('Public examples.','Private projects.','Clear boundaries.'),
    'faq':('Your questions,','answered clearly.'),
}

def social_image(slug):
    return '/seo-assets/share-v2-'+(slug or 'home')+'.png'

def social_metadata(slug):
    title,description,_=PAGES[slug]
    values={'og:type':'website','og:site_name':'Gao Intelligence','og:locale':'en_AU',
            'og:title':SEO_TITLES[slug],'og:description':description,'og:url':url(slug),
            'og:image':ORIGIN+social_image(slug),'og:image:secure_url':ORIGIN+social_image(slug),
            'og:image:type':'image/png','og:image:width':'1200','og:image:height':'630',
            'og:image:alt':'Gao Intelligence: '+' '.join(SOCIAL_CARDS[slug]),
            'twitter:card':'summary_large_image','twitter:title':SEO_TITLES[slug],
            'twitter:description':description,'twitter:image':ORIGIN+social_image(slug),
            'twitter:image:alt':'Gao Intelligence: '+' '.join(SOCIAL_CARDS[slug])}
    return ''.join(f'<meta {"name" if key.startswith("twitter:") else "property"}="{key}" content="{e(value)}">' for key,value in values.items())

def share_panel(slug):
    title,description,_=PAGES[slug]
    canonical=url(slug)
    post=description+'\n'+canonical+'\n#ConstructionAI #GaoIntelligence'
    links={
        'LinkedIn':'https://www.linkedin.com/sharing/share-offsite/?'+urlencode({'url':canonical}),
        'X':'https://twitter.com/intent/tweet?'+urlencode({'url':canonical,'text':description,'hashtags':'ConstructionAI'}),
        'WhatsApp':'https://wa.me/?'+urlencode({'text':description+' '+canonical}),
        'Facebook':'https://www.facebook.com/sharer/sharer.php?'+urlencode({'u':canonical}),
        'Email':'mailto:?'+urlencode({'subject':title+' | Gao Intelligence','body':post},quote_via=quote),
    }
    actions=''.join(f'<a class="button" href="{e(target)}" target="_blank" rel="noopener noreferrer nofollow" aria-label="Share this public guide via {name}">{name}</a>' for name,target in links.items())
    return f'''<section class="sharing" id="share" aria-labelledby="share-title" data-public-url="{canonical}" data-share-title="{e(title)}" data-share-description="{e(description)}"><div><p class="eyebrow">PASS IT ON</p><h2 id="share-title">Share this public guide</h2><p>Introduce the workflow to a colleague, research collaborator or project team.</p><p class="note">Only this public product guide is shared. Private documents, reports and account details stay in your workspace.</p><div class="share-actions"><button class="button primary" type="button" data-native-share hidden>Share…</button><button class="button" type="button" data-copy-link hidden>Copy public link</button>{actions}</div><label for="public-share-link">Public link</label><input id="public-share-link" type="url" value="{canonical}" readonly><p class="share-status note" role="status" aria-live="polite"></p><details><summary>Suggested post text</summary><label class="note" for="public-share-text">Edit the text in your social app before posting.</label><textarea id="public-share-text" rows="6" readonly>{e(post)}</textarea><button class="button" type="button" data-copy-post hidden>Copy post text</button></details></div><figure><img src="{social_image(slug)}" width="1200" height="630" loading="lazy" alt="Gao Intelligence: {e(' '.join(SOCIAL_CARDS[slug]))}"><figcaption><a href="{social_image(slug)}" target="_blank" rel="noopener">View share image</a>{' · <a href="/seo-assets/share-v2-home-square.png" target="_blank" rel="noopener">Square image</a>' if not slug else ''}</figcaption></figure></section>'''

SHARE_JS='''"use strict";
for (const panel of document.querySelectorAll("[data-public-url]")) {
  const status = panel.querySelector("[role=status]");
  const linkField = panel.querySelector("#public-share-link");
  const postField = panel.querySelector("#public-share-text");
  const copy = async (field, message) => {
    try {
      if (!navigator.clipboard || !window.isSecureContext) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(field.value);
      status.textContent = message;
    } catch {
      if (field === postField) field.closest("details").open = true;
      field.focus(); field.select();
      status.textContent = "Automatic copy is unavailable. The text is selected; copy it manually.";
    }
  };
  const copyLink = panel.querySelector("[data-copy-link]");
  copyLink.hidden = false;
  copyLink.addEventListener("click", () => copy(linkField, "Public link copied."));
  const copyPost = panel.querySelector("[data-copy-post]");
  copyPost.hidden = false;
  copyPost.addEventListener("click", () => copy(postField, "Public post text copied."));
  const native = panel.querySelector("[data-native-share]");
  if (navigator.share && window.isSecureContext) {
    native.hidden = false;
    native.addEventListener("click", async () => {
      try {
        await navigator.share({title: panel.dataset.shareTitle, text: panel.dataset.shareDescription, url: panel.dataset.publicUrl});
        status.textContent = "Share request handed to your device. Check the destination app to confirm posting.";
      } catch (error) {
        status.textContent = error.name === "AbortError" ? "Sharing cancelled." : "Device sharing is unavailable. Use Copy public link or a platform button.";
      }
    });
  }
}
'''
SHARE_CSS='''button.button{background:transparent;color:#edf4fa}button.button.primary{background:#72e3cd;color:#081923}button.button:hover{border-color:#70dfcb}button.button.primary:hover{background:#b0f6e7}[hidden]{display:none!important}button{font:inherit;cursor:pointer}.sharing{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:32px;margin:30px 0 60px;padding:32px;border:1px solid #293e50;border-radius:16px;background:#101e2e}.sharing h2{margin:10px 0}.sharing p{color:#c1cfdd}.share-actions{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0}.share-actions .button{min-height:44px;font-size:14px;padding:8px 12px}.sharing label{display:block;font-size:13px;color:#b5c6d7}.sharing input,.sharing textarea{display:block;width:100%;min-width:0;padding:12px;border:1px solid #435d6c;border-radius:8px;background:#080f1c;color:#edf4fa;font:14px/1.6 system-ui;overflow-wrap:anywhere}.sharing textarea{resize:vertical;margin:12px 0}.sharing input:focus-visible,.sharing textarea:focus-visible,.sharing button:focus-visible{outline:3px solid #70dfcb;outline-offset:3px}.sharing figure{margin:0;align-self:start}.sharing img{display:block;width:100%;height:auto;border-radius:12px;border:1px solid #293e50}.sharing figcaption{font-size:13px;margin-top:12px}.sharing details{padding-bottom:0}.sharing summary{font-size:17px}.share-status{min-height:24px}nav .share-nav{white-space:nowrap}@media(max-width:760px){.sharing{grid-template-columns:1fr;padding:20px;gap:24px}nav{flex-wrap:wrap;gap:16px}}'''

WORKFLOWS={
 'ncc':('NCC review', [('Project context','Building class, jurisdiction and review question'),('Relevant NCC references','Matched publications, provisions and source pages'),('Review with citations','Inspect evidence, gaps and applicability'),('Saved draft report','Retain findings with their source snapshot')], 'Publication · Clause · Page', 'Confirm the edition, jurisdiction and any missing reference coverage.'),
 'ifc':('IFC checks', [('IFC model','A model retained inside its authorised project'),('Local data checks','Inspect identifiers, units and selected properties'),('Element findings','Trace findings to the model element'),('Saved draft report','Keep findings, originals and inspection exports')], 'Identifiers · Units · Containment', 'Model data quality checks, not geometric clash detection or certification.'),
 'documents':('Documents', [('Project files','PDF, TXT, DOCX or XLSX evidence'),('Retained versions','Keep originals and recoverable revisions'),('Searchable passages','Retrieve evidence from the active project'),('Evidence-linked report','Save a snapshot of the evidence used')], 'Originals · Versions · Evidence', 'Searchability depends on extraction limits and text quality.')
}

def workflow_explorer():
    choices=''.join('<label><input type="radio" name="public-workflow" value="'+key+'"'+(' checked' if key=='ncc' else '')+'><span>'+e(value[0])+'</span></label>' for key,value in WORKFLOWS.items())
    panels=[]
    for key,(label,steps,output,limit) in WORKFLOWS.items():
        stages=''.join(f'<li><span class="flow-number" aria-hidden="true">{index:02}</span><div><strong>{e(title)}</strong><p>{e(detail)}</p></div></li>' for index,(title,detail) in enumerate(steps,1))
        panels.append(f'<div class="flow-panel" data-flow-panel="{key}" role="group" aria-label="{e(label)} workflow"><ol class="flow-stages">{stages}</ol><div class="flow-output"><span>What stays visible</span><strong>{e(output)}</strong></div><p class="flow-limit">{e(limit)}</p></div>')
    return '<div class="workflow-explorer"><div class="flow-heading"><span class="eyebrow">EVIDENCE → REVIEW</span><h2>See how it connects.</h2><p>Workflow illustration · no project data</p></div><fieldset class="flow-selector"><legend>Explore a workflow</legend><div class="flow-choices">'+choices+'</div>'+''.join(panels)+'</fieldset></div>'

FLOW_CSS='''
.comparison-scroll{max-width:100%;overflow-x:auto;border:1px solid #293e50;border-radius:12px}.comparison-scroll:focus-visible{outline:3px solid #70dfcb;outline-offset:3px}.comparison-scroll table{border-collapse:collapse;width:100%;min-width:640px;font-size:14px;text-align:left}.comparison-scroll caption{text-align:left;padding:14px;color:#b5c6d7}.comparison-scroll th,.comparison-scroll td{padding:14px;vertical-align:top;border-top:1px solid #293e50}.comparison-scroll thead{background:#101e2e}.guide-contents{display:block;padding:20px 24px;margin:0 0 24px;border:1px solid #293e50;border-radius:14px;background:#101e2e}.guide-contents ul{margin:8px 0 0;padding-left:20px}.guide-contents li{margin:5px 0;font-size:15px}article [id]{scroll-margin-top:24px}.official-references li{margin:8px 0}.hero-layout{display:grid;grid-template-columns:minmax(0,1.22fr) minmax(340px,1fr);gap:48px;align-items:center;position:relative;isolation:isolate;padding:60px 0 48px}
.hero-layout::before{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(ellipse at 85% 35%,#70dfcb0d,transparent 55%)}
.hero-layout .hero{max-width:none;padding:18px 0 24px;animation:public-enter .55s ease both}
.hero-layout h1{font-size:clamp(36px,4.1vw,54px)}.hero-layout .lead{font-size:19px}.hero-layout .note{max-width:390px}
.workflow-explorer{min-width:0;border:1px solid #304856;border-radius:22px;background:linear-gradient(145deg,#102331,#0d1725 75%);padding:26px;box-shadow:0 22px 70px #0003;animation:public-enter .65s .08s ease both}
.flow-heading h2{font-size:25px;margin:8px 0}.flow-heading>p{font-size:12px;color:#a9bdce;margin:0 0 18px}
.flow-selector{padding:0;margin:0;border:0;min-width:0}.flow-selector legend{font-size:12px;color:#b5c6d7;margin-bottom:8px}
.flow-choices{display:flex;gap:6px;margin-bottom:22px;flex-wrap:wrap}.flow-choices label{display:flex;align-items:center;justify-content:center;gap:6px;flex:1 1 88px;min-height:44px;border:1px solid #3b5364;border-radius:9px;background:#0a1523;color:#c6d5e1;cursor:pointer;font-size:12px;font-weight:650;transition:background .18s,border-color .18s}
.flow-choices label:has(input:checked){background:#72e3cd;color:#08232b;border-color:#72e3cd}.flow-choices label:has(input:focus-visible){outline:3px solid #fff;outline-offset:3px}.flow-choices input{margin:0;accent-color:#133c43;width:13px;height:13px;flex-shrink:0}
.flow-panel{display:block}.flow-selector:has(input:checked) .flow-panel{display:none}
.flow-selector:has(input[value="ncc"]:checked) [data-flow-panel="ncc"],.flow-selector:has(input[value="ifc"]:checked) [data-flow-panel="ifc"],.flow-selector:has(input[value="documents"]:checked) [data-flow-panel="documents"]{display:block}
.flow-stages{list-style:none;padding:0;margin:0}.flow-stages li{display:flex;gap:13px;position:relative;padding:0 0 20px;animation:public-enter .38s ease both}.flow-stages li:nth-child(2){animation-delay:.06s}.flow-stages li:nth-child(3){animation-delay:.12s}.flow-stages li:nth-child(4){animation-delay:.18s;padding-bottom:10px}
.flow-stages li:not(:last-child)::after{content:"";position:absolute;left:16px;top:36px;bottom:3px;width:1px;background:linear-gradient(#72e3cd80,#344b5c);transform-origin:top;animation:flow-connect .6s ease both}
.flow-number{display:grid;place-items:center;flex:0 0 34px;height:34px;border-radius:10px;border:1px solid #41665f;background:#173c3c;color:#9aead9;font-size:11px;font-weight:700}.flow-stages strong{display:block;font-size:14px;color:#edf4fa;line-height:1.45}.flow-stages p{font-size:12px;line-height:1.5;margin:4px 0 0;color:#b1c4d3}
.flow-output{padding:14px 16px;margin-top:8px;border:1px solid #33554f;border-radius:12px;background:#0e2a2d}.flow-output span{display:block;font-size:11px;color:#b8cbd2}.flow-output strong{display:block;font-size:13px;color:#9cead9;margin-top:3px}.flow-limit{font-size:11px;line-height:1.6;color:#b1c4d3;margin:12px 0 0}
.button{transition:transform .18s,background .18s,border-color .18s}.button:hover{transform:translateY(-2px)}.button:active{transform:translateY(0)}
@keyframes public-enter{from{opacity:.4;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@keyframes flow-connect{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@media(max-width:900px){.hero-layout{grid-template-columns:1fr;gap:12px;padding:38px 0 40px}.hero-layout .hero{max-width:760px;padding:0 0 22px}.hero-layout h1{font-size:clamp(36px,6.5vw,54px)}.workflow-explorer{max-width:680px;width:100%}.hero-layout .lead{font-size:19px}}
@media(max-width:480px){.workflow-explorer{padding:20px;border-radius:16px}.hero-layout{padding-top:32px}.hero-layout .lead{font-size:18px}.flow-heading h2{font-size:23px}.flow-choices{gap:5px}.flow-choices label{font-size:11px;flex-basis:85px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
'''

def render(slug):
    title,description,sections=PAGES[slug]
    graph=[{'@type':'Organization','@id':ORIGIN+'/#organization','name':'Gao Intelligence','alternateName':['GaoIntelligence','gaointelligence','gaointelligence.com'],'description':PAGES[''][2][0][1],'subjectOf':{'@id':url('about')+'#page'},'url':url(''),'logo':{'@type':'ImageObject','url':ORIGIN+'/seo-assets/brand-logo.png','width':512,'height':512}},
           {'@type':'WebSite','@id':ORIGIN+'/#website','name':'Gao Intelligence','alternateName':['GaoIntelligence','gaointelligence','gaointelligence.com','Gao Intelligence Construction AI'],'inLanguage':'en-AU','url':url(''),'publisher':{'@id':ORIGIN+'/#organization'}},
           {'@type':'WebPage','@id':url(slug)+'#page','url':url(slug),'name':SEO_TITLES[slug],'description':description,'inLanguage':'en-AU','dateModified':REVIEWED,'publisher':{'@id':ORIGIN+'/#organization'},'isPartOf':{'@id':ORIGIN+'/#website'},'breadcrumb':{'@id':url(slug)+'#breadcrumbs'}},
           {'@type':'BreadcrumbList','@id':url(slug)+'#breadcrumbs','itemListElement':[{'@type':'ListItem','position':1,'name':'Gao Intelligence','item':url('')}]+([{'@type':'ListItem','position':2,'name':title,'item':url(slug)}] if slug else [])}]
    if slug=='about':
        graph[2]['additionalType']='https://schema.org/AboutPage'
        graph[2]['mainEntity']={'@id':ORIGIN+'/#organization'}
    if not slug: graph.append({'@type':'SoftwareApplication','@id':ORIGIN+'/#application','name':'Gao Intelligence','alternateName':['GaoIntelligence','gaointelligence'],'url':ORIGIN+'/','applicationCategory':'BusinessApplication','operatingSystem':'Web browser','description':description,'publisher':{'@id':ORIGIN+'/#organization'}})
    if slug=='faq': graph.append({'@type':'FAQPage','@id':url(slug)+'#faq','url':url(slug),'isPartOf':{'@id':ORIGIN+'/#website'},'mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in FAQ]})
    body=answer_content(slug,sections)
    cards=''.join(f'<a class="card" href="/discover/{s}/"><span>{e(t)}</span><small>{e(d)}</small><b aria-hidden="true">↗</b></a>' for s,(t,d,_) in PAGES.items() if s and s!=slug)
    schema=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('<','\\u003c')
    hero=f'''<div class="hero"><p class="eyebrow">CONSTRUCTION INTELLIGENCE · AUSTRALIA</p><h1>{e(title)}</h1><p class="lead">{e(description)}</p><a class="button primary" href="/workspace/">Try the workspace ↗</a><p class="note">Guest examples available · Private projects require sign-in</p></div>'''
    if not slug:hero='<div class="hero-layout">'+hero+workflow_explorer()+'</div>'
    return f'''<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(SEO_TITLES[slug])}</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{url(slug)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">{social_metadata(slug)}<link rel="icon" href="/favicon.png" type="image/png" sizes="96x96"><link rel="shortcut icon" href="/favicon.ico"><link rel="apple-touch-icon" href="/seo-assets/apple-touch-icon.png" sizes="180x180"><link rel="stylesheet" href="/seo-assets/site-v5.css"><script type="application/ld+json">{schema}</script><script src="/seo-assets/share-v2.js" defer></script></head><body><a class="skip" href="#main">Skip to content</a><header><a class="brand" href="/"><img src="/seo-assets/logo.svg" width="36" height="36" alt="">Gao Intelligence</a><nav aria-label="Main navigation"><a class="share-nav" href="#share">Share</a><a href="/discover/faq/">FAQ</a><a class="button" href="/workspace/">Open workspace ↗</a></nav></header><main id="main">{hero}<article>{body}<p class="review">Product guide reviewed <time datetime="{REVIEWED}">3 November 2026</time> · Gao Intelligence</p></article>{share_panel(slug)}<aside aria-label="Explore product guides"><h2>Explore the workflow</h2><div class="cards">{cards}</div></aside></main><footer><a class="brand" href="/">Gao Intelligence</a><p>Construction evidence, connected.</p><a href="/discover/about/">About Gao Intelligence</a> · <a href="/discover/data-boundaries/">Data boundaries</a> · <a href="/mail-privacy">Account and Email Privacy</a> · <a href="/workspace/">Workspace</a><p class="note">Analysis supports professional review. It does not certify compliance.</p></footer></body></html>'''

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#080f1c;color:#edf4fa;font:17px/1.7 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:#70dfcb;text-underline-offset:.22em}a:hover{color:#fff}a:focus-visible,summary:focus-visible{outline:3px solid #70dfcb;outline-offset:5px}header,main,footer{width:min(1120px,calc(100% - 48px));margin:auto}header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:28px 0;border-bottom:1px solid #29384a}.brand{display:inline-flex;align-items:center;gap:12px;font-size:20px;font-weight:750;color:#fff;text-decoration:none}nav{display:flex;gap:24px;align-items:center}.button{display:inline-block;padding:10px 20px;border:1px solid #435d6c;border-radius:9px;text-decoration:none;font-weight:650;color:#fff}.primary{background:#72e3cd;color:#081923;border-color:#72e3cd}.primary:hover{background:#b0f6e7;color:#081923}.hero{padding:88px 0 60px;max-width:900px}.eyebrow{font-size:12px;letter-spacing:.17em;font-weight:700;color:#70dfcb}h1{font-size:clamp(36px,5.3vw,64px);line-height:1.1;letter-spacing:-.035em;margin:22px 0}h2{font-size:26px;line-height:1.3;letter-spacing:-.02em}.lead{font-size:21px;color:#b5c6d7;max-width:760px}.note,.review{font-size:13px;color:#b5c6d7}.hero .button{margin-top:18px}article{max-width:790px}section{padding:20px 0;border-top:1px solid #29384a}section p,details p{color:#c1cfdd}details{border-top:1px solid #29384a;padding:24px 0}summary{cursor:pointer;font-size:21px;font-weight:650}details[open] summary{color:#70dfcb}.review{padding:25px 0}aside{margin:40px 0 80px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.card{display:block;position:relative;background:#101e2e;border:1px solid #293e50;border-radius:14px;padding:25px 48px 25px 25px;text-decoration:none;transition:transform .15s,border-color .15s}.card:hover{transform:translateY(-3px);border-color:#70dfcb}.card span{display:block;font-size:20px;font-weight:650}.card small{display:block;color:#b5c6d7;margin-top:10px;font-size:14px}.card b{position:absolute;top:24px;right:22px}footer{padding:35px 0 50px;border-top:1px solid #29384a;color:#b5c6d7;font-size:14px}.skip{position:absolute;top:-100px;left:15px;background:#fff;color:#081923;padding:12px;z-index:10}.skip:focus{top:10px}@media(max-width:600px){header,main,footer{width:calc(100% - 32px)}header{align-items:flex-start;flex-direction:column;padding:20px 0}nav{width:100%;justify-content:space-between}.hero{padding:45px 0 35px}.lead{font-size:18px}.cards{grid-template-columns:1fr}.button{padding:9px 16px}h2{font-size:23px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.card{transition:none}}'''
LOGO='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#72e3cd"/><path d="M33 17a12 12 0 1 0 1 13v-7H23v5h6a7 7 0 1 1-1-8z" fill="#081923"/></svg>'

def build_social_images(assets):
    from PIL import Image,ImageDraw,ImageFont
    def font(size):
        try:return ImageFont.truetype('DejaVuSans.ttf',size)
        except OSError:return ImageFont.load_default(size=size)
    for slug in PAGES:
        for square in ((False,True) if not slug else (False,)):
            width,height=(1080,1080) if square else (1200,630)
            image=Image.new('RGB',(width,height),'#080f1c');draw=ImageDraw.Draw(image)
            # Decorative construction grid, with no screenshots or project evidence.
            for x in range(width-340,width,52):draw.line((x,0,x,height),fill='#112437',width=1)
            for y in range(0,height,52):draw.line((width-340,y,width,y),fill='#112437',width=1)
            margin=72 if square else 64
            draw.rounded_rectangle((margin,margin,margin+64,margin+64),radius=16,fill='#72e3cd')
            draw.text((margin+15,margin+6),'G',font=font(40),fill='#081923')
            draw.text((margin+86,margin+12),'Gao Intelligence',font=font(36),fill='#edf4fa')
            draw.text((margin,250 if square else 175),'CONSTRUCTION INTELLIGENCE',font=font(22 if square else 18),fill='#72e3cd')
            lines=SOCIAL_CARDS[slug]
            size=78 if square else 64
            while max(draw.textbbox((0,0),line,font=font(size))[2] for line in lines)>width-2*margin:size-=2
            y=330 if square else 230
            for index,line in enumerate(lines):
                draw.text((margin,y),line,font=font(size),fill='#72e3cd' if index==len(lines)-1 else '#edf4fa')
                y+=size+12
            bottom=height-135
            draw.line((margin,bottom-25,width-margin,bottom-25),fill='#293e50',width=2)
            draw.text((margin,bottom),'NCC references / IFC checks / Project reports' if not slug else 'Project evidence for professional review',font=font(25 if square else 23),fill='#b5c6d7')
            draw.text((margin,height-76),'gaointelligence.com',font=font(26 if square else 23),fill='#72e3cd')
            filename='share-v2-home-square.png' if square else Path(social_image(slug)).name
            image.save(assets/filename,optimize=True)
            if not slug and not square:image.save(assets/'og-image.png',optimize=True)

def build_brand_icons(root,assets):
    # Rasterise the existing geometric G mark; no font or external service needed.
    from PIL import Image,ImageDraw
    image=Image.new('RGB',(512,512),'#72e3cd');draw=ImageDraw.Draw(image)
    scale=512/48
    box=tuple(round(v*scale) for v in (12,12,36,36))
    draw.arc(box,start=42,end=318,fill='#081923',width=round(5*scale))
    draw.rectangle(tuple(round(v*scale) for v in (24,22,36,27)),fill='#081923')
    draw.rectangle(tuple(round(v*scale) for v in (31,22,36,31)),fill='#081923')
    image.save(assets/'brand-logo.png',optimize=True)
    image.resize((96,96),Image.Resampling.LANCZOS).save(root/'favicon.png',optimize=True)
    image.save(root/'favicon.ico',sizes=[(16,16),(32,32),(48,48),(64,64)])
    image.resize((180,180),Image.Resampling.LANCZOS).save(assets/'apple-touch-icon.png',optimize=True)


def build(destination):
    root=Path(destination)
    for slug in PAGES:
        path=root/'discover'/slug/'index.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(render(slug),encoding='utf-8')
    (root/'index.html').write_text(render(''),encoding='utf-8')
    assets=root/'seo-assets';assets.mkdir(parents=True,exist_ok=True)
    (assets/'site.css').write_text(CSS+SHARE_CSS+FLOW_CSS,encoding='utf-8');(assets/'site-v2.css').write_text(CSS+SHARE_CSS+FLOW_CSS,encoding='utf-8');(assets/'site-v3.css').write_text(CSS+SHARE_CSS+FLOW_CSS,encoding='utf-8');(assets/'site-v4.css').write_text(CSS+SHARE_CSS+FLOW_CSS,encoding='utf-8');(assets/'site-v5.css').write_text(CSS+SHARE_CSS+FLOW_CSS,encoding='utf-8');(assets/'share-v2.js').write_text(SHARE_JS,encoding='utf-8');(assets/'logo.svg').write_text(LOGO,encoding='utf-8')
    build_social_images(assets)
    build_brand_icons(root,assets)
    blocked=['/workspace/','/private-download/','/_stcore/','/component/','/static/','/media/','/api/','/projects/','/reports/']
    (root/'robots.txt').write_text('User-agent: *\n'+''.join('Disallow: '+p+'\n' for p in blocked)+'Sitemap: '+ORIGIN+'/sitemap.xml\n')
    (root/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{url(s)}</loc><lastmod>{REVIEWED}</lastmod></url>' for s in PAGES)+'</urlset>')
    return root

if __name__=='__main__':build(sys.argv[1])
