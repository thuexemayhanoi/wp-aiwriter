#!/usr/bin/env python3
"""English pipeline: deterministic QA of the English articles in en/posts/, and a create-only publisher that registers
every post with VI-EN Core before it goes public, then verifies it at /en/{slug}/.

Topic matrix: en/topics.json (the single source of IDs, titles, slugs and categories). Business facts for the QA:
en/business.json. Policy: en/publication-policy.json. Ledger: data/en-publication-state.json. The Vietnamese pipeline
(scripts/engine.py, posts/, data/topics.json) is untouched; its helpers are reused read-only.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
import engine  # noqa: E402
import seo_common  # noqa: E402

EN_DIR = ROOT / 'en'
TOPICS_PATH = EN_DIR / 'topics.json'
POSTS_DIR = EN_DIR / 'posts'
POLICY_PATH = EN_DIR / 'publication-policy.json'
BUSINESS_PATH = EN_DIR / 'business.json'
STATE_PATH = ROOT / 'data' / 'en-publication-state.json'
REPORT_DIR = ROOT / 'reports' / 'en'
WP_URL = engine.WP_URL
EN_HOME = WP_URL + '/en/'
MARKER = 'wp-aiwriter-en:en_id={id};sha256={hash}'

ROUTE_RESERVED = {'page', 'category', 'tag', 'author', 'search', 'feed', 'embed', 'comments', 'attachment', 'trackback',
                  'wp-json', 'wp-admin', 'wp-content', 'wp-includes'}
# Protect the English service and legal pages from future article slug collisions.
EN_PAGE_SLUGS = {
    'about', 'prices', 'contact', 'rental-guide', 'faq', 'motorbikes',
    'services', '50cc-bikes', 'electric-scooters', 'guides', 'areas',
    'hoan-kiem', 'old-quarter', 'long-bien', 'ba-dinh', 'gia-lam',
    'privacy', 'terms',
}
SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,74}$')
VI_LETTERS = re.compile(r'[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵĂÂĐÊÔƠƯÀÁẢÃẠẰẮẲẴẶẦẤẨẪẬÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ]')
VI_STOPWORDS = re.compile(r'\b(của|và|là|các|những|được|trong|không|với|cho|này|bạn|thuê|giá|khi|để)\b', re.I)
PHONE_RE = re.compile(r'(?:\+84[\s.-]?\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4}|\b0\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4}\b)')
NUMBER = r'([\d][\d.,]*)(?:\s*[\u2013\u2014-]\s*([\d][\d.,]*))?\s*(k|million|m)?'
AMOUNT_RE = re.compile(r'(?:VND|₫|dong)\s*' + NUMBER + r'\b|' + NUMBER + r'\s*(?:VND|₫|dong)\b', re.I)
FINE_CONTEXT = re.compile(r'\b(fine[sd]?|penalt(?:y|ies)|fined)\b', re.I)
USD_RE = re.compile(r'(?:\$\s?\d|\d\s?(?:USD|US\$|dollars?)\b)', re.I)
LEGAL_WORDS = re.compile(r'\b(licen[cs]e|IDP|international driving permit|decree|law|fine[sd]?|penalt(?:y|ies)|police|legal(?:ly)?|insurance)\b', re.I)
OFFICIAL_DOMAINS = ('.gov.vn', 'thuvienphapluat.vn', 'chinhphu.vn', 'csgt.vn', 'luatvietnam.vn', 'vbpl.vn', 'moj.gov.vn', 'mt.gov.vn', 'bocongan.gov.vn', 'unece.org', 'honda.com.vn', 'yamaha-motor.com.vn')
DATE_RE = re.compile(r'\b(effective|in force|took effect|applies from|valid from|as of|updated)\b[^.\n]{0,60}?\b(20\d{2})\b', re.I)


def now():
    return engine.now()


def today_site():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime('%Y-%m-%d')


def read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))


def load_policy():
    policy = read_json(POLICY_PATH)
    required = {'enabled', 'mode', 'pilot_ids', 'batch_size', 'category_ids', 'legal_categories', 'min_score', 'require_live_routes', 'min_words'}
    if (not required <= set(policy) or policy['mode'] not in ('pilot', 'batch')
            or not 1 <= int(policy['batch_size']) <= 20
            or not 1600 <= int(policy['min_words']) <= 5000):
        raise ValueError('en/publication-policy.json violates the pipeline safeguards')
    return policy


def load_business():
    business = read_json(BUSINESS_PATH)
    for key in ('phone_local', 'phone_international', 'allowed_amounts_vnd', 'forbidden_fragments', 'pages_en'):
        if key not in business:
            raise ValueError(f'en/business.json misses {key}')
    return business


def load_topics(policy=None):
    rows = read_json(TOPICS_PATH)
    policy = policy or load_policy()
    leaves = set(policy['category_ids']['leaves'])
    topics, slugs, titles = {}, set(), set()
    for row in rows:
        i = int(row['id'])
        slug, title, category = row['slug'], row['title'].strip(), int(row['category_id'])
        if i in topics or slug in slugs or engine.normalized(title) in titles:
            raise ValueError(f'Duplicate id, slug or title in en/topics.json at #{i}')
        if not SLUG_RE.match(slug) or slug in ROUTE_RESERVED or slug in EN_PAGE_SLUGS:
            raise ValueError(f'Slug of #{i} cannot be routed below /en/: {slug}')
        if category not in leaves:
            raise ValueError(f'Category of #{i} is not an English leaf category: {category}')
        topics[i] = {'id': i, 'title': title, 'slug': slug, 'category_id': category,
                     'intent': row.get('intent', ''), 'hub': row.get('hub', ''), 'keywords': row.get('keywords', [])}
        slugs.add(slug)
        titles.add(engine.normalized(title))
    return topics


def front_matter(text):
    match = re.fullmatch(r'---\n(.*?)\n---\n(.*)', text, re.S)
    if not match:
        raise ValueError('Missing front matter')
    metadata = {}
    for line in match[1].splitlines():
        if not line.strip():
            continue
        key, sep, val = line.partition(':')
        if not sep or key.strip() in metadata:
            raise ValueError('Malformed or duplicate front matter key')
        metadata[key.strip()] = val.strip().strip('"').strip("'")
    return metadata, match[2].strip()


def sections(body):
    """Level-2 sections of the body: [(heading, text)]."""
    parts = re.split(r'^## +(.+?)\s*$', body, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def words_of(text):
    return re.findall(r"[A-Za-z][A-Za-z'’-]*|\d+", text)


def amounts_in(text):
    """Every VND amount in the text as (value, is_fine): ranges, thousands (150k) and millions (2-4 million) included."""
    found = []
    for match in AMOUNT_RE.finditer(text):
        groups = match.groups()
        first, second, unit = (groups[0], groups[1], groups[2]) if groups[0] else (groups[3], groups[4], groups[5])
        factor = {'k': 1000, 'million': 1000000, 'm': 1000000}.get((unit or '').lower(), 1)
        context = text[max(0, match.start() - 160):match.end() + 160]
        for raw in (first, second):
            digits = re.sub(r'[^\d]', '', raw or '')
            if digits:
                found.append((int(digits) * factor, bool(FINE_CONTEXT.search(context))))
    return found


def verified_legacy_short_article(article_id, topic, body):
    """Allow unchanged already-published English posts to keep their old minimum.

    Only an exact, verified publication-ledger hash qualifies. A new manuscript
    or any edit to a shorter legacy article must pass the current word minimum.
    This is a QA compatibility allowance, never a republishing bypass.
    """
    try:
        state = read_json(STATE_PATH)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    previous = state.get('posts', {}).get(str(article_id), {})
    return (previous.get('phase') == 'VERIFIED'
            and previous.get('status') == 'publish'
            and previous.get('title') == topic['title']
            and previous.get('slug') == topic['slug']
            and previous.get('category_id') == topic['category_id']
            and previous.get('source_hash') == seo_common.sha256_text(body))


def read_article(path, topics, business, policy):
    metadata, body = front_matter(path.read_text(encoding='utf-8'))
    try:
        i = int(metadata['en_id'])
    except (KeyError, ValueError):
        raise ValueError('Invalid en_id')
    if i not in topics or path.name != f'{i:04}.md':
        raise ValueError('en_id/filename must match a row of en/topics.json')
    topic = topics[i]
    if metadata.get('title') != topic['title'] or metadata.get('slug') != topic['slug'] or metadata.get('category_id') != str(topic['category_id']):
        raise ValueError(f'Title, slug or category differs from en/topics.json #{i}')
    if metadata.get('ready', 'false').lower() != 'true':
        return {'id': i, 'ready': False}
    description = metadata.get('description', '').strip()
    html = engine.markdown_to_html(body)
    text = engine.visible(html)
    words = words_of(text)
    secs = sections(body)
    problems = []
    min_words = int(policy['min_words'])
    if len(words) > 5000 or (len(words) < min_words and
                            not (1000 <= len(words) and verified_legacy_short_article(i, topic, body))):
        problems.append(f'{len(words)} words; new or revised English articles need {min_words} to 5000')
    if len(secs) < 3:
        problems.append('fewer than 3 level-2 sections')
    if re.search(r'\b(TODO|TBD|Lorem ipsum)\b|^# |<\s*(script|iframe|style)\b|javascript:', body, re.I | re.M):
        problems.append('placeholder, duplicate H1, or unsafe markup')
    letters = re.findall(r'[A-Za-zÀ-ỹ]', text)
    vietnamese = VI_LETTERS.findall(text)
    if letters and len(vietnamese) / len(letters) > 0.02 or len(VI_STOPWORDS.findall(text)) >= 5:
        problems.append('Vietnamese text in an English article')
    for fragment in business['forbidden_fragments']:
        if fragment.lower() in text.lower() or fragment.lower() in body.lower():
            problems.append(f'forbidden business fragment: {fragment}')
    for phone in set(PHONE_RE.findall(text)):
        digits = re.sub(r'\D', '', phone)
        if digits not in (re.sub(r'\D', '', business['phone_local']), re.sub(r'\D', '', business['phone_international'])):
            problems.append(f'phone number that is not the business phone: {phone}')
    allowed = set(business['allowed_amounts_vnd'])
    for amount, is_fine in amounts_in(text):
        # A fine or penalty is a legal figure, covered by the official-source gate below; a price must be a listed one.
        if amount not in allowed and not is_fine:
            problems.append(f'unverified VND amount: {amount}')
    if USD_RE.search(text):
        problems.append('prices must be stated in VND only (no USD conversions)')
    links = seo_common.md_links(body)
    for label, url in links:
        if seo_common.is_internal(url, WP_URL) and not url.startswith(EN_HOME):
            problems.append(f'internal link outside /en/: {url}')
        if not url.startswith('https://'):
            problems.append(f'link must be https: {url}')
    for alt, src in re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', body):
        if not alt.strip():
            problems.append(f'image without alt text: {src}')
    paragraphs = [engine.normalized(p) for p in re.split(r'\n\s*\n', body) if len(p) > 140]
    if len(set(paragraphs)) != len(paragraphs):
        problems.append('repeated paragraph')
    headings = {h.lower() for h, _ in secs}
    source_links = [url for h, t in secs if h.lower().startswith('source') for _, url in seo_common.md_links(t)]
    official = [u for u in source_links if any(d in seo_common.host_of(u) for d in OFFICIAL_DOMAINS)]
    legal = topic['category_id'] in set(policy['legal_categories']) or len(LEGAL_WORDS.findall(text)) >= 6
    if legal:
        if not official:
            problems.append('legal or regulatory topic without an official source in a "## Sources" section')
        if not DATE_RE.search(text):
            problems.append('legal or regulatory topic without an effective date ("effective ...", "as of ...")')
    if problems:
        raise ValueError('; '.join(problems))
    score, notes = qa_score(body, text, words, secs, description, links, source_links, topic, legal)
    if score < int(policy['min_score']):
        raise ValueError(f'QA score {score} below {policy["min_score"]}: ' + '; '.join(notes))
    return {**topic, 'ready': True, 'words': len(words), 'body': body, 'description': description, 'score': score,
            'notes': notes, 'legal': legal, 'sources': source_links, 'headings': [h for h, _ in secs],
            'hash': seo_common.sha256_text(body)}


def qa_score(body, text, words, secs, description, links, source_links, topic, legal):
    score, notes = 100, []

    def ding(points, note):
        nonlocal score
        score -= points
        notes.append(f'-{points} {note}')
    if not description:
        ding(10, 'no description in the front matter')
    elif not 110 <= len(description) <= 175:
        ding(5, f'description is {len(description)} characters (110-175 reads best)')
    if len(words) < 1200:
        ding(5, 'under 1200 words')
    elif len(words) > 3500:
        ding(3, 'over 3500 words')
    if len(secs) < 4:
        ding(5, 'fewer than 4 level-2 sections')
    headings = [h.lower() for h, _ in secs]
    if not any('faq' in h or 'question' in h for h in headings):
        ding(8, 'no FAQ section')
    if not source_links:
        ding(8 if not legal else 0, 'no "## Sources" section')
    internal = [u for _, u in links if u.startswith(EN_HOME)]
    if len(internal) < 2:
        ding(8, f'{len(internal)} internal link(s) to /en/; 2 or more expected')
    external = [u for _, u in links if not seo_common.is_internal(u, WP_URL)]
    if not external:
        ding(5, 'no external reference link')
    if not 35 <= len(topic['title']) <= 65:
        ding(4, f'title is {len(topic["title"])} characters (35-65 reads best)')
    if len(topic['slug']) > 60:
        ding(2, 'slug longer than 60 characters')
    intro = body.split('\n## ', 1)[0]
    if len(words_of(engine.visible(engine.markdown_to_html(intro)))) < 60:
        ding(5, 'intro before the first section is shorter than 60 words')
    long_paragraphs = [p for p in re.split(r'\n\s*\n', body) if not p.startswith(('#', '|', '-', '*', '>')) and len(words_of(p)) > 180]
    if long_paragraphs:
        ding(min(9, 3 * len(long_paragraphs)), f'{len(long_paragraphs)} paragraph(s) over 180 words')
    return max(0, score), notes


def shingles(body):
    return engine.shingles(body)


def load_articles(topics, business, policy):
    articles, errors = [], []
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(POSTS_DIR.glob('[0-9][0-9][0-9][0-9].md')):
        try:
            articles.append(read_article(path, topics, business, policy))
        except ValueError as exc:
            errors.append({'file': str(path.relative_to(ROOT)), 'reason': str(exc)})
    accepted, signatures, outlines = [], [], {}
    ready = [a for a in articles if a['ready']]
    vectors = seo_common.tfidf_vectors({a['id']: a['title'] + ' ' + ' '.join(a['headings']) for a in ready}) if len(ready) > 1 else {}
    for article in ready:
        sig = shingles(article['body'])
        duplicate = next((other for other, prior in signatures
                          if len(sig & prior) / max(1, min(len(sig), len(prior))) > .70), None)
        if duplicate is not None:
            errors.append({'id': article['id'], 'reason': f'Near-duplicate content of #{duplicate}'})
            continue
        same_intent = next((other for other in outlines if seo_common.cosine(vectors[article['id']], vectors[other]) > .60), None) if vectors else None
        if same_intent is not None:
            errors.append({'id': article['id'], 'reason': f'Same search intent as #{same_intent} (title and outline)'})
            continue
        signatures.append((article['id'], sig))
        outlines[article['id']] = True
        accepted.append(article)
    return articles, accepted, errors


# ------------------------------------------------------------------ publisher -------------------------------------
class EnLedger:
    """Write-ahead ledger of the English publications, checkpointed to origin/main like the Vietnamese one."""

    def __init__(self, persist_remote=False):
        self.remote = persist_remote
        self.expected_blob = None
        if persist_remote:
            engine.git('fetch', 'origin', 'main')
            shown = subprocess.run(['git', 'show', 'origin/main:data/en-publication-state.json'], cwd=ROOT,
                                   capture_output=True, text=True)
            if shown.returncode == 0:
                STATE_PATH.parent.mkdir(exist_ok=True)
                STATE_PATH.write_text(shown.stdout)
                self.expected_blob = engine.git('rev-parse', 'origin/main:data/en-publication-state.json')
        self.data = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {'version': 1, 'posts': {}}

    def save(self):
        self.data['updated_at'] = now()
        STATE_PATH.parent.mkdir(exist_ok=True)
        STATE_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + '\n')
        if not self.remote:
            return
        for attempt in range(3):
            engine.git('fetch', 'origin', 'main')
            base = engine.git('rev-parse', 'origin/main')
            current = subprocess.run(['git', 'rev-parse', f'{base}:data/en-publication-state.json'], cwd=ROOT,
                                     capture_output=True, text=True)
            remote_blob = current.stdout.strip() if current.returncode == 0 else None
            if remote_blob != self.expected_blob:
                raise RuntimeError('Checkpoint changed outside this serialized publisher; reconcile before any POST')
            blob = engine.git('hash-object', '-w', str(STATE_PATH))
            with tempfile.TemporaryDirectory() as tmp:
                env = {**os.environ, 'GIT_INDEX_FILE': str(pathlib.Path(tmp) / 'index')}
                engine.git('read-tree', base, env=env)
                engine.git('update-index', '--add', '--cacheinfo', f'100644,{blob},data/en-publication-state.json', env=env)
                tree = engine.git('write-tree', env=env)
                commit = engine.git('commit-tree', tree, '-p', base, input_text='chore(en): checkpoint English publication\n')
            result = subprocess.run(['git', 'push', 'origin', f'{commit}:refs/heads/main'], cwd=ROOT, capture_output=True, text=True)
            if result.returncode == 0:
                self.expected_blob = blob
                return
        raise RuntimeError('Could not persist remote checkpoint; no further POST allowed')


def record(ledger, article, **fields):
    previous = ledger.data['posts'].get(str(article['id']), {})
    ledger.data['posts'][str(article['id'])] = {**previous, 'title': article['title'], 'slug': article['slug'],
                                                'source_hash': article['hash'], 'checked_at': now(), **fields}
    ledger.save()


def vien_status(rest):
    status, data = rest.call('nh-vien/v1/status')
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError(f'nh-vien/v1/status answered HTTP {status}: VI-EN Core 0.5.1 is not installed or the account is not an administrator')
    return data


def gate(status, policy, needed_categories):
    problems = []
    if policy['require_live_routes'] and not status.get('live'):
        problems.append('the English routes are not live (switch them on under Tools > VI/EN Links first)')
    registered = set(int(x) for x in status.get('english_categories', []))
    missing = sorted(set(needed_categories) - registered)
    if missing:
        problems.append(f'English categories not registered with VI-EN Core: {missing}')
    return problems


def duplicates(article, inventory):
    marker = f"wp-aiwriter-en:en_id={article['id']};"
    return [p for p in inventory if engine.normalized(engine.title_of(p)) == engine.normalized(article['title'])
            or p['slug'] == article['slug'] or marker in p.get('content', {}).get('raw', '')]


def verify(client, rest, article, post_id, category_id):
    post = client.get(f'posts/{post_id}?context=edit')
    marker = MARKER.format(id=article['id'], hash=article['hash'])
    raw = post.get('content', {}).get('raw', '')
    if (post.get('status') != 'publish' or post.get('slug') != article['slug'] or engine.title_of(post) != article['title']
            or marker not in raw or post.get('categories') != [category_id]):
        raise RuntimeError('Post-readback verification failed; preserve existing post and investigate')
    status = vien_status(rest)
    if post_id not in [int(x) for x in status.get('public_en_posts', [])]:
        raise RuntimeError('VI-EN Core does not list the post as a public English post')
    url = f"{EN_HOME}{article['slug']}/"
    reply = seo_common.http_get(url, timeout=30, retries=1)
    page = seo_common.parse_page(reply.text) if reply.text else {}
    if reply.status != 200 or reply.headers.get('x-nh-vien-lang') != 'en' or not (page.get('lang') or '').lower().startswith('en'):
        raise RuntimeError(f'{url} answered HTTP {reply.status} without the English marker; the post stays as it is')
    if engine.normalized(article['title']) not in engine.normalized(reply.text) or seo_common.norm_url(page.get('canonical') or '') != seo_common.norm_url(url):
        raise RuntimeError(f'{url} does not show the title or its canonical is not itself')
    native = seo_common.http_get(f"{WP_URL}/{article['slug']}/", timeout=30, retries=1)
    if seo_common.norm_url(native.final_url) != seo_common.norm_url(url):
        raise RuntimeError('the ordinary address of the English post does not redirect to /en/')
    return {**post, 'en_url': url}


def sync(client, rest, ready, ledger, policy, report):
    client.get('users/me?context=edit&_fields=id')
    status = vien_status(rest)
    report['vien'] = {k: status.get(k) for k in ('version', 'enabled', 'source', 'live', 'english_categories', 'public_en_posts')}
    needed = sorted({a['category_id'] for a in ready}) + list(policy['category_ids']['parents'])
    problems = gate(status, policy, needed)
    if problems:
        raise RuntimeError('BLOCKED: ' + '; '.join(problems))
    inventory = client.all('posts', context='edit', status='any', _fields='id,title,slug,status,link,categories,content')
    report['auth_ok'] = True
    eligible, created = [], 0
    for article in ready:
        matches = duplicates(article, inventory)
        old = ledger.data['posts'].get(str(article['id']), {})
        if len(matches) > 1:
            report['duplicates'].append({'id': article['id'], 'wp_ids': [p['id'] for p in matches]})
            continue
        if matches:
            report['existing'].append({'id': article['id'], 'wp_id': matches[0]['id'], 'status': matches[0]['status'], 'phase': old.get('phase')})
            continue
        if old.get('phase'):
            report['errors'].append({'id': article['id'], 'reason': f"Unresolved prior write ({old['phase']}); reconcile the ledger instead of reposting"})
            continue
        eligible.append(article)
    limit = int(policy['batch_size'])
    remaining, attempts = [], 0
    for article in eligible:
        # One attempt per article per run, at most batch_size attempts: a failed attempt is never followed by a retry.
        if attempts >= limit:
            remaining.append(article['id'])
            continue
        attempts += 1
        try:
            category_id = article['category_id']
            marker = MARKER.format(id=article['id'], hash=article['hash'])
            payload = {'title': article['title'], 'slug': article['slug'], 'status': 'draft', 'excerpt': article['description'],
                       'categories': [category_id],
                       'content': f'<!-- {marker} -->\n' + engine.markdown_to_html(article['body']),
                       'meta': {'nh_summary': article['description'], 'nh_content_updated': today_site()}}
            record(ledger, article, phase='POST_INTENT', category_id=category_id)
            result = client.request('posts', payload=payload)[0]
            post_id = int(result['id'])
            record(ledger, article, phase='DRAFT_CREATED', wp_id=post_id)
            http, data = rest.call('nh-vien/v1/posts', {'id': post_id})
            if http != 200:
                record(ledger, article, phase='REGISTER_FAILED', wp_id=post_id, reason=str(data))
                raise RuntimeError(f'VI-EN Core refused to register post {post_id} as English (HTTP {http}); left as a draft')
            record(ledger, article, phase='REGISTERED', wp_id=post_id)
            client.request(f'posts/{post_id}', payload={'status': 'publish'})
            record(ledger, article, phase='VERIFY_PENDING', wp_id=post_id)
            post = verify(client, rest, article, post_id, category_id)
            record(ledger, article, phase='VERIFIED', wp_id=post_id, status='publish', url=post['en_url'])
            inventory.append(post)
            report['created'].append({'id': article['id'], 'wp_id': post_id, 'url': post['en_url'], 'category_id': category_id, 'score': article['score']})
            created += 1
        except (RuntimeError, ValueError, KeyError) as exc:
            report['errors'].append({'id': article['id'], 'reason': str(exc)})
            if 'heckpoint' in str(exc):
                raise
    report['created_count'] = created
    report['remaining_ready_ids'] = remaining
    report['has_more'] = bool(remaining)


def write_report(report):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / 'latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = (f"### EN pipeline — {report['mode']}\n\n"
               f"- Topics: {report['topics']}; authored: {report['authored']}; QA PASS: {report['qa_pass']}; QA FAIL: {len(report['qa_errors'])}\n"
               f"- Policy: enabled={report['policy']['enabled']}, mode={report['policy']['mode']}, batch={report['policy']['batch_size']}\n"
               f"- VI-EN Core: {report.get('vien', 'not checked')}\n"
               f"- Newly created and verified: {len(report['created'])}; existing: {len(report['existing'])}; "
               f"duplicates: {len(report['duplicates'])}; errors: {len(report['errors'])}; next: {report.get('remaining_ready_ids', [])[:5]}\n")
    if report.get('scores'):
        summary += '\nQA scores:\n```json\n' + json.dumps(report['scores'], ensure_ascii=False, indent=2) + '\n```\n'
    for key in ('created', 'existing', 'duplicates', 'errors', 'qa_errors'):
        if report[key]:
            summary += f'\n{key}:\n```json\n' + json.dumps(report[key], ensure_ascii=False, indent=2) + '\n```\n'
    (REPORT_DIR / 'summary.md').write_text(summary, encoding='utf-8')
    print(summary)
    seo_common.step_summary(summary)
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            out.write(f"has_more={str(report.get('has_more', False)).lower()}\n")


def run(args):
    policy = load_policy()
    business = load_business()
    topics = load_topics(policy)
    all_items, ready, errors = load_articles(topics, business, policy)
    report = {'at': now(), 'mode': args.mode, 'live': args.live, 'topics': len(topics), 'authored': len(all_items), 'qa_pass': len(ready),
              'qa_errors': errors, 'created': [], 'existing': [], 'duplicates': [], 'errors': [], 'has_more': False,
              'policy': {k: policy[k] for k in ('enabled', 'mode', 'batch_size', 'pilot_ids')},
              'scores': [{'id': a['id'], 'score': a['score'], 'words': a['words'], 'notes': a['notes']} for a in ready]}
    try:
        if policy['mode'] == 'pilot':
            ready = [a for a in ready if a['id'] in set(int(x) for x in policy['pilot_ids'])]
        report['queue'] = [a['id'] for a in ready]
        if args.mode == 'sync':
            if not args.live:
                report['notice'] = 'DRY RUN - no WordPress authentication or writes'
            elif not policy['enabled']:
                raise RuntimeError('BLOCKED: en/publication-policy.json has enabled=false; zero WordPress writes')
            else:
                if errors:
                    raise ValueError('QA errors present; publishing aborted with zero new WordPress writes')
                user, password = os.getenv('WP_USERNAME'), os.getenv('WP_APPLICATION_PASSWORD')
                if not user or not password:
                    raise RuntimeError('BLOCKED: missing WP_USERNAME / WP_APPLICATION_PASSWORD; zero WordPress writes')
                import en_ops  # noqa: E402
                ledger = EnLedger(args.persist_state)
                sync(engine.WPClient(user, password), en_ops.Rest(user, password), ready, ledger, policy, report)
    except (RuntimeError, ValueError) as exc:
        report['errors'].append({'reason': str(exc)})
    finally:
        write_report(report)
    return 1 if errors or report['errors'] else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['qa', 'sync'], default='qa')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--persist-state', action='store_true')
    sys.exit(run(parser.parse_args()))
