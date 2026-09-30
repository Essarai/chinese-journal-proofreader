# DOCX native-comment workflow

Use this workflow for native comments. For the default direct-edit deliverable, first read `word-edit-output.md` for edits, colors, ledger fields, and final-text anchors. The JSON below is the comment-insertion payload, not the complete edit ledger.

## Before editing

1. Load the bundled workspace document dependencies.
2. Follow the `documents` skill's required operation marker exactly once before the first artifact edit.
3. Copy the user file into an isolated working directory. Never overwrite the original.
4. Inspect both the logical document and its OOXML package:
   - paragraphs and style names;
   - tables and cell text;
   - footnotes/endnotes;
   - headers/footers, sections, fields, hyperlinks, drawings;
   - tracked changes and existing comments.
5. Extract text for review, but retain paragraph or cell anchors that can be matched back to the DOCX.

## Build the issue ledger

Record each issue as:

```json
{
  "anchor": "a unique substring used only to locate the paragraph or cell",
  "target": "the exact smallest text range that should be highlighted",
  "comment": "【待核实｜引文·页码】Explain the conflict, source to check, and action after verification.",
  "occurrence": 1
}
```

- Use a unique, stable `anchor`; it is a locator and must not determine the highlighted range.
- Set `target` to the smallest useful range: one character, word, citation, number, phrase, or sentence.
- Use `occurrence` only when the same target appears more than once in the located paragraph or cell.
- Separate unrelated issues in the same paragraph so that each comment points to its own target.
- A paragraph-wide target is allowed only when the entire paragraph needs replacement or a paragraph-level structural query.
- Check that every anchor matches before producing the reviewed file.
- If an issue occurs in a footnote but the available helper cannot anchor comments in footnotes, anchor the comment to the corresponding footnote reference paragraph and say which note it concerns.

## Add comments

- `scripts/add_precise_comments.py` only adds minimum-range native Word comments. If using it after direct edits, resolve anchors and targets against the edited file; it does not apply corrections or colors. Do not use a paragraph-only helper when the issue is a smaller text span.
- Do not simulate comments with highlighted body text, text boxes, or appended review tables.
- Keep the original visible text unchanged in comment-only mode.
- Preserve existing comments and tracked changes unless the user explicitly asks to remove or resolve them.
- Use a clear review author such as `Codex审校`.

## Structural verification

1. Extract comments and confirm the expected count and readable text.
2. In comment-only mode run `scripts/verify_commented_docx.py`. For direct edits, use the ledger-based verification in `word-edit-output.md`; the existing helper assumes unchanged text.
3. Test ZIP/package integrity.
4. Confirm each comment ID has a range start, range end, and reference.
5. Confirm visible text matches the source plus exactly the ledger changes; preserve unrelated tables, notes, and all existing tracked changes. In comment-only mode require all visible text to match the source.
6. Extract anchored text and confirm that every range equals its ledger `target`, not the containing paragraph.

## Visual verification

1. Render the reviewed DOCX using the `documents` skill and compare page count and key pages with the source.
2. Inspect the first page, table-heavy pages, references, English title/abstract pages, and the last page.
3. Native Word comments often do not appear in PDF output, so rendering does not replace structural comment verification.
4. If the renderer lacks the manuscript's fonts, open the reviewed copy in Microsoft Word and verify:
   - Chinese glyphs and line breaks;
   - tables and footnotes;
   - comment balloons and long comment text;
   - the final English pages.

## Delivery

- Put only the final reviewed DOCX in the output folder unless the user requested other artifacts.
- Use a descriptive filename ending in `审校修改批注版.docx` (or `审校批注版.docx` in comment-only mode) or the user's preferred naming convention.
- Report the comment count, review coverage, structural checks, and any visual-QA limitation.
