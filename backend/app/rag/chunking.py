import re

_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_HYPHEN_LINEBREAK_RE = re.compile(r"(\w)-\n(\w)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def clean_text(raw: str) -> str:
    """Strip control chars, de-hyphenate wrapped words, collapse whitespace."""
    text = _CONTROL_CHARS_RE.sub("", raw)
    text = _HYPHEN_LINEBREAK_RE.sub(r"\1\2", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def chunk_text(text: str, target_chars: int = 1200, overlap_chars: int = 180) -> list[str]:
    """Sentence-aware recursive splitter.

    Approximates ~250-400 tokens per chunk using a character-length proxy
    (roughly 4 chars/token in English), with overlap so context isn't lost
    at chunk boundaries.
    """
    if not text:
        return []

    sentences = _SENTENCE_SPLIT_RE.split(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= target_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk, carrying over a tail of the previous chunk for continuity
            overlap = current[-overlap_chars:] if current else ""
            current = f"{overlap} {sentence}".strip()

    if current:
        chunks.append(current)

    # Guard against pathological single-sentence-too-long chunks
    final_chunks: list[str] = []
    for c in chunks:
        if len(c) <= target_chars * 1.5:
            final_chunks.append(c)
        else:
            for i in range(0, len(c), target_chars):
                final_chunks.append(c[i : i + target_chars])

    return final_chunks
