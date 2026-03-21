# Edit File Tool Display - Highlight Color Issue

## Problem
When displaying edit file diffs, the highlight color (red/green background) does not fill the entire row when lines wrap. The highlighting stops at the last word when a wrap occurs.

## Root Cause
In `src/tools/helpers/formatters.py`, the `_colorize_numbered_lines()` function uses `ljust()` to pad lines:

```python
padded = line.ljust(terminal_width)
result.append(padded, style="on #870101")
```

Rich's text rendering doesn't apply background color to trailing whitespace - spaces at the end of a line are invisible and don't contribute to visual width. When a line wraps:
1. The visible content stops before `terminal_width`
2. The padding spaces don't get rendered with the background color
3. The highlight stops at the last visible word instead of extending to the edge

## Proposed Solution: Character-Based Padding with Newline Styling

### Implementation
```python
def _colorize_numbered_lines(lines, file_path=None):
    """Apply color highlighting to diff lines."""
    try:
        terminal_width = os.get_terminal_size().columns
    except (OSError, AttributeError):
        terminal_width = DEFAULT_TERMINAL_WIDTH

    result = Text()
    for line in lines:
        if len(line) >= 7:
            sign = line[6]

            if sign == "-":
                result.append(line)
                # Add visible spacer to extend background
                spacer_count = terminal_width - len(line)
                if spacer_count > 0:
                    result.append(" " * spacer_count, style="on #870101")
                result.append("\n", style="on #870101")
            elif sign == "+":
                result.append(line)
                spacer_count = terminal_width - len(line)
                if spacer_count > 0:
                    result.append(" " * spacer_count, style="on #005f00")
                result.append("\n", style="on #005f00")
            else:
                result.append(line, style="dim")
                result.append("\n")
        else:
            result.append(line)
            result.append("\n")

    return result
```

### Key Changes
- Append the line first, then separately append the padding spaces **with the background style**
- Append the newline **with the background style** too (ensures wrap gets colored)
- Don't use `ljust()` on the whole line - manually add styled spaces
- Each segment (content + spaces + newline) has explicit background style

## Potential Pitfalls

### Critical Concerns

#### 1. Character Width vs Visual Width
`len(line)` counts characters, but visual width differs:
- **Tabs** - Expand to 4-8 spaces visually but count as 1 character
- **CJK characters** - Chinese, Japanese, Korean are double-width visually
- **Emoji** - Can be 1-2 characters wide
- **Impact** - Causes under-padding, background stops early

**Possible fix:** Use `rich.console.measure_text()` or manually expand tabs before measuring.

#### 2. Newline Styling Might Not Work
Applying `style="on #870101"` to `\n` is speculative:
- Newline is a control character, not visible
- Rich might ignore styles on control characters
- Even if styled, it may not affect wrapped line rendering
- **This could be the whole problem - the style on `\n` might not propagate**

**Research needed:** Test whether styling a `\n` actually causes wrapped lines to inherit background color.

#### 3. Rich's Internal Rendering
When Rich wraps lines, it might:
- Strip trailing whitespace before wrapping
- Not inherit background color from previous segment
- Reset styles at line breaks

**Alternative approach:** Use a visible Unicode space character that Rich definitely renders with background:
- `\u00A0` - Non-breaking space (NBSP)
- `\u2003` - Em space
- `\u2007` - Figure space

### Secondary Concerns

#### 4. Negative spacer_count
Handled with `if spacer_count > 0`, but long lines (> terminal_width) have no padding at all.

**Impact:** Lines that exceed terminal width won't have any background color extension beyond their content.

#### 5. Performance
3 appends per highlighted line.

**Impact:** Negligible for typical diffs (20-100 lines).

## Alternative Solutions Considered

### Panel-Based Approach (Rejected)
- Wrap each colored line in a Panel with full width
- **Issues:**
  - Borders require `box=None`
  - Padding requires `padding=0`
  - Per-line Panel overhead
  - Visual gaps possible with stacked panels

### Single Panel with Styled Content (Not Implemented)
- Put entire diff in one Panel
- Use Rich's `Style` for line-by-line background colors
- **Pros:** Cleaner rendering, uses existing Rich infrastructure
- **Cons:** Still using Panel, though only one

## Next Steps

1. **Research Rich line wrapping behavior** - Verify if styling `\n` affects wrapped lines
2. **Test Unicode space characters** - Determine if `\u00A0` or `\u2003` extend background color properly
3. **Handle tab expansion** - Convert tabs to spaces before measuring line width
4. **Implement and test** - Apply fix and verify highlight extends full width on wrapped lines

## File Location
`src/tools/helpers/formatters.py` - Function `_colorize_numbered_lines()` (lines ~35-66)
