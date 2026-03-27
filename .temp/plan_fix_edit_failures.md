# Plan: Fix Edit Tool Failures — Blank Line Annotation & Encoding Asymmetry

## Problem

The edit_file tool fails intermittently, primarily due to two issues:

1. **read_file adds fake content** via `_annotate_blank_lines()` — the LLM receives transformed output that doesn't match the actual file, causing edit search text mismatches
2. **Encoding error handling is inconsistent** — read_file uses `errors="replace"`, edit_file uses `errors="strict"`, so files with non-UTF-8 bytes can be read but not edited

## Changes

### 1. Remove `_annotate_blank_lines` from read_file

**File:** `src/tools/helpers/formatters.py`

- Remove the `_annotate_blank_lines()` function (lines 311–343)
- In `format_file_result()`, pass `content` directly instead of calling `_annotate_blank_lines(content)`

**Rationale:** The LLM can count blank lines and see whitespace in raw output. The annotation adds lines that don't exist in the file (`# (3 blank lines)`, `# (trailing whitespace: ····)`), forcing the LLM to reverse-engineer the original content. This is the #1 source of edit_file search text mismatches.

### 2. Align encoding error handling

**File:** `src/tools/edit.py`

- In `_prepare_edit()`, change `file_path.open("r", encoding="utf-8", newline="")` to `file_path.open("r", encoding="utf-8", errors="replace", newline="")` (line ~296)

**Rationale:** read_file already uses `errors="replace"`. Without this alignment, the LLM reads a file with replaced characters, builds search text from that output, then edit crashes on the same file with a UnicodeDecodeError.

## Files Modified

| File | Change |
|------|--------|
| `src/tools/helpers/formatters.py` | Remove `_annotate_blank_lines()`; pass raw content in `format_file_result()` |
| `src/tools/edit.py` | Add `errors="replace"` to file open in `_prepare_edit()` |
