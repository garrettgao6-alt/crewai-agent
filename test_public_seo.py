import json
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
import public_site as site
from deploy import install_public_seo as installer

class Document(HTMLParser):
    def __init__(self,text):
        super().__init__();self.tags=[];self.schemas=[];self.in_schema=False;self.feed(text)
    def handle_starttag(self,tag,attrs):
        data=dict(attrs);self.tags.append((tag,data))
        if tag=='script' and data.get('type')=='application/ld+json':self.in_schema=True
    def handle_endtag(self,tag):
        if tag=='script':self.in_schema=False
    def handle_data(self,data):
        if self.in_schema:self.schemas.append(json.loads(data))

class PublicSiteTests(unittest.TestCase):
    def test_public_pages_have_consistent_metadata_and_existing_local_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=site.build(tmp)
            titles=[]
            for slug in site.PAGES:
                doc=Document((root/'discover'/slug/'index.html').read_text())
                self.assertEqual(sum(t=='h1' for t,_ in doc.tags),1)
                canonical=[a['href'] for t,a in doc.tags if t=='link' and a.get('rel')=='canonical']
                self.assertEqual(canonical,[site.url(slug)])
                self.assertTrue(any(t=='meta' and a.get('name')=='description' and a.get('content') for t,a in doc.tags))
                self.assertEqual(len(doc.schemas),1)
                graph=doc.schemas[0]['@graph']
                self.assertTrue(any(v['@type']=='WebPage' and v['url']==canonical[0] for v in graph))
                for tag,a in doc.tags:
                    target=a.get('href') or a.get('src')
                    if target and target.startswith('/') and target not in ('/','/workspace/','/mail-privacy') and not target.startswith('#'):
                        file=root/target.lstrip('/')
                        self.assertTrue(file.exists(),target)
                if slug=='faq':
                    faq=next(v for v in graph if v['@type']=='FAQPage')
                    self.assertEqual(len(faq['mainEntity']),len(site.FAQ))
                    for q in faq['mainEntity']:self.assertIn(q['name'],(root/'discover/faq/index.html').read_text())
            urls=ET.parse(root/'sitemap.xml').findall('{*}url/{*}loc')
            self.assertEqual({u.text for u in urls},{site.url(s) for s in site.PAGES})
            home=(root/'index.html').read_text()
            self.assertEqual(home,(root/'discover/index.html').read_text())
            self.assertIn('<link rel="canonical" href="'+site.ORIGIN+'/">',home)
            self.assertIn('href="/workspace/">Open workspace',home)
            self.assertIn('href="/workspace/">Try the workspace',home)
            self.assertNotIn('<div id="root"></div>',home)
            robots=(root/'robots.txt').read_text()
            self.assertIn('Disallow: /workspace/',robots)
            self.assertIn('Disallow: /private-download/',robots)
            self.assertNotIn('Disallow: /\n',robots)
            self.assertNotIn(site.ORIGIN+'/<',robots)
            self.assertEqual(set(p.name for p in root.iterdir()),{'index.html','discover','seo-assets','robots.txt','sitemap.xml'})
    def test_nginx_change_preserves_existing_proxy_and_rejects_ambiguous_config(self):
        original='server {\n    location ^~ /private-download/ { proxy_pass http://127.0.0.1:8000; }\n    location / { proxy_pass http://127.0.0.1:8501; }\n}'
        changed=installer.site_config(original)
        self.assertIn('proxy_pass http://127.0.0.1:8000;',changed)
        self.assertEqual(installer.site_config(changed),changed)
        self.assertIn('location ^~ /workspace/ {',changed)
        self.assertNotIn('    location / {',changed)
        self.assertIn('location = / {',installer.SNIPPET_TEXT)
        self.assertIn('try_files /index.html =404;',installer.SNIPPET_TEXT)
        self.assertIn('/index.html "";',installer.MAP_TEXT)  # Resolved static root must stay indexable.
        self.assertIn('location / { return 404; }',installer.SNIPPET_TEXT)
        self.assertIn('http://127.0.0.1:8501/workspace/_stcore/health',installer.SNIPPET_TEXT)
        self.assertIn('location = /workspace { return 308 /workspace/$is_args$args; }',installer.SNIPPET_TEXT)
        proof='    location = /googled326aae452cb5530.html { root /var/www/gao-ownership; }\n'
        self.assertIn(proof,installer.site_config(original.replace('    location / {',proof+'    location / {')))
        self.assertIn('add_header X-Robots-Tag $gao_search_robots always;',changed)
        for unsafe in ('server {}',original+original):
            with self.assertRaises(ValueError):installer.site_config(unsafe)
        self.assertIn('default "noindex, nofollow, noarchive";',installer.MAP_TEXT)
        self.assertNotIn('add_header',installer.SNIPPET_TEXT)
    def test_reload_readiness_retries_old_worker_responses_and_still_fails_closed(self):
        from unittest.mock import MagicMock
        def response(body):
            obj=MagicMock();obj.__enter__.return_value=obj;obj.status=200;obj.headers={};obj.read.return_value=body
            return obj
        with patch.object(installer.urllib.request,'urlopen',side_effect=[response(b'old Streamlit shell'),response(b'Construction AI'),response(b'User-agent: *'),response(b'<urlset'),response(b'<div id="root"></div>')]),patch.object(installer.time,'sleep') as sleep:
            installer.verify_public_ready()
            sleep.assert_called_once()
        with patch.object(installer.urllib.request,'urlopen',return_value=response(b'old Streamlit shell')):
            with self.assertRaisesRegex(RuntimeError,'/'):
                installer.verify_public_ready(timeout=0)

    def test_failed_reload_restores_previous_config_and_public_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);public=base/'public';public.mkdir();previous=public/'previous';previous.mkdir();(public/'current').symlink_to(previous)
            config=base/'site';config.write_text('server {\n    location / { proxy_pass http://127.0.0.1:8501; }\n}')
            map_file=base/'map';snippet=base/'snippet';backup=base/'backup';backup.mkdir()
            original=config.read_bytes()
            with patch.multiple(installer,SITE=config,MAP=map_file,SNIPPET=snippet,HOME_SOCIAL=base/'home-social',PUBLIC=public),patch.object(installer,'reload_nginx',side_effect=[RuntimeError('configuration check failed'),None]) as reload:
                with self.assertRaises(RuntimeError):installer.install(backup)
                self.assertEqual(config.read_bytes(),original)
                self.assertFalse(map_file.exists());self.assertFalse(snippet.exists())
                self.assertEqual((public/'current').resolve(),previous.resolve())
                self.assertEqual(reload.call_count,2)
                self.assertTrue((backup/'public-seo-state/restore.py').exists())


