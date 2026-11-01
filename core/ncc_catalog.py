"""Private, edition-aware PDF catalog. Indexing/retrieval makes no AI calls."""
from contextlib import closing
import hashlib
import gc
import os
from pathlib import Path
import re
import shutil
import sqlite3
from uuid import uuid4

from core.document_pipeline import chunk_text

STATES = {'Australian Capital Territory':'ACT', 'New South Wales':'NSW', 'Northern Territory':'NT', 'Queensland':'QLD', 'South Australia':'SA', 'Tasmania':'TAS', 'Victoria':'VIC', 'Western Australia':'WA'}

MAX_OWNER_BYTES = 600 * 1024 * 1024

KINDS = {'Volume One': 'one', 'Volume Two': 'two', 'Housing Provisions': 'housing'}


class NCCContextRequired(ValueError):
    pass


def owner_folder(user_id):
    value = str(user_id)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('Invalid library owner')
    return 'u_' + value


def check_owner(root, path, user_id):
    parts = path.resolve().relative_to(root.resolve()).parts
    if parts and parts[0] == 'private' and (user_id is None or len(parts) < 2 or parts[1] != owner_folder(user_id)):
        raise PermissionError('This private NCC library belongs to another account.')


def create_catalog(directory, records, user_id):
    """Index existing PDF records [(filename, edition year, kind)] without embeddings."""
    from PyPDF2 import PdfReader
    directory = Path(directory)
    index = directory / '.ncc-index.sqlite3'
    with closing(sqlite3.connect(index)) as connection:
        connection.executescript('''
            CREATE TABLE owner (id TEXT NOT NULL);
            CREATE TABLE files(name TEXT PRIMARY KEY,year TEXT,kind TEXT,pages INTEGER,bytes INTEGER,mtime INTEGER,sha TEXT);
            CREATE VIRTUAL TABLE chunks USING fts5(text, name UNINDEXED, year UNINDEXED, kind UNINDEXED, page UNINDEXED, clause UNINDEXED, sha UNINDEXED, jurisdiction UNINDEXED, outline UNINDEXED, tokenize='porter unicode61');
        ''')
        connection.execute('CREATE TABLE pages(name TEXT,page INTEGER,text TEXT,jurisdiction TEXT,outline INTEGER,PRIMARY KEY(name,page))')
        connection.execute('CREATE TABLE clauses(name TEXT,year TEXT,kind TEXT,clause TEXT,page_start INTEGER,page_end INTEGER,text TEXT,jurisdiction TEXT,sha TEXT)')
        connection.execute('CREATE INDEX clause_lookup ON clauses(name,clause,jurisdiction)')
        connection.execute('INSERT INTO owner VALUES(?)', (str(user_id),))
        count = 0
        for name, year, kind in records:
            if year not in ('2022', '2025') or kind not in KINDS:
                raise ValueError('Choose the edition and volume for every PDF.')
            file = directory / name
            reader = PdfReader(file)
            if reader.is_encrypted:
                raise ValueError(f'{name}: encrypted PDFs are not supported.')
            if len(reader.pages) > 5000:
                raise ValueError(f'{name}: PDF exceeds 5,000 pages.')
            first = reader.pages[0].extract_text() or ''
            if year not in first or re.sub(r'\s+', '', kind.lower()) not in re.sub(r'\s+', '', first.lower()):
                raise ValueError(f'{name}: the selected edition/volume does not match the PDF cover.')
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            chunks_for_file = 0
            for page_number, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ''
                header = next((line.strip() for line in page_text.splitlines() if line.strip()), '')
                jurisdiction = next((code for name, code in STATES.items() if header.casefold() == name.casefold()), '')
                outline = int(_is_outline(page_text))
                connection.execute('INSERT INTO pages VALUES(?,?,?,?,?)', (name,page_number,page_text,jurisdiction,outline))
                for text in chunk_text(page_text):
                    if not text.strip():
                        continue
                    clause = re.search(r'\b(?:[A-Z]{1,3}\d+[A-Z]\d+(?:\.\d+)*|[A-Z]\d+\.\d+|\d+\.\d+\.\d+)\b', text)
                    connection.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)',
                        (text, name, year, KINDS[kind], page_number, clause.group() if clause else '', sha, jurisdiction, outline))
                    chunks_for_file += 1
            if not chunks_for_file:
                raise ValueError(f'{name}: no extractable text; OCR is required.')
            _store_sections(connection, name, year, KINDS[kind], sha, reader)
            stat = file.stat()
            connection.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?)',
                (name, year, KINDS[kind], len(reader.pages), stat.st_size, stat.st_mtime_ns, sha))
            count += chunks_for_file
            del reader
            gc.collect()
        connection.commit()
    os.chmod(index, 0o600)
    return count


