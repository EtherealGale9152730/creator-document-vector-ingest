from creator_ingest import chunk_text


def test_chunk_text_preserves_order_and_bounds():
    chunks = chunk_text("one two three four five", size=2)
    assert chunks == ["one two", "three four", "five"]
