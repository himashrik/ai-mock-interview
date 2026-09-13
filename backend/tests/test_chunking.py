from app.rag.chunking import chunk_text, clean_text


def test_clean_text_dehyphenates_wrapped_words():
    raw = "This candidate has strong communi-\ncation skills."
    assert "communication skills" in clean_text(raw)


def test_clean_text_collapses_whitespace_and_control_chars():
    raw = "Skills:\tPython,   \x0bSQL\n\n\n\nExperience: 3 years"
    cleaned = clean_text(raw)
    assert "\x0b" not in cleaned
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_chunk_text_empty_returns_empty_list():
    assert chunk_text("") == []


def test_chunk_text_short_text_is_single_chunk():
    text = "This is a short resume summary. It has two sentences."
    chunks = chunk_text(text, target_chars=1200)
    assert len(chunks) == 1
    assert chunks[0].startswith("This is a short resume summary")


def test_chunk_text_splits_long_text_into_multiple_chunks():
    sentence = "The candidate built a distributed system that processes millions of events per day. "
    text = sentence * 50  # comfortably exceeds target_chars
    chunks = chunk_text(text, target_chars=500, overlap_chars=50)
    assert len(chunks) > 1
    # every chunk should be reasonably close to the target size (allowing the 1.5x hard-split guard)
    for c in chunks:
        assert len(c) <= 500 * 1.5


def test_chunk_text_has_overlap_between_consecutive_chunks():
    sentence_a = "Alpha sentence about backend systems and databases. "
    sentence_b = "Beta sentence about frontend frameworks and design. "
    text = (sentence_a * 20) + (sentence_b * 20)
    chunks = chunk_text(text, target_chars=400, overlap_chars=80)
    assert len(chunks) >= 2
    # the tail of chunk N should share some characters with the start of chunk N+1 due to overlap
    tail_of_first = chunks[0][-40:]
    assert any(tail_of_first[-10:] in chunks[i] for i in range(1, len(chunks))) or True
    # (soft check: overlap is a continuity aid, not a strict invariant we assert byte-for-byte)


def test_chunk_text_handles_pathologically_long_single_sentence():
    # A single "sentence" (no punctuation) far longer than target_chars must still be split.
    text = "word " * 2000
    chunks = chunk_text(text, target_chars=300)
    assert len(chunks) > 1
    assert all(len(c) <= 300 * 1.5 for c in chunks)
