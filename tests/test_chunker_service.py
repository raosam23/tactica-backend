"""
Unit tests for the chunker service.

The chunker service splits text into overlapping chunks while preserving metadata.
These tests verify:
- Basic chunking with default parameters
- Edge cases (empty text, text smaller than chunk size)
- Overlap behavior between consecutive chunks
- Metadata preservation when chunking documents
- Invalid parameter handling
"""

import pytest

from app.services.chunker_service import chunk_documents, chunk_text


class TestChunkText:
    """Tests for the chunk_text function."""

    def test_chunk_text_returns_single_chunk_when_text_fits(self):
        """Text shorter than chunk_size should return as a single chunk."""
        text = "Short text"
        result = chunk_text(text, chunk_size=100, overlap=10)

        assert len(result) == 1
        assert result[0] == "Short text"

    def test_chunk_text_returns_single_chunk_when_exactly_chunk_size(self):
        """Text exactly equal to chunk_size should return as a single chunk."""
        text = "x" * 100
        result = chunk_text(text, chunk_size=100, overlap=10)

        assert len(result) == 1
        assert result[0] == text

    def test_chunk_text_splits_long_text_into_multiple_chunks(self):
        """Text longer than chunk_size should be split into multiple chunks."""
        text = "a" * 250
        result = chunk_text(text, chunk_size=100, overlap=20)

        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 100

    def test_chunk_text_overlap_creates_overlapping_content(self):
        """Consecutive chunks should overlap by the specified amount."""
        text = "abcdefghij" * 10  # 100 characters
        chunk_size = 40
        overlap = 10

        result = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        assert len(result) >= 2
        first_chunk = result[0]
        second_chunk = result[1]
        overlap_content = first_chunk[-overlap:]
        assert second_chunk.startswith(overlap_content)

    def test_chunk_text_covers_entire_text(self):
        """All parts of the original text should appear in at least one chunk."""
        text = "The quick brown fox jumps over the lazy dog"
        result = chunk_text(text, chunk_size=15, overlap=5)

        reconstructed = result[0]
        for i in range(1, len(result)):
            non_overlapping = result[i][5:]
            reconstructed += non_overlapping

        assert text in reconstructed or reconstructed.startswith(text)

    def test_chunk_text_raises_on_invalid_chunk_size(self):
        """chunk_size must be greater than 0."""
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            chunk_text("some text", chunk_size=0, overlap=5)

        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            chunk_text("some text", chunk_size=-1, overlap=5)

    def test_chunk_text_raises_on_negative_overlap(self):
        """overlap must be non-negative."""
        with pytest.raises(ValueError, match="overlap must be >= 0"):
            chunk_text("some text", chunk_size=100, overlap=-1)

    def test_chunk_text_raises_when_overlap_equals_chunk_size(self):
        """overlap must be less than chunk_size to make progress."""
        with pytest.raises(ValueError, match="overlap must be >= 0 and < chunk_size"):
            chunk_text("some text", chunk_size=50, overlap=50)

    def test_chunk_text_raises_when_overlap_exceeds_chunk_size(self):
        """overlap must be less than chunk_size."""
        with pytest.raises(ValueError, match="overlap must be >= 0 and < chunk_size"):
            chunk_text("some text", chunk_size=50, overlap=60)

    def test_chunk_text_with_zero_overlap(self):
        """Zero overlap should produce non-overlapping chunks."""
        text = "a" * 100
        result = chunk_text(text, chunk_size=25, overlap=0)

        assert len(result) == 4
        combined = "".join(result)
        assert combined == text

    def test_chunk_text_with_real_content(self):
        """Test with realistic article content."""
        text = (
            "Lionel Messi is an Argentine professional footballer who plays as a "
            "forward for Inter Miami and captains the Argentina national team. "
            "Widely regarded as one of the greatest players of all time, Messi has "
            "won a record eight Ballon d'Or awards and a record six European Golden "
            "Shoes. He has spent most of his professional career with Barcelona."
        )

        result = chunk_text(text, chunk_size=100, overlap=20)

        assert len(result) >= 3
        assert all(len(chunk) <= 100 for chunk in result)


class TestChunkDocuments:
    """Tests for the chunk_documents function."""

    def test_chunk_documents_preserves_metadata(self, sample_documents):
        """Chunked documents should preserve source, sport, tags, and metadata_."""
        result = chunk_documents(sample_documents, chunk_size=200, chunk_overlap=30)

        assert len(result) > 0

        for chunk in result:
            assert "content" in chunk
            assert "source" in chunk
            assert "sport" in chunk
            assert "tags" in chunk
            assert "metadata_" in chunk
            assert chunk["source"] in ["wikipedia"]
            assert chunk["sport"] == "football"

    def test_chunk_documents_sets_metadata_title_and_url(self, sample_documents):
        """Each chunk's metadata_ should include the original title and URL."""
        result = chunk_documents(sample_documents, chunk_size=200, chunk_overlap=30)

        first_doc_chunks = [
            c for c in result if "Messi" in c["metadata_"].get("title", "")
        ]
        assert len(first_doc_chunks) > 0

        for chunk in first_doc_chunks:
            assert chunk["metadata_"]["title"] == "Lionel Messi"
            assert (
                chunk["metadata_"]["url"]
                == "https://en.wikipedia.org/wiki/Lionel_Messi"
            )

    def test_chunk_documents_creates_multiple_chunks_for_long_content(
        self, sample_documents
    ):
        """Long documents should be split into multiple chunks."""
        result = chunk_documents(sample_documents, chunk_size=100, chunk_overlap=20)

        messi_content = sample_documents[0]["content"]
        expected_min_chunks = len(messi_content) // 100
        messi_chunks = [c for c in result if "Messi" in c["metadata_"].get("title", "")]

        assert len(messi_chunks) >= expected_min_chunks

    def test_chunk_documents_handles_empty_list(self):
        """Empty input should return empty output."""
        result = chunk_documents([], chunk_size=100, chunk_overlap=20)
        assert result == []

    def test_chunk_documents_handles_document_with_empty_content(self):
        """Documents with empty content should be skipped."""
        docs = [
            {
                "title": "Empty Doc",
                "content": "",
                "url": "http://example.com",
                "source": "test",
                "sport": None,
                "tags": [],
            }
        ]
        result = chunk_documents(docs, chunk_size=100, chunk_overlap=20)
        assert len(result) == 1
        assert result[0]["content"] == ""

    def test_chunk_documents_handles_missing_optional_fields(self):
        """Documents missing optional fields should use defaults."""
        docs = [
            {
                "title": "Minimal Doc",
                "content": "Some content here",
                "url": "http://example.com",
                "source": "test",
            }
        ]
        result = chunk_documents(docs, chunk_size=100, chunk_overlap=20)

        assert len(result) == 1
        assert result[0]["sport"] is None
        assert result[0]["tags"] == []

    def test_chunk_documents_with_multiple_sources(self):
        """Multiple documents from different sources should all be chunked."""
        docs = [
            {
                "title": "Wiki Article",
                "content": "Wikipedia content " * 20,
                "url": "http://wikipedia.org/test",
                "source": "wikipedia",
                "sport": "basketball",
                "tags": ["wiki"],
            },
            {
                "title": "ESPN News",
                "content": "ESPN news content " * 15,
                "url": "http://espn.com/news",
                "source": "espn",
                "sport": "basketball",
                "tags": ["espn", "news"],
            },
        ]

        result = chunk_documents(docs, chunk_size=100, chunk_overlap=20)

        sources = {chunk["source"] for chunk in result}
        assert "wikipedia" in sources
        assert "espn" in sources
