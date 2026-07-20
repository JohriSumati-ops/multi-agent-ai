"""
tests/test_text_cleaning.py
"""

from __future__ import annotations

from document_processing.text_cleaner import (
    clean_text,
    collapse_empty_lines,
    normalize_unicode,
    normalize_whitespace,
    remove_page_number_lines,
    remove_repeated_lines,
)


def test_normalize_whitespace_collapses_runs_and_trims() -> None:
    text = "This   has    extra\t\tspaces  \nand a  second   line "
    result = normalize_whitespace(text)
    assert result == "This has extra spaces\nand a second line"


def test_normalize_unicode_canonicalizes_ligatures() -> None:
    # "ﬁ" (U+FB01, LATIN SMALL LIGATURE FI) should normalize to "fi"
    text = "the ﬁrst example"
    result = normalize_unicode(text)
    assert "\ufb01" not in result
    assert "first" in result


def test_remove_page_number_lines_strips_bare_numbers() -> None:
    text = "Some content\n4\nMore content\n- 5 -\nEven more"
    result = remove_page_number_lines(text)
    assert "4" not in result.split("\n")
    assert "- 5 -" not in result.split("\n")
    assert "Some content" in result
    assert "More content" in result


def test_remove_page_number_lines_keeps_numbers_within_sentences() -> None:
    text = "There are 4 types of traversal."
    result = remove_page_number_lines(text)
    assert result == text


def test_collapse_empty_lines_reduces_to_single_paragraph_break() -> None:
    text = "Paragraph one.\n\n\n\n\nParagraph two."
    result = collapse_empty_lines(text)
    assert result == "Paragraph one.\n\nParagraph two."


def test_remove_repeated_lines_strips_running_header() -> None:
    pages = [
        "Chapter 1: Trees\nContent about trees on page 1.",
        "Chapter 1: Trees\nContent about trees on page 2.",
        "Chapter 1: Trees\nContent about trees on page 3.",
        "Chapter 1: Trees\nContent about trees on page 4.",
    ]
    cleaned_pages = remove_repeated_lines(pages)
    for page in cleaned_pages:
        assert "Chapter 1: Trees" not in page
    assert "Content about trees on page 1." in cleaned_pages[0]


def test_remove_repeated_lines_leaves_short_documents_untouched() -> None:
    pages = ["Shared line\nUnique content one.", "Shared line\nUnique content two."]
    result = remove_repeated_lines(pages)
    assert result == pages  # fewer than 3 pages -> no removal, per docstring


def test_clean_text_full_pipeline() -> None:
    raw = "  Messy   text.  \n\n\n\n4\n\nMore content here.  "
    result = clean_text(raw)
    assert "\n\n\n" not in result
    assert result.strip() == result
