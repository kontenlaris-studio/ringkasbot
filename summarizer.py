"""Extractive text summarizer — deterministic, offline, no AI API key needed.

Scores sentences by word frequency (with stopword filtering for English and
Indonesian), picks the top N, and returns them in original order.
"""
import re
from collections import Counter

STOP = set("""the a an and or but if then else of at by for with about into through after over
between out against during without before under around among is are was were be been being have
has had do does did will would shall should can could may might must i you he she it we they them
his her its our their this that these those am an the dan yang di ke dari untuk dengan pada adalah
ini itu atau tidak dalam akan juga sudah saya anda kita mereka oleh sebagai dapat lebih sangat
ada bila jadi karena ketika hingga antara lain saat telah bagi para ya pun""".split())

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"[a-zA-ZÀ-ÿ']+")


def summarize(text: str, max_sentences: int = 5) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [s.strip() for s in SENT_SPLIT.split(text) if len(s.strip()) > 25]
    if len(sentences) <= max_sentences:
        return text
    freq = Counter(w.lower() for w in WORD.findall(text) if w.lower() not in STOP and len(w) > 2)
    if not freq:
        return " ".join(sentences[:max_sentences])
    top = max(freq.values())
    scored = []
    for i, s in enumerate(sentences):
        words = [w.lower() for w in WORD.findall(s)]
        score = sum(freq[w] / top for w in words if w in freq) / (len(words) ** 0.6 or 1)
        scored.append((score, i, s))
    chosen = sorted(sorted(scored, reverse=True)[:max_sentences], key=lambda x: x[1])
    return " ".join(s for _, _, s in chosen)


def looks_like_url(s: str) -> bool:
    return bool(re.match(r"^https?://\S+$", s.strip()))