def import_pdfs(user_id, uploads):
    from core import ncc_library as library
    if not uploads or len(uploads) > 10:
        raise ValueError('Select between 1 and 10 NCC PDFs.')
    names = [name for name, _, _, _ in uploads]
    if len(set(names)) != len(names):
        raise ValueError('PDF filenames must be unique.')
    if sum(len(data) for _, data, _, _ in uploads) > 200 * 1024 * 1024:
        raise ValueError('Upload at most 200 MB of references at a time.')
    for name, data, _, _ in uploads:
        if Path(name).name != name or Path(name).suffix.lower() != '.pdf' or not data.startswith(b'%PDF-'):
            raise ValueError('Only valid PDF filenames and PDF contents are accepted.')
        if len(data) > library.MAX_FILE_BYTES:
            raise ValueError('Each NCC PDF must be at most 75 MB.')
    parent = library.library_root() / 'private' / owner_folder(user_id)
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    check_owner(library.library_root(), parent, user_id)
    os.chmod(parent, 0o700)
    existing_bytes = sum(file.stat().st_size for file in parent.rglob("*") if file.is_file())
    if existing_bytes + sum(len(data) for _, data, _, _ in uploads) > MAX_OWNER_BYTES:
        raise ValueError("Private NCC library quota reached. Archive older collections before importing more files.")
    directory = parent / ('collection_' + uuid4().hex)
    directory.mkdir(mode=0o700)
    try:
        for name, data, _, _ in uploads:
            file = directory / name
            file.write_bytes(data)
            os.chmod(file, 0o600)
        count = create_catalog(directory, [(name, year, kind) for name, _, year, kind in uploads], user_id)
        library.save_reference(user_id, str(directory), 'Per-document NCC editions and volumes')
        return {'files': len(uploads), 'chunks': count, 'path': str(directory)}
    except Exception:
        shutil.rmtree(directory)
        raise


def select_sources(query, context, available):
    context = dict(context or {})
    for name, code in STATES.items():
        if re.search(r'\b(?:' + re.escape(name) + '|' + code + r')\b', query, re.I):
            if context.get('jurisdiction') and context['jurisdiction'] != code:
                raise NCCContextRequired('The requested state differs from the project state. Confirm the project jurisdiction.')
            context['jurisdiction'] = code
    explicit = re.search(r'\b(?:ncc|edition)\s*(2022|2025)\b', query, re.I)
    year = explicit.group(1) if explicit else context.get('edition', '')
    if explicit and context.get('edition') and year != context['edition']:
        raise NCCContextRequired('The requested NCC edition differs from the project edition. Confirm the project edition or ask an explicit source comparison separately.')
    if not year and {item[1] for item in available} == {'2025'}:
        year = '2025'  # Owner explicitly imported a 2025-only reference collection.
    classification = re.search(r'\bclass\s*(10|[1-9])\s*([abc])?\b', query, re.I)
    cls = classification.group(1) if classification else str(context.get('building_class', ''))
    number = re.match(r'(10|[1-9])', cls)
    volume = re.search(r'\bvolume\s*(one|two|1|2)\b', query, re.I)
    kinds = {'one'} if volume and volume.group(1).lower() in ('one', '1') else {'two', 'housing'} if volume else None
    if kinds is None and re.search(r'housing provisions', query, re.I):
        kinds = {'two', 'housing'}
    if number:
        class_kinds = {'two', 'housing'} if number.group(1) in ('1', '10') else {'one'}
        if kinds and not kinds.intersection(class_kinds):
            raise NCCContextRequired('The building class and requested NCC volume conflict. Confirm the classification before analysis.')
        kinds = class_kinds
    missing = []
    if year not in ('2022', '2025'): missing.append('applicable NCC edition (2022 or 2025)')
    if not kinds: missing.append('building class or NCC volume')
    if missing:
        raise NCCContextRequired('Please specify ' + ' and '.join(missing) + ' in the project NCC context or question. Edition applicability is not inferred from the current year.')
    assessment = re.search(r'complian|assess|approval|review|check|合规|符合|检查|是否|满足', query, re.I)
    if assessment and not context.get('jurisdiction'):
        raise NCCContextRequired('Set the project state/territory before a compliance assessment. National clauses alone do not establish local applicability.')
    matches = [(name, y, kind) for name, y, kind in available if y == year and kind in kinds]
    if not matches:
        raise NCCContextRequired(f'This library has no matching NCC {year} volume for that building class. Upload the matching reference; a different edition will not be substituted.')
    return matches


