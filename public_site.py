"""Deterministic public product pages. Never imports application stores or secrets."""
from html import escape as e
import json
from pathlib import Path
import sys

ORIGIN='https://www.gaointelligence.com'
REVIEWED='2026-11-02'
PAGES={
'':('Construction AI, NCC references and IFC checks','Gao Intelligence helps Australian construction teams review project evidence, retrieve NCC references, check IFC models and save reports.',[
('What is Gao Intelligence?','Gao Intelligence is a construction analysis workspace for NCC reference retrieval, document management, IFC model quality checks and saved reports. It helps teams organise evidence and draft reviews for professional assessment.'),
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
PAGES['faq']=('Gao Intelligence FAQ: NCC, BIM, documents and privacy','Answers about guest AI, NCC reference retrieval, IFC checks, document versions, saved reports and private project boundaries.',FAQ)

def url(slug): return ORIGIN+'/discover/'+(slug+'/' if slug else '')
def render(slug):
    title,description,sections=PAGES[slug]
    graph=[{'@type':'Organization','@id':ORIGIN+'/#organization','name':'Gao Intelligence','url':url(''),'logo':ORIGIN+'/seo-assets/logo.svg'},
           {'@type':'WebSite','@id':ORIGIN+'/#website','name':'Gao Intelligence','url':url(''),'publisher':{'@id':ORIGIN+'/#organization'}},
           {'@type':'WebPage','@id':url(slug)+'#page','url':url(slug),'name':title,'description':description,'inLanguage':'en-AU','dateModified':REVIEWED,'isPartOf':{'@id':ORIGIN+'/#website'}},
           {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Gao Intelligence','item':url('')}]+([{'@type':'ListItem','position':2,'name':title,'item':url(slug)}] if slug else [])}]
    if not slug: graph.append({'@type':'SoftwareApplication','name':'Gao Intelligence','url':ORIGIN+'/','applicationCategory':'BusinessApplication','operatingSystem':'Web browser','description':description})
    if slug=='faq': graph.append({'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in FAQ]})
    body=''.join((f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' if slug=='faq' else f'<section><h2>{e(q)}</h2><p>{e(a)}</p></section>') for q,a in sections)
    cards=''.join(f'<a class="card" href="/discover/{s}/"><span>{e(t)}</span><small>{e(d)}</small><b aria-hidden="true">↗</b></a>' for s,(t,d,_) in PAGES.items() if s and s!=slug)
    schema=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('<','\\u003c')
    return f'''<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | Gao Intelligence</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{url(slug)}"><meta name="robots" content="index,follow"><meta property="og:type" content="website"><meta property="og:site_name" content="Gao Intelligence"><meta property="og:locale" content="en_AU"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{url(slug)}"><meta property="og:image" content="{ORIGIN}/seo-assets/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Gao Intelligence: construction evidence, connected"><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="/seo-assets/logo.svg" type="image/svg+xml"><link rel="stylesheet" href="/seo-assets/site.css"><script type="application/ld+json">{schema}</script></head><body><a class="skip" href="#main">Skip to content</a><header><a class="brand" href="/discover/"><img src="/seo-assets/logo.svg" width="36" height="36" alt="">Gao Intelligence</a><nav aria-label="Main navigation"><a href="/discover/faq/">FAQ</a><a class="button" href="/">Open workspace ↗</a></nav></header><main id="main"><div class="hero"><p class="eyebrow">CONSTRUCTION INTELLIGENCE · AUSTRALIA</p><h1>{e(title)}</h1><p class="lead">{e(description)}</p><a class="button primary" href="/">Try the workspace ↗</a><p class="note">Guest examples available · Private projects require sign-in</p></div><article>{body}<p class="review">Product guide reviewed <time datetime="{REVIEWED}">2 November 2026</time> · Gao Intelligence</p></article><aside aria-label="Explore product guides"><h2>Explore the workflow</h2><div class="cards">{cards}</div></aside></main><footer><a class="brand" href="/discover/">Gao Intelligence</a><p>Construction evidence, connected.</p><a href="/discover/data-boundaries/">Data boundaries</a> · <a href="/mail-privacy">Account and Email Privacy</a> · <a href="/">Workspace</a><p class="note">Analysis supports professional review. It does not certify compliance.</p></footer></body></html>'''

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#080f1c;color:#edf4fa;font:17px/1.7 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:#70dfcb;text-underline-offset:.22em}a:hover{color:#fff}a:focus-visible,summary:focus-visible{outline:3px solid #70dfcb;outline-offset:5px}header,main,footer{width:min(1120px,calc(100% - 48px));margin:auto}header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:28px 0;border-bottom:1px solid #29384a}.brand{display:inline-flex;align-items:center;gap:12px;font-size:20px;font-weight:750;color:#fff;text-decoration:none}nav{display:flex;gap:24px;align-items:center}.button{display:inline-block;padding:10px 20px;border:1px solid #435d6c;border-radius:9px;text-decoration:none;font-weight:650;color:#fff}.primary{background:#72e3cd;color:#081923;border-color:#72e3cd}.primary:hover{background:#b0f6e7;color:#081923}.hero{padding:88px 0 60px;max-width:900px}.eyebrow{font-size:12px;letter-spacing:.17em;font-weight:700;color:#70dfcb}h1{font-size:clamp(36px,5.3vw,64px);line-height:1.1;letter-spacing:-.035em;margin:22px 0}h2{font-size:26px;line-height:1.3;letter-spacing:-.02em}.lead{font-size:21px;color:#b5c6d7;max-width:760px}.note,.review{font-size:13px;color:#b5c6d7}.hero .button{margin-top:18px}article{max-width:790px}section{padding:20px 0;border-top:1px solid #29384a}section p,details p{color:#c1cfdd}details{border-top:1px solid #29384a;padding:24px 0}summary{cursor:pointer;font-size:21px;font-weight:650}details[open] summary{color:#70dfcb}.review{padding:25px 0}aside{margin:40px 0 80px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.card{display:block;position:relative;background:#101e2e;border:1px solid #293e50;border-radius:14px;padding:25px 48px 25px 25px;text-decoration:none;transition:transform .15s,border-color .15s}.card:hover{transform:translateY(-3px);border-color:#70dfcb}.card span{display:block;font-size:20px;font-weight:650}.card small{display:block;color:#b5c6d7;margin-top:10px;font-size:14px}.card b{position:absolute;top:24px;right:22px}footer{padding:35px 0 50px;border-top:1px solid #29384a;color:#b5c6d7;font-size:14px}.skip{position:absolute;top:-100px;left:15px;background:#fff;color:#081923;padding:12px;z-index:10}.skip:focus{top:10px}@media(max-width:600px){header,main,footer{width:calc(100% - 32px)}header{align-items:flex-start;flex-direction:column;padding:20px 0}nav{width:100%;justify-content:space-between}.hero{padding:45px 0 35px}.lead{font-size:18px}.cards{grid-template-columns:1fr}.button{padding:9px 16px}h2{font-size:23px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.card{transition:none}}'''
LOGO='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#72e3cd"/><path d="M33 17a12 12 0 1 0 1 13v-7H23v5h6a7 7 0 1 1-1-8z" fill="#081923"/></svg>'

def build(destination):
    root=Path(destination)
    for slug in PAGES:
        path=root/'discover'/slug/'index.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(render(slug),encoding='utf-8')
    assets=root/'seo-assets';assets.mkdir(parents=True,exist_ok=True)
    (assets/'site.css').write_text(CSS,encoding='utf-8');(assets/'logo.svg').write_text(LOGO,encoding='utf-8')
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(1200,630),'#080f1c');draw=ImageDraw.Draw(image)
    def font(size):
        try:return ImageFont.truetype('DejaVuSans.ttf',size)
        except OSError:return ImageFont.load_default(size=size)
    draw.rounded_rectangle((64,64,138,138),radius=18,fill='#72e3cd');draw.text((83,72),'G',font=font(44),fill='#081923')
    draw.text((165,80),'Gao Intelligence',font=font(40),fill='#edf4fa')
    draw.text((64,235),'Construction evidence,',font=font(64),fill='#edf4fa');draw.text((64,315),'connected.',font=font(64),fill='#72e3cd')
    draw.text((64,505),'NCC references  /  IFC checks  /  Project reports',font=font(28),fill='#b5c6d7')
    image.save(assets/'og-image.png')
    blocked=['/private-download/','/_stcore/','/component/','/static/','/media/','/api/','/projects/','/reports/']
    (root/'robots.txt').write_text('User-agent: *\n'+''.join('Disallow: '+p+'\n' for p in blocked)+'Sitemap: '+ORIGIN+'/sitemap.xml\n')
    (root/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{url(s)}</loc><lastmod>{REVIEWED}</lastmod></url>' for s in PAGES)+'</urlset>')
    return root

if __name__=='__main__':build(sys.argv[1])
