"""Dependency-free BM25. Good enough for READMEs and code; no vector DB needed."""
import math
import re
from collections import Counter

_TOKEN = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for t in _TOKEN.findall(text):
        t = t.lower()
        out.append(t)
        if "_" in t:  # split snake_case into parts too
            out.extend(p for p in t.split("_") if p)
    return out


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for d, ln in zip(self.docs, self.lens):
            s = 0.0
            for t in q:
                f = d.get(t, 0)
                if f:
                    denom = f + self.k1 * (1 - self.b + self.b * ln / (self.avg or 1))
                    s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / denom
            out.append(s)
        return out
