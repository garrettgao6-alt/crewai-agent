"""Deterministic public product pages. Never imports application stores or secrets."""
from html import escape as e
import json
from pathlib import Path
import sys
from urllib.parse import urlencode, quote

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

def url(slug): return ORIGIN+('/discover/'+slug+'/' if slug else '/')
SOCIAL_CARDS={
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
            'og:title':title+' | Gao Intelligence','og:description':description,'og:url':url(slug),
            'og:image':ORIGIN+social_image(slug),'og:image:secure_url':ORIGIN+social_image(slug),
            'og:image:type':'image/png','og:image:width':'1200','og:image:height':'630',
            'og:image:alt':'Gao Intelligence: '+' '.join(SOCIAL_CARDS[slug]),
            'twitter:card':'summary_large_image','twitter:title':title+' | Gao Intelligence',
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
    return f'''<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | Gao Intelligence</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{url(slug)}"><meta name="robots" content="index,follow">{social_metadata(slug)}<link rel="icon" href="/seo-assets/logo.svg" type="image/svg+xml"><link rel="stylesheet" href="/seo-assets/site-v2.css"><script type="application/ld+json">{schema}</script><script src="/seo-assets/share-v2.js" defer></script></head><body><a class="skip" href="#main">Skip to content</a><header><a class="brand" href="/"><img src="/seo-assets/logo.svg" width="36" height="36" alt="">Gao Intelligence</a><nav aria-label="Main navigation"><a class="share-nav" href="#share">Share</a><a href="/discover/faq/">FAQ</a><a class="button" href="/workspace/">Open workspace ↗</a></nav></header><main id="main"><div class="hero"><p class="eyebrow">CONSTRUCTION INTELLIGENCE · AUSTRALIA</p><h1>{e(title)}</h1><p class="lead">{e(description)}</p><a class="button primary" href="/workspace/">Try the workspace ↗</a><p class="note">Guest examples available · Private projects require sign-in</p></div><article>{body}<p class="review">Product guide reviewed <time datetime="{REVIEWED}">2 November 2026</time> · Gao Intelligence</p></article>{share_panel(slug)}<aside aria-label="Explore product guides"><h2>Explore the workflow</h2><div class="cards">{cards}</div></aside></main><footer><a class="brand" href="/">Gao Intelligence</a><p>Construction evidence, connected.</p><a href="/discover/data-boundaries/">Data boundaries</a> · <a href="/mail-privacy">Account and Email Privacy</a> · <a href="/workspace/">Workspace</a><p class="note">Analysis supports professional review. It does not certify compliance.</p></footer></body></html>'''

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

def build(destination):
    root=Path(destination)
    for slug in PAGES:
        path=root/'discover'/slug/'index.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(render(slug),encoding='utf-8')
    (root/'index.html').write_text(render(''),encoding='utf-8')
    assets=root/'seo-assets';assets.mkdir(parents=True,exist_ok=True)
    (assets/'site.css').write_text(CSS+SHARE_CSS,encoding='utf-8');(assets/'site-v2.css').write_text(CSS+SHARE_CSS,encoding='utf-8');(assets/'share-v2.js').write_text(SHARE_JS,encoding='utf-8');(assets/'logo.svg').write_text(LOGO,encoding='utf-8')
    build_social_images(assets)
    blocked=['/workspace/','/private-download/','/_stcore/','/component/','/static/','/media/','/api/','/projects/','/reports/']
    (root/'robots.txt').write_text('User-agent: *\n'+''.join('Disallow: '+p+'\n' for p in blocked)+'Sitemap: '+ORIGIN+'/sitemap.xml\n')
    (root/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{url(s)}</loc><lastmod>{REVIEWED}</lastmod></url>' for s in PAGES)+'</urlset>')
    return root

if __name__=='__main__':build(sys.argv[1])
