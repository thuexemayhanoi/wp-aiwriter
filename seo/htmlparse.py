"""Dependency-free HTML extraction for SEO: head metadata, headings, links, images, JSON-LD.

The same parser reads full public pages and REST ``content.rendered`` fragments. Text inside
script/style/noscript/template is ignored. Paragraph blocks keep track of which text is
already inside a link, so link suggestions only use plain text that really exists.
"""
from html.parser import HTMLParser
import html as html_lib
import json
import re

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param',
        'source', 'track', 'wbr'}
SKIP_TEXT = {'script', 'style', 'noscript', 'template', 'svg'}
BLOCKS = {'p', 'li', 'td', 'th', 'dd', 'dt', 'blockquote', 'figcaption'}
HEADINGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}


def clean(text):
    return ' '.join(html_lib.unescape(text or '').split())


class SEOParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self._in_title = False
        self._title_parts = []
        self.lang = None
        self.metas = {}            # name/property (lowercase) -> list of content
        self.links_rel = []        # (rel, href, attrs)
        self.headings = []         # (level, text)
        self.anchors = []          # dict(href, text, rel, in_heading, target)
        self.images = []           # dict(src, alt or None, width, height, loading, srcset)
        self.jsonld = []           # dict(text, attrs)
        self.itemtypes = []
        self.http_resources = []
        self.blocks = []           # dict(tag, segments=[(text, in_link)])
        self.text_parts = []
        self.iframes = []
        self._skip = 0
        self._script = None
        self._heading = None
        self._heading_parts = []
        self._anchor = None
        self._anchor_parts = []
        self._block_stack = []

    # ---- helpers -------------------------------------------------------------------------
    @staticmethod
    def _attrs(attrs):
        return {k.lower(): (v if v is not None else '') for k, v in attrs}

    def _open_block(self, tag):
        self._block_stack.append({'tag': tag, 'segments': []})

    def _close_block(self, tag=None):
        if not self._block_stack:
            return
        block = self._block_stack.pop()
        text = clean(''.join(t for t, _ in block['segments']))
        if text:
            self.blocks.append(block)

    # ---- parser callbacks ----------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = self._attrs(attrs)
        if tag == 'html' and a.get('lang'):
            self.lang = a['lang']
        if 'itemtype' in a:
            self.itemtypes.append(a['itemtype'])
        for key in ('src', 'href'):
            if a.get(key, '').startswith('http://') and tag in ('img', 'script', 'link', 'iframe', 'source', 'video', 'audio'):
                if not (tag == 'link' and a.get('rel', '').lower() in ('canonical', 'alternate', 'shortlink')):
                    self.http_resources.append(a[key])
        if tag == 'script':
            stype = a.get('type', '').lower()
            self._script = {'type': stype, 'attrs': a, 'parts': []}
            self._skip += 1
            return
        if tag in SKIP_TEXT:
            self._skip += 1
            return
        if tag == 'title' and self.title is None and not self._skip:
            self._in_title = True
            return
        if tag == 'meta':
            key = (a.get('name') or a.get('property') or a.get('http-equiv') or '').lower()
            if key:
                self.metas.setdefault(key, []).append(a.get('content', ''))
            return
        if tag == 'link':
            rel = a.get('rel', '').lower()
            if rel:
                self.links_rel.append((rel, a.get('href', ''), a))
            return
        if tag == 'iframe':
            self.iframes.append(a.get('src', ''))
        if tag in HEADINGS:
            self._heading = int(tag[1])
            self._heading_parts = []
        if tag == 'a':
            self._anchor = {'href': a.get('href', ''), 'rel': a.get('rel', ''), 'target': a.get('target', ''),
                            'in_heading': self._heading is not None}
            self._anchor_parts = []
        if tag == 'img':
            self.images.append({'src': a.get('src') or a.get('data-src') or '',
                                'alt': a['alt'] if 'alt' in a else None,
                                'width': a.get('width', ''), 'height': a.get('height', ''),
                                'loading': a.get('loading', ''), 'srcset': bool(a.get('srcset'))})
        if tag in BLOCKS:
            if tag == 'p' and self._block_stack and self._block_stack[-1]['tag'] == 'p':
                self._close_block()
            self._open_block(tag)
        if tag == 'br' and self._block_stack:
            self._block_stack[-1]['segments'].append((' ', self._anchor is not None))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'script' and self._script is not None:
            if 'ld+json' in self._script['type']:
                self.jsonld.append({'text': ''.join(self._script['parts']), 'attrs': self._script['attrs']})
            self._script = None
            self._skip = max(0, self._skip - 1)
            return
        if tag in SKIP_TEXT:
            self._skip = max(0, self._skip - 1)
            return
        if tag == 'title' and self._in_title:
            self._in_title = False
            self.title = clean(''.join(self._title_parts))
            return
        if tag in HEADINGS and self._heading is not None:
            self.headings.append((self._heading, clean(''.join(self._heading_parts))))
            self._heading = None
        if tag == 'a' and self._anchor is not None:
            self._anchor['text'] = clean(''.join(self._anchor_parts))
            self.anchors.append(self._anchor)
            self._anchor = None
        if tag in BLOCKS:
            # Close the innermost matching block (tolerates sloppy nesting).
            for idx in range(len(self._block_stack) - 1, -1, -1):
                if self._block_stack[idx]['tag'] == tag:
                    while len(self._block_stack) > idx:
                        self._close_block()
                    break

    def handle_data(self, data):
        if self._script is not None:
            self._script['parts'].append(data)
            return
        if self._skip:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        self.text_parts.append(data)
        if self._heading is not None:
            self._heading_parts.append(data)
        if self._anchor is not None:
            self._anchor_parts.append(data)
        if self._block_stack and self._heading is None:
            self._block_stack[-1]['segments'].append((data, self._anchor is not None))

    def close(self):
        super().close()
        while self._block_stack:
            self._close_block()

    # ---- derived values ------------------------------------------------------------------
    def meta(self, key):
        values = self.metas.get(key.lower(), [])
        return values[0] if values else None

    def canonicals(self):
        return [href for rel, href, _ in self.links_rel if 'canonical' in rel.split()]

    def rel_links(self, name):
        return [href for rel, href, _ in self.links_rel if name in rel.split()]

    def visible_text(self):
        return clean(' '.join(self.text_parts))


