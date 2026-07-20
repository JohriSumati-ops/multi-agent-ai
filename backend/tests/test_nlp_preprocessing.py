"""
tests/test_nlp_preprocessing.py
"""

from __future__ import annotations

from document_processing.nlp_preprocessor import (
    compute_statistics,
    count_characters,
    count_words,
    detect_language,
    estimate_reading_time_minutes,
    segment_paragraphs,
    segment_sentences,
)

SAMPLE_EN_TEXT = (
    "A tree is a hierarchical data structure. It consists of nodes connected by edges. "
    "Each node has a parent, except the root node, which has no parent at all."
)


def test_segment_sentences_splits_on_real_boundaries() -> None:
    sentences = segment_sentences(SAMPLE_EN_TEXT)
    assert len(sentences) == 3
    assert sentences[0].startswith("A tree is a hierarchical")


def test_segment_sentences_does_not_split_on_abbreviations() -> None:
    text = "Dr. Smith wrote the textbook. It covers e.g. trees and graphs."
    sentences = segment_sentences(text)
    # A naive split on "." would produce 4+ fragments; pysbd should not
    # split after "Dr." or "e.g."
    assert len(sentences) == 2


def test_segment_paragraphs_splits_on_blank_lines() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    paragraphs = segment_paragraphs(text)
    assert paragraphs == ["First paragraph.", "Second paragraph.", "Third paragraph."]


def test_count_words_ignores_punctuation() -> None:
    assert count_words("Hello, world! This is a test.") == 6


def test_count_characters_is_exact_length() -> None:
    assert count_characters("hello") == 5


def test_estimate_reading_time_scales_with_word_count() -> None:
    assert estimate_reading_time_minutes(0) == 0.0
    assert estimate_reading_time_minutes(225) == 1.0
    assert estimate_reading_time_minutes(450) == 2.0


def test_detect_language_identifies_english() -> None:
    result = detect_language(SAMPLE_EN_TEXT)
    assert result == "en"


def test_detect_language_returns_none_for_short_text() -> None:
    assert detect_language("hi") is None


def test_compute_statistics_bundles_everything_consistently() -> None:
    stats = compute_statistics(SAMPLE_EN_TEXT)
    assert stats.word_count == count_words(SAMPLE_EN_TEXT)
    assert stats.char_count == len(SAMPLE_EN_TEXT)
    assert stats.sentence_count == 3
    assert stats.language == "en"
    assert stats.reading_time_minutes >= 0.0
