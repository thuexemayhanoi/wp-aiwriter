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
        self.body_pruned = {}
        for k, v in self.body.vectors.items():
            top = dict(sorted(v.items(), key=lambda kv: kv[1], reverse=True)[:80])
            length = math.sqrt(sum(w * w for w in top.values())) or 1.0
            # Re-normalise so identical documents score 1.0 on the pruned vectors as well.
            self.body_pruned[k] = {t: w / length for t, w in top.items()}
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

    def is_compound(self, a, b, min_df=3, ratio=0.25):
        """True when syllables a b form a frequent collocation (e.g. "bộ phận", "xe điện")."""
        both = self.body.df.get(f'{a}_{b}', 0)
        if both < min_df:
            return False
        single = min(self.body.df.get(a, 0) or both, self.body.df.get(b, 0) or both)
        return both / max(1, single) >= ratio

    def centroid(self, keys):
        acc = {}
        for k in keys:
            for t, w in self.body.vectors.get(k, {}).items():
                acc[t] = acc.get(t, 0.0) + w
        length = math.sqrt(sum(w * w for w in acc.values())) or 1.0
        return {t: w / length for t, w in acc.items()}

    def duplicate_copies(self, preferred=()):
        """{copy_key: canonical_key} for published posts that repeat another post exactly
        (same body hash, or same Excel matrix_id). The publication-ledger post (``preferred``
        WordPress IDs), else the lowest ID, is treated as the original only for reporting;
        the owner decides what to keep."""
        preferred = set(preferred)
        groups = {}
        for key, r in self.records.items():
            if r['type'] != 'post':
                continue
            for g in (('sha', r.get('content_sha256')), ('matrix', r.get('matrix_id'))):
                if g[1]:
                    groups.setdefault(g, []).append(key)
        out = {}
        for members in groups.values():
            if len(members) < 2:
                continue
            ordered = sorted(members, key=lambda k: (self.records[k]['id'] not in preferred, self.records[k]['id']))
            for k in ordered[1:]:
                out.setdefault(k, ordered[0])
        return out

