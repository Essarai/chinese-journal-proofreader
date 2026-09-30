# Token-efficient comprehensive-review orchestration

Use this protocol for one manuscript when the user requests a comprehensive or full review. Preserve full coverage without creating a separate model context for every capability.

## Default execution shape

Use **one primary review context plus at most one optional verification context**.

- The primary context owns the manuscript, target-journal information, review decisions, issue ledger, deduplication, and final comment text.
- Keep Chinese grammar and wording, typography and terminology, structure and local argument, tables/figures/notes, and Chinese-English alignment in the primary context. These tasks depend on the same manuscript context and should not receive duplicate full-text inputs.
- Run those tasks as sequential attention passes. A new pass is a change of review focus inside the same context, not a new agent or execution.
- DOCX inventory, extraction, comment insertion, package validation, and rendering are tooling stages. Do not start a new model context for them.

## Primary-context passes

Extract the manuscript once with stable paragraph and table-cell locators, then use the same extraction for these passes:

1. Chinese grammar, wording, typography, terminology, numbers, and units.
2. Title-to-conclusion consistency, argument relationships, internal references, tables, figures, notes, captions, and appendices.
3. Chinese-English title, abstract, and keyword alignment plus academic-English corrections where applicable.
4. Candidate selection for citations, bibliographic fields, journal rules, laws, policies, standards, dates, and other claims that may require external verification.

Append findings to one on-disk issue ledger after each pass. Reread only the local paragraph, neighboring text, or relevant manuscript section needed to challenge a candidate; do not repeatedly inject the complete extraction.

## External-verification routing

Keep verification in the primary context when it is compact and its evidence can be summarized without crowding out manuscript review. Use one isolated verification context only when source-by-source browsing, many bibliographic records, or large raw tool results would materially dilute the primary review context.

When isolation is warranted:

- send a verification packet, not the full manuscript;
- include only the claim or reference, its exact manuscript wording, a short necessary excerpt, locator, requested fields, target-journal requirement if relevant, and the evidence standard;
- let the verifier use `nature-ref-verifier` and current primary or official sources as needed;
- require compact structured results containing locator, status, verified fields, conflict or unresolved field, source, and proposed comment;
- keep unresolved items explicitly unresolved rather than returning invented certainty;
- do not let the verifier edit the DOCX or independently rewrite unrelated manuscript text.

The primary context merges verifier results into the existing issue ledger, resolves duplicates or conflicts, and owns the final wording. Do not create a third context just for aggregation.

## When not to split

Do not create the optional verification context merely because the manuscript contains references, English text, tables, or policy terms. Keep the entire review in the primary context when the manuscript and required verification are compact, or when the user did not request external verification and no consequential factual conflict requires it.

## Completion check

Before writing comments, confirm that:

- every applicable checklist domain was covered in the primary context;
- only evidence-heavy work, if any, was isolated;
- the verification context did not receive the full manuscript;
- all findings now exist in one deduplicated issue ledger;
- final DOCX creation and verification will reuse that ledger without another model review pass.