def search_catalog(user_id, directory, query, context, top_k):
    from core import ncc_library as library
    index = directory / '.ncc-index.sqlite3'
    if not index.exists():
        return None
    with closing(sqlite3.connect(f'file:{index}?mode=ro', uri=True)) as connection:
        owner = connection.execute('SELECT id FROM owner').fetchone()[0]
        default = os.getenv('NCC_DEFAULT_REFERENCE', '').strip()
        operator_allowed = owner == 'operator_public_ncc' and default and library.resolve_reference(default) == directory.resolve()
        if owner != str(user_id) and not operator_allowed:
            raise PermissionError('This indexed library belongs to another account.')
        files = connection.execute('SELECT name,year,kind,pages,bytes,mtime,sha FROM files').fetchall()
        for name, _, _, _, size, modified, _ in files:
            file = directory / name
            library.resolve_reference(str(file))
            check_owner(library.library_root(), file, user_id)
            if not file.is_file() or (file.stat().st_size, file.stat().st_mtime_ns) != (size, modified):
                raise library.NCCReferenceError('An indexed NCC file changed or was removed. Reimport the library before analysis.')
        context = dict(context or {})
        for name, code in STATES.items():
            if re.search(r"\b(?:" + re.escape(name) + "|" + code + r")\b", query, re.I):
                if context.get("jurisdiction") and context["jurisdiction"] != code:
                    raise NCCContextRequired("The requested state differs from the project state. Confirm the project jurisdiction.")
                context["jurisdiction"] = code
        selected = select_sources(query, context, [row[:3] for row in files])
        words = list(dict.fromkeys(library._tokens(query)))[:32]
        words = [word for word in words if word not in {'2022', '2025', 'class', 'volume', 'one', 'two', 'please', 'what', 'are', 'requirements', 'vic', 'nsw', 'qld', 'sa', 'wa', 'tas', 'nt', 'act', 'victoria', 'south', 'wales', 'queensland', 'tasmania', 'australia', 'northern', 'territory', 'western', 'australian', 'capital'}]
        if not words:
            raise NCCContextRequired("Specify a review topic, such as fire separation, stairs, waterproofing or energy efficiency.")
        expression = ' OR '.join('"' + word + '"' for word in words)
        names = [row[0] for row in selected]
        placeholders = ','.join('?' for _ in names)
        rows = connection.execute(f"SELECT text,name,year,kind,page,clause,sha,bm25(chunks),jurisdiction FROM chunks WHERE chunks MATCH ? AND name IN ({placeholders}) AND (jurisdiction='' OR jurisdiction=?) AND outline=0 ORDER BY bm25(chunks) LIMIT ?",
                                  (expression, *names, context.get("jurisdiction", ""), min(max(int(top_k), 1), 10))).fetchall()
        return _expand_evidence(connection, rows, names, context.get("jurisdiction", ""), top_k, words) if rows else []



def _is_outline(text):
    headings = len(re.findall(r'(?m)^\s*(?:[A-Z]{1,3}\d+[A-Z]\d+|\d+\.\d+\.\d+)\s+', text))
    return len(re.findall(r'\.{4,}', text)) >= 3 or (headings >= 8 and len(re.findall(r'\b(?:must|shall|means|where|if|applies)\b', text, re.I)) <= 1)


def _heading(line):
    line = re.sub(r'\s+', ' ', line).strip()
    match = re.match(r'^(?:(?:NSW|VIC|QLD|SA|WA|TAS|NT|ACT) )?([A-Z]{1,3}\d+[A-Z]\d+(?:\.\d+)*|\d+\.\d+(?:\.\d+)*[a-z]?)\s+\S', line)
    if match:
        return match.group(1)
    match = re.match(r'^Part\s+(\d+\.\d+)\s+\S', line)
    return match.group(1) if match else None


def _store_sections(connection, name, year, kind, sha, reader=None):
    allowed = set()
    def bookmarks(items):
        for item in items:
            if isinstance(item, list): bookmarks(item)
            elif hasattr(item, 'title'):
                code = _heading(item.title)
                if code and (re.fullmatch(r"[A-Z]{1,3}\d+[A-Z]\d+(?:\.\d+)*", code) or re.fullmatch(r"\d+\.\d+\.\d+", code)):
                    allowed.add((reader.get_destination_page_number(item)+1, code))
    if reader is not None: bookmarks(reader.outline)
    active = None
    def flush(item):
        if item:
            connection.execute('INSERT INTO clauses VALUES(?,?,?,?,?,?,?,?,?)',
                (name, year, kind, item['clause'], item['start'], item['end'], '\n'.join(item['lines']), item['state'], sha))
    for page, text, state, outline in connection.execute('SELECT page,text,jurisdiction,outline FROM pages WHERE name=? ORDER BY page', (name,)):
        if outline or (active and active['state'] != state):
            flush(active)
            active = None
        if outline:
            continue
        # PDF anchors sometimes join a clause heading to the page footer.
        text = re.sub(r"\u200a(?=(?:[A-Z]{1,3}\d+[A-Z]\d+|\d+\.\d+\.\d+)\u200a)", "\n", text)
        for line in text.splitlines():
            heading = _heading(line)
            if heading and not (re.fullmatch(r"[A-Z]{1,3}\d+[A-Z]\d+(?:\.\d+)*", heading) or re.fullmatch(r"\d+\.\d+\.\d+", heading)):
                heading = None
            if heading and allowed and (page, heading) not in allowed:
                heading = None
            if heading:
                flush(active)
                active = {'clause':heading, 'start':page, 'end':page, 'state':state, 'lines':[]}
            if active:
                active['lines'].append(line)
                active['end'] = page
    flush(active)