class SocialSharingTests(unittest.TestCase):
    def test_share_links_and_metadata_only_contain_canonical_public_urls(self):
        from urllib.parse import urlparse,parse_qs
        images=set()
        for slug in site.PAGES:
            doc=Document(site.render(slug))
            metadata={a.get('property') or a.get('name'):a.get('content') for tag,a in doc.tags if tag=='meta'}
            self.assertEqual(metadata['og:url'],site.url(slug))
            self.assertEqual(metadata['og:image'],metadata['twitter:image'])
            self.assertEqual(metadata['og:image:width'],'1200')
            self.assertTrue(metadata['twitter:title']);self.assertTrue(metadata['twitter:description'])
            images.add(metadata['og:image'])
            panels=[a for tag,a in doc.tags if 'data-public-url' in a]
            self.assertEqual([a['data-public-url'] for a in panels],[site.url(slug)])
            for tag,a in doc.tags:
                if tag!='a' or not a.get('aria-label','').startswith('Share this public guide via'):continue
                query=parse_qs(urlparse(a['href']).query)
                if a['href'].startswith('mailto:'):
                    self.assertNotIn('+',a['href'])
                    self.assertIn('%20',a['href'])
                self.assertIn(site.url(slug),str(query))
                self.assertNotIn('project_id',a['href']);self.assertNotIn('session',a['href'])
                self.assertIn('noopener',a['rel'])
            self.assertIn('value="'+site.url(slug)+'"',site.share_panel(slug))
        self.assertEqual(len(images),len(site.PAGES))
        self.assertNotIn('location',site.SHARE_JS)
        self.assertNotIn('fetch(',site.SHARE_JS)
        self.assertNotIn('localStorage',site.SHARE_JS)
        self.assertIn('await navigator.clipboard.writeText',site.SHARE_JS)
        self.assertIn('copy it manually',site.SHARE_JS)
    def test_generated_social_images_and_homepage_preview_are_public_only(self):
        from PIL import Image
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=site.build(tmp);hashes=set()
            for slug in site.PAGES:
                path=root/site.social_image(slug).lstrip('/')
                with Image.open(path) as image:self.assertEqual(image.size,(1200,630))
                hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertLess(path.stat().st_size,1000000)
            self.assertEqual(len(hashes),len(site.PAGES))
            with Image.open(root/'seo-assets/share-v2-home-square.png') as image:self.assertEqual(image.size,(1080,1080))
        config=installer.home_social_config()
        self.assertIn('sub_filter_once on;',config)
        # Apply the literal Nginx rules to the upstream shell and inspect the resulting document.
        import re
        shell='<html><head><title>Streamlit</title><link rel="shortcut icon" href="./favicon.png" /></head><body><noscript>You need to enable JavaScript to run this app.</noscript><div id="root"></div><script type="module" src="./static/app.js"></script></body></html>'
        for before,after in re.findall(r"sub_filter '([^']*)' '([^']*)';",config):
            shell=shell.replace(before,after,1)
        self.assertIn('<title>Gao Intelligence | Construction AI workspace</title>',shell)
        self.assertIn('<noscript><h1>Gao Intelligence</h1>',shell)
        self.assertNotIn('You need to enable JavaScript to run this app.',shell)
        self.assertNotIn('./favicon.png',shell)
        self.assertIn('<div id="root"></div>',shell)
        self.assertIn('<script type="module" src="./static/app.js"></script>',shell)
        doc=Document(shell)
        self.assertTrue(any(t=='link' and a.get('rel')=='icon' and a.get('href')=='/seo-assets/logo.svg' for t,a in doc.tags))
        self.assertTrue(any(t=='a' and a.get('href')=='/discover/' for t,a in doc.tags))
        self.assertIn('proxy_set_header Accept-Encoding $gao_share_upstream_encoding;',config)
        self.assertNotIn('proxy_set_header Accept-Encoding "";',config)
        self.assertIn('default $http_accept_encoding;',installer.MAP_TEXT)
        self.assertIn('/workspace/ "";',installer.MAP_TEXT)
        self.assertIn(site.ORIGIN+'/',config)
        self.assertNotIn('$request_uri',config)
        self.assertNotIn('$cookie',config)
        self.assertNotIn('private-download',config)
        old='server {\n'+installer.MARKER+'    add_header X-Robots-Tag $gao_search_robots always;\n    include /etc/nginx/snippets/gao-public-seo.conf;\n    location / { proxy_pass http://127.0.0.1:8501; }\n}'
        upgraded=installer.site_config(old)
        self.assertIn('include /etc/nginx/snippets/gao-home-social.conf;',upgraded)
        self.assertEqual(installer.site_config(upgraded),upgraded)

if __name__=='__main__':unittest.main()