def parse(markup):
    parser = SEOParser()
    try:
        parser.feed(markup or '')
        parser.close()
    except Exception:  # noqa: BLE001 - malformed markup must not abort a site-wide audit
        pass
    return parser


def block_texts(parser):
    """Plain-text paragraphs; each item: (full_text, [(text, in_link), ...])."""
    out = []
    for block in parser.blocks:
        segments = [(t, linked) for t, linked in block['segments']]
        out.append((clean(''.join(t for t, _ in segments)), segments))
    return out


def jsonld_nodes(parser):
    """Return (nodes, errors, sources). sources counts blocks by origin (yoast/other)."""
    nodes, errors, sources = [], [], {'yoast': 0, 'other': 0}
    for block in parser.jsonld:
        origin = 'yoast' if 'yoast' in block['attrs'].get('class', '').lower() else 'other'
        sources[origin] += 1
        text = block['text'].strip()
        if not text:
            errors.append('empty JSON-LD block')
            continue
        try:
            data = json.loads(text)
        except ValueError as exc:
            errors.append(f'invalid JSON-LD ({origin}): {str(exc)[:80]}')
            continue
        stack = data if isinstance(data, list) else [data]
        for item in stack:
            if not isinstance(item, dict):
                continue
            graph = item.get('@graph')
            if isinstance(graph, list):
                for node in graph:
                    if isinstance(node, dict):
                        nodes.append({**node, '_origin': origin})
            else:
                nodes.append({**item, '_origin': origin})
    return nodes, errors, sources


def node_types(node):
    value = node.get('@type', [])
    return [value] if isinstance(value, str) else [v for v in value if isinstance(v, str)]


HTML_COMMENT = re.compile(r'<!--(.*?)-->', re.S)


def html_comments(markup):
    return [c.strip() for c in HTML_COMMENT.findall(markup or '')]
