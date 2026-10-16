"""Shared text model of published posts/pages for linking, content and AEO audits."""
import math

from .htmlparse import block_texts, parse
from .textutil import TfIdf, candidate_pairs, cosine, features, shingles


def key_of(record):
    return f"{record['type']}:{record['id']}"


class Corpus:
    def __init__(self, records, content_cache):
        self.records = {key_of(r): r for r in records if r.get('status') == 'publish'}
        self.parsed = {}
        self.text = {}
        for key, r in self.records.items():
            item = content_cache.get(key) or {}
            html = (item.get('content') or {}).get('rendered', '')
            parser = parse(html)
            self.parsed[key] = parser
            self.text[key] = parser.visible_text() or r.get('excerpt', '')
        self.body = TfIdf({k: features(t) for k, t in self.text.items()})
        self.body_pruned = {k: dict(sorted(v.items(), key=lambda kv: kv[1], reverse=True)[:80])
                            for k, v in self.body.vectors.items()}
        self.titles = TfIdf({k: features(r['title']) for k, r in self.records.items()})
        self._shingles = {}
        self._neighbors = None

    def neighbors(self, min_score=0.15):
        """{key: [(other, full_cosine), ...]} sorted desc; candidates from pruned vectors."""
        if self._neighbors is None:
            out = {k: [] for k in self.records}
            for (a, b), _approx in candidate_pairs(self.body_pruned, min_score).items():
                sim = self.body_cos(a, b)
                out[a].append((b, sim))
                out[b].append((a, sim))
            for k in out:
                out[k].sort(key=lambda kv: kv[1], reverse=True)
            self._neighbors = out
        return self._neighbors

    def blocks(self, key):
        parser = self.parsed.get(key)
        return block_texts(parser) if parser else []

    def shingle_set(self, key):
        if key not in self._shingles:
            self._shingles[key] = shingles(self.text.get(key, ''))
        return self._shingles[key]

    def body_cos(self, a, b):
        return cosine(self.body.vectors.get(a, {}), self.body.vectors.get(b, {}))

    def title_cos(self, a, b):
        return cosine(self.titles.vectors.get(a, {}), self.titles.vectors.get(b, {}))

    def idf(self, term):
        return self.body.idf.get(term, math.log(1 + self.body.n) + 1)

    def centroid(self, keys):
        acc = {}
        for k in keys:
            for t, w in self.body.vectors.get(k, {}).items():
                acc[t] = acc.get(t, 0.0) + w
        length = math.sqrt(sum(w * w for w in acc.values())) or 1.0
        return {t: w / length for t, w in acc.items()}
