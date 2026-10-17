"""Vietnamese-aware text utilities: normalization, features, TF-IDF, shingles, similarity.

Vietnamese words are often two or more syllables, so features are syllable unigrams plus
bigrams; IDF weighting removes site-wide boilerplate such as "xe máy" automatically.
"""
from collections import Counter, defaultdict
import hashlib
import math
import re
import unicodedata

TYPOGRAPHIC = str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'",
                             '–': '-', '—': '-', '…': '...', ' ': ' '})

# Function words and very generic syllables. Topic words are deliberately NOT listed.
STOPWORDS = set('''
và của là có cho khi với các những một được để trong này không nên thì đến từ theo hay hoặc như
nào gì bạn người cũng đã sẽ đang rất nhiều ít hơn nhất vì nếu mà thế làm ra vào lên xuống lại
còn chỉ đều vẫn phải cần nhưng tuy do bởi về sau trước trên dưới giữa ở tại qua bằng thể
cách việc điều mình họ chúng ta tôi anh chị em ai đâu sao bao nhiêu thường luôn mỗi mọi
các nhé nha ạ đó đây kia vậy rằng thì là lúc khá hết đủ quá cùng nữa vừa mới chưa hãy
the a an of to and or in on for with is are be by at from as it this that
'''.split())

WORD = re.compile(r'\w+', re.UNICODE)


def norm(text):
    text = unicodedata.normalize('NFC', text or '').translate(TYPOGRAPHIC)
    return ' '.join(text.casefold().split())


def ascii_fold(text):
    text = unicodedata.normalize('NFKD', norm(text).replace('đ', 'd'))
    return ''.join(ch for ch in text if not unicodedata.combining(ch))


def syllables(text):
    return WORD.findall(norm(text))


def word_count(text):
    return len(syllables(text))


def content_terms(text):
    return [s for s in syllables(text) if s not in STOPWORDS and not s.isdigit() and len(s) > 1]


def features(text, bigrams=True):
    toks = syllables(text)
    feats = Counter(t for t in toks if t not in STOPWORDS and not t.isdigit() and len(t) > 1)
    if bigrams:
        for a, b in zip(toks, toks[1:]):
            if a in STOPWORDS and b in STOPWORDS:
                continue
            if a.isdigit() and b.isdigit():
                continue
            feats[a + '_' + b] += 1
    return feats


class TfIdf:
    """Sparse, L2-normalised TF-IDF vectors keyed by document id."""

    def __init__(self, docs, prune=None, min_df=1):
        self.n = len(docs)
        df = Counter()
        for counts in docs.values():
            df.update(counts.keys())
        self.df = dict(df)
        self.idf = {t: math.log((1 + self.n) / (1 + d)) + 1 for t, d in df.items() if d >= min_df}
        self.vectors = {}
        for key, counts in docs.items():
            vec = {t: (1 + math.log(c)) * self.idf[t] for t, c in counts.items() if t in self.idf}
            if prune and len(vec) > prune:
                vec = dict(sorted(vec.items(), key=lambda kv: kv[1], reverse=True)[:prune])
            length = math.sqrt(sum(w * w for w in vec.values())) or 1.0
            self.vectors[key] = {t: w / length for t, w in vec.items()}

    def top_terms(self, key, k=10):
        vec = self.vectors.get(key, {})
        return [t for t, _ in sorted(vec.items(), key=lambda kv: kv[1], reverse=True)[:k]]


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def candidate_pairs(vectors, min_score):
    """All pairs whose (pruned-vector) cosine >= min_score, via an inverted index."""
    postings = defaultdict(list)
    for key, vec in vectors.items():
        for term, weight in vec.items():
            postings[term].append((key, weight))
    scores = defaultdict(float)
    cap = max(50, len(vectors) // 2)
    for items in postings.values():
        # Terms shared by most documents carry tiny weights; skipping them bounds runtime.
        if len(items) < 2 or len(items) > cap:
            continue
        for i in range(len(items)):
            ki, wi = items[i]
            for j in range(i + 1, len(items)):
                kj, wj = items[j]
                pair = (ki, kj) if str(ki) < str(kj) else (kj, ki)
                scores[pair] += wi * wj
    return {pair: s for pair, s in scores.items() if s >= min_score}


def shingles(text, k=5):
    toks = syllables(text)
    out = set()
    for i in range(max(0, len(toks) - k + 1)):
        digest = hashlib.blake2b(' '.join(toks[i:i + k]).encode(), digest_size=8).digest()
        out.add(int.from_bytes(digest, 'big'))
    return out


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def sha256(text):
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


SENTENCE_SPLIT = re.compile(r'(?<=[.!?;:])\s+')


def sentences(text):
    return [s.strip() for s in SENTENCE_SPLIT.split(text or '') if s.strip()]