def _expand_evidence(connection, rows, selected_names, state, top_k, query_words):
    """Return complete sections and linked provisions; explicitly flag coverage limits."""
    titles = {'one':'Volume One', 'two':'Volume Two', 'housing':'Housing Provisions'}
    result, seen, warnings = [], set(), set()
    total = 0
    queue = []
    for text, name, year, kind, page, clause, sha, rank, source_state in rows:
        section = connection.execute('SELECT text,page_start,page_end,jurisdiction FROM clauses WHERE name=? AND clause=? AND page_start<=? AND page_end>=? AND jurisdiction=? ORDER BY length(text) DESC LIMIT 1', (name,clause,page,page,source_state)).fetchone()
        if section is None:
            candidates = connection.execute('SELECT text,page_start,page_end,jurisdiction,clause FROM clauses WHERE name=? AND page_start<=? AND page_end>=? AND jurisdiction=?', (name,page,page,source_state)).fetchall()
            if candidates:
                best = max(candidates, key=lambda row: sum(word in row[0].lower() for word in query_words) + int(row[1] == page))
                section, clause = best[:4], best[4]
        if section:
            text, start, end, source_state = section
        else:
            text = connection.execute('SELECT text FROM pages WHERE name=? AND page=?', (name,page)).fetchone()[0]
            start = end = page
            clause = ''
        queue.append((text,name,year,kind,start,end,clause,sha,source_state,'primary'))
    while queue:
        text,name,year,kind,start,end,clause,sha,source_state,reason = queue.pop(0)
        key = (name,start,end,clause,source_state)
        if key in seen:
            continue
        seen.add(key)
        if len(text) > 80000 or total + len(text) > 100000 or len(result) >= 24:
            warnings.add(f'Complete provision {name}, p. {start}-{end}, {clause or "page"} exceeds this review scope; narrow the question for a complete review.')
            continue
        if not clause:
            warnings.add(f"Clause boundary could not be resolved for {name}, page {start}. Full page text is provided; verify continuation in the original PDF.")
        total += len(text)
        result.append({'text':text, 'score':1, 'metadata':{'source':f'{name}, p. {start}' + (f'-{end}' if end != start else ''), 'page':start,'page_end':end,'code':f'NCC {year} {titles[kind]}','clause':clause,'document_sha256':sha,'reference_kind':'server_local_ncc','catalog_version':2,'source_jurisdiction':source_state,'jurisdiction':state,'selection_reason':reason,'complete_section':bool(clause and reason != 'page')}})
        codes = set(re.findall(r'\b[A-Z]{1,3}\d+[A-Z]\d+(?:\.\d+)*\b', text)) | set(re.findall(r'\b\d+\.\d+\.\d+\b', text))
        parts = set(re.findall(r'\bPart\s+(\d+\.\d+)\b', text)) if 'Housing Provisions' in text else set()
        placeholders = ','.join('?' for _ in selected_names)
        for code in sorted(codes | parts):
            linked = connection.execute(f"SELECT text,name,year,kind,page_start,page_end,clause,sha,jurisdiction FROM clauses WHERE name IN ({placeholders}) AND year=? AND (jurisdiction='' OR jurisdiction=?) AND (clause=? OR (?=1 AND kind='housing' AND clause LIKE ?)) ORDER BY jurisdiction DESC,page_start LIMIT 64", (*selected_names,year,state,code,int(code in parts),code+'.%')).fetchall()
            if len(linked) == 64:
                warnings.add(f"Referenced part {code} has more provisions than this review scope can resolve; narrow the question.")
            if not linked:
                warnings.add(f'Referenced provision {code} was not resolved within the selected edition, volume and jurisdiction.')
            for linked_row in linked:
                queue.append((*linked_row,'cross-reference'))
        for standard in re.findall(r'\bAS(?:/NZS)?\s+\d+(?:\.\d+)*(?::\d{4})?', text):
            warnings.add(f'External referenced standard {standard}: full standard text is not supplied by these NCC PDFs.')
    if not result:
        raise NCCContextRequired('No complete provisions fit this review scope. Narrow the question to a specific clause or topic.')
    if warnings:
        result[0]['metadata']['coverage_warnings'] = sorted(warnings)
    return result
