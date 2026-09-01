# Isolated full-depth batch protocol

Use this protocol whenever the request contains two or more manuscripts. Its purpose is to keep batch results at the same review depth as a standalone single-manuscript run.

## Non-negotiable execution model

- Set maximum concurrency to **2**.
- Create **one isolated worker execution per manuscript**. Each worker loads this skill and receives one source DOCX only; do not give one worker two manuscripts to review in the same context.
- Partition manuscripts into ordered waves of at most two. Start the next wave only after every worker in the current wave has completed its review and verification.
- For ten manuscripts, run ten independent single-manuscript executions in five waves of two.
- Treat an “execution” as the platform's isolated task, agent, workflow run, or LLM context. Loading the same skill twice inside one shared conversation does not create two isolated executions.
- The coordinator may inventory files, assign workers, wait, check completion records, and collect outputs. It must not replace worker review with a shared candidate scan or write substantive manuscript comments itself.

## Isolation requirements

Give every worker:

- exactly one immutable source DOCX;
- its own working directory, extraction artifacts, issue ledger, rendered pages, and final output path;
- the target journal information available for that manuscript;
- the complete single-manuscript workflow and relevant companion skills.

Do not combine full text, extracted paragraphs, candidate lists, issue ledgers, or reference lists from different manuscripts in one review context. Shared journal rules may be cached, but each worker must apply and verify them independently.

## Required coverage record

Before adding comments, each worker must record that it inspected the manuscript's applicable parts:

- titles, authors, affiliations, abstracts, and keywords in both languages;
- all body paragraphs and headings;
- every table and table cell;
- footnotes and endnotes, including empty, duplicate, or orphaned notes;
- headers, footers, text boxes, hyperlinks, fields, sections, tracked changes, and existing comments;
- figures, captions, source notes, appendices, and internal cross-references;
- all in-text citations, direct quotations, notes, and bibliography entries;
- English title, abstract, and keywords sentence by sentence against the Chinese text.

An OOXML inventory may assist this review, but a flag such as `footnotes: true` is not evidence that the footnote text was inspected. If a document component cannot be extracted or rendered, the worker must report that limitation and must not mark the manuscript complete.

## Review-depth safeguards

- Automated typo dictionaries and regex scans are optional candidate generators only. They never satisfy full-manuscript review.
- Citation checking must go beyond numeric set matching. Check that quotations, authors, page ranges, and source claims correspond to the cited work whenever the manuscript makes that relationship reviewable.
- Check Chinese and English abstracts for proposition-level alignment, not only spelling and punctuation.
- Challenge suggestions against the target journal's current rules and reliable examples. Remove unsupported preferences and label unresolved factual questions accurately.
- Do not use comment count as a quality target. If a manuscript produces unusually few or no comments, perform a coverage audit; do not invent issues to match other manuscripts.

## Per-manuscript completion gate

A worker is complete only when all of the following are true:

1. The full review checklist has been applied to every applicable document component.
2. An issue ledger with exact minimum-range targets has been finalized.
3. A separate comment-only DOCX has been produced without overwriting the source.
4. Comment structure, target ranges, visible-text preservation, and package integrity have passed verification.
5. The reviewed DOCX has been rendered and inspected as required by the documents workflow.
6. The worker reports output path, comment count, coverage, verification results, and explicit limitations.

If a deterministic extraction, comment, or verification step fails, fix and rerun that manuscript only. Do not advance its wave silently. If completion needs author input or unavailable external evidence, preserve the document, label the unresolved item or limitation, and report it rather than retrying indefinitely.

## Coordinator completion gate

After each wave, confirm that both independent worker records satisfy the per-manuscript gate before starting the next wave. After the final wave:

- confirm one reviewed output for every source manuscript;
- confirm source-to-output names are unambiguous and no source was overwritten;
- report failures or limitations per manuscript rather than hiding them in a batch total;
- deliver only the requested final artifacts.
