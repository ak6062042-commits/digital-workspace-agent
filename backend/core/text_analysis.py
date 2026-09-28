"""Small, deterministic text-analysis helpers for local research and writing workflows."""
from __future__ import annotations

import re
from collections import Counter


_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]{2,}")
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "being", "between", "could", "does",
    "from", "have", "into", "more", "most", "not", "only", "other", "over", "should", "some", "such", "than",
    "that", "their", "there", "these", "they", "this", "those", "through", "using", "very", "what", "when", "where",
    "which", "with", "would", "your", "will", "were", "while", "whose", "them", "then", "than", "have", "has",
    "had", "our", "out", "into", "its", "you", "for", "the", "and", "but", "are", "was", "were", "can", "may",
}


def normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str, minimum_length: int = 24) -> list[str]:
    return [
        sentence.strip()
        for sentence in _SENTENCE_PATTERN.split(normalise_text(text))
        if len(sentence.strip()) >= minimum_length
    ]


def extract_keywords(text: str, maximum: int = 8) -> list[str]:
    words = [word.lower() for word in _WORD_PATTERN.findall(text or "")]
    counts = Counter(word for word in words if word not in _STOPWORDS)
    return [word for word, _count in counts.most_common(max(1, maximum))]


def rank_sentences(text: str, maximum: int = 5) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []
    if len(sentences) <= maximum:
        return sentences

    frequencies = Counter(
        word.lower()
        for sentence in sentences
        for word in _WORD_PATTERN.findall(sentence)
        if word.lower() not in _STOPWORDS
    )
    if not frequencies:
        return sentences[:maximum]

    scored = []
    for index, sentence in enumerate(sentences):
        words = [word.lower() for word in _WORD_PATTERN.findall(sentence) if word.lower() not in _STOPWORDS]
        score = sum(frequencies[word] for word in words) / max(1, len(words))
        scored.append((score, index, sentence))
    selected = sorted(sorted(scored, key=lambda item: (-item[0], item[1]))[:maximum], key=lambda item: item[1])
    return [sentence for _score, _index, sentence in selected]


def summarize_text(text: str, maximum_sentences: int = 4, maximum_characters: int = 1400) -> str:
    selected = rank_sentences(text, maximum_sentences)
    if not selected:
        return "No readable content was available to summarize."
    summary = " ".join(selected)
    if len(summary) <= maximum_characters:
        return summary
    return summary[: maximum_characters - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def key_takeaways(text: str, maximum: int = 5, maximum_characters: int = 360) -> list[str]:
    takeaways = []
    for sentence in rank_sentences(text, maximum):
        if len(sentence) > maximum_characters:
            sentence = sentence[: maximum_characters - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
        if sentence not in takeaways:
            takeaways.append(sentence)
    return takeaways
