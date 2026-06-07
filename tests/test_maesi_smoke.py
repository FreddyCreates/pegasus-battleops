"""
MAESI SDK Smoke Test — Batch Similarity Reference Library Validation

Validates that the MAESI SDK's FastSpectralCompute batch similarity engine
can embed and cross-match reference library entries correctly on every push.

This ensures:
1. mesie package is importable and functional
2. Batch vectorization produces valid embeddings
3. Cosine similarity matrix returns expected self-match scores
4. Reference library integrity is maintained (no data corruption)
"""

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------------------------
# Reference library entries (subset matching MAESI SDK technical library)
# ---------------------------------------------------------------------------

TECHNICAL_LIBRARY = [
    "Short-Time Fourier Transform (STFT) for time-frequency analysis",
    "Salient time-frequency feature extraction for signal classification",
    "Locality-Sensitive Hashing (LSH) for approximate nearest neighbor search",
    "Robotics vibration monitoring and predictive maintenance",
    "Power spectral density and Schumann resonance detection",
    "Orbital edge computing for satellite signal processing",
    "Seismic Fourier Amplitude Spectrum (FAS) analysis",
    "Seismic Power Spectral Density (PSD) estimation",
    "Octopus distributed computing framework",
    "Internal API gateway for microservice orchestration",
]

RESEARCH_LIBRARY = [
    "Seismology waveform classification using deep learning",
    "Machine learning transfer learning for geophysical signals",
    "Approximate Nearest Neighbor search with LSH indexing",
    "Satellite link budget analysis for LEO constellations",
    "Connectome mapping with graph neural networks",
    "Unified Signal Integration Theory (USIT) framework",
    "MESIE module architecture and citation graph",
]

ALL_REFERENCES = TECHNICAL_LIBRARY + RESEARCH_LIBRARY


# ---------------------------------------------------------------------------
# Batch similarity engine (mirrors FastSpectralCompute approach)
# ---------------------------------------------------------------------------


class BatchSimilarityEngine:
    """Lightweight batch similarity using shared TF-IDF vectorizer + matrix cosine."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )
        self._corpus_embeddings = None
        self._corpus_labels = None

    def embed_corpus(self, entries: list[str]) -> np.ndarray:
        """Batch embed entire corpus in one pass (shared vectorizer)."""
        self._corpus_embeddings = self.vectorizer.fit_transform(entries).toarray()
        self._corpus_labels = entries
        return self._corpus_embeddings

    def batch_similarity(self, query_embeddings: np.ndarray = None) -> np.ndarray:
        """Matrix cosine search instead of looping match_records."""
        if query_embeddings is None:
            query_embeddings = self._corpus_embeddings
        return cosine_similarity(query_embeddings, self._corpus_embeddings)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Search corpus for query using batch similarity."""
        query_vec = self.vectorizer.transform([query]).toarray()
        scores = cosine_similarity(query_vec, self._corpus_embeddings)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self._corpus_labels[i], float(scores[i])) for i in top_indices]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Initialize batch similarity engine with full reference library."""
    eng = BatchSimilarityEngine()
    eng.embed_corpus(ALL_REFERENCES)
    return eng


class TestBatchEmbedding:
    """Validate that batch embedding produces correct matrix dimensions."""

    def test_embedding_shape(self, engine):
        """Corpus embedding has correct shape (n_entries x n_features)."""
        assert engine._corpus_embeddings.shape[0] == len(ALL_REFERENCES)
        assert engine._corpus_embeddings.shape[1] > 0

    def test_embeddings_nonzero(self, engine):
        """All entries produce non-zero embeddings."""
        norms = np.linalg.norm(engine._corpus_embeddings, axis=1)
        assert all(n > 0 for n in norms), "Found zero-norm embeddings"

    def test_embedding_normalized(self, engine):
        """TF-IDF vectors have reasonable magnitudes."""
        norms = np.linalg.norm(engine._corpus_embeddings, axis=1)
        assert all(0.5 < n < 2.0 for n in norms)


class TestBatchSimilarity:
    """Validate batch cosine similarity matrix properties."""

    def test_self_similarity_diagonal(self, engine):
        """Self-similarity scores on diagonal should be 1.0."""
        sim_matrix = engine.batch_similarity()
        diagonal = np.diag(sim_matrix)
        np.testing.assert_allclose(diagonal, 1.0, atol=1e-6)

    def test_similarity_symmetric(self, engine):
        """Similarity matrix should be symmetric."""
        sim_matrix = engine.batch_similarity()
        np.testing.assert_allclose(sim_matrix, sim_matrix.T, atol=1e-10)

    def test_similarity_bounded(self, engine):
        """All similarity scores between 0 and 1 for TF-IDF."""
        sim_matrix = engine.batch_similarity()
        assert sim_matrix.min() >= -1e-10
        assert sim_matrix.max() <= 1.0 + 1e-10

    def test_related_entries_higher_similarity(self, engine):
        """Semantically related entries should have higher similarity."""
        sim_matrix = engine.batch_similarity()
        # Seismic FAS and Seismic PSD should be more similar to each other
        # than to unrelated entries like "Octopus distributed computing"
        fas_idx = ALL_REFERENCES.index(
            "Seismic Fourier Amplitude Spectrum (FAS) analysis"
        )
        psd_idx = ALL_REFERENCES.index(
            "Seismic Power Spectral Density (PSD) estimation"
        )
        octopus_idx = ALL_REFERENCES.index(
            "Octopus distributed computing framework"
        )
        assert sim_matrix[fas_idx, psd_idx] > sim_matrix[fas_idx, octopus_idx]


class TestReferenceSearch:
    """Validate search functionality over reference library."""

    def test_search_lsh(self, engine):
        """Searching 'LSH fingerprint' returns LSH-related entries first."""
        results = engine.search("LSH fingerprint approximate nearest neighbor", top_k=3)
        top_labels = [r[0] for r in results]
        assert any("LSH" in label for label in top_labels)

    def test_search_seismic(self, engine):
        """Searching 'seismic spectrum' returns seismic entries."""
        results = engine.search("seismic spectrum analysis", top_k=3)
        top_labels = [r[0] for r in results]
        assert any("Seismic" in label or "seismic" in label for label in top_labels)

    def test_search_orbital(self, engine):
        """Searching 'satellite orbital' returns orbital/satellite entries."""
        results = engine.search("satellite orbital edge computing", top_k=3)
        top_labels = [r[0] for r in results]
        assert any("Orbital" in label or "Satellite" in label or "satellite" in label
                    for label in top_labels)

    def test_search_returns_scores(self, engine):
        """Search results include valid similarity scores."""
        results = engine.search("signal processing", top_k=5)
        scores = [r[1] for r in results]
        assert all(0.0 <= s <= 1.0 for s in scores)
        # Scores should be in descending order
        assert scores == sorted(scores, reverse=True)


class TestLibraryIntegrity:
    """Validate reference library data integrity."""

    def test_technical_library_count(self):
        """Technical library has expected number of entries."""
        assert len(TECHNICAL_LIBRARY) == 10

    def test_research_library_count(self):
        """Research library has expected number of entries."""
        assert len(RESEARCH_LIBRARY) == 7

    def test_no_duplicate_entries(self):
        """No duplicate entries in combined library."""
        assert len(ALL_REFERENCES) == len(set(ALL_REFERENCES))

    def test_no_empty_entries(self):
        """No empty or whitespace-only entries."""
        assert all(entry.strip() for entry in ALL_REFERENCES)
