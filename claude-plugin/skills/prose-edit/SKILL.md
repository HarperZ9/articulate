---
name: prose-edit
description: Use when the user asks Claude to edit, rewrite, tighten or give an editorial pass to prose (an essay, documentation, a README, release notes, a message draft) with Articulate. Claude writes the rewrite itself, and Articulate's local checker finds the patterns before and confirms the result after. No other model or account is involved, and the checker sends the text nowhere.
allowed-tools: mcp__plugin_articulate-writing_articulate__check, mcp__plugin_articulate-writing_articulate__score
---

# Edit prose with Articulate, as the host model

Articulate's checker names prose patterns and what each one costs a reader. In this
flow you do the rewriting, and the checker confirms each pass. It works in any
harness that runs this plugin's server, with no model account of Articulate's own.

## Steps

1. Get the exact text. Read a named file with the usual file tools. Keep a byte copy
   of the original before any edit.
2. Call `check` on the original. Note the `gate`, each blocking finding with its
   `reason`, and the rule counts.
3. Before rewriting, list the protected spans: every number, date, URL and link
   target, citation, name, code span, quotation and stated limit or qualifier.
   These stay word for word.
4. Rewrite for the intended reader, one paragraph at a time:
   - fix every blocking finding by changing the construction, never by deleting a
     claim or a limit;
   - address the other findings where the fix keeps the meaning;
   - prefer active verbs to noun phrases, concrete statements to abstractions, and
     a direct statement of what the evidence covers to an "X, not Y" contrast;
   - keep the author's argument, order, examples and register.
5. Call `check` on the rewrite. If the gate is blocked, revise the flagged lines and
   check again. Stop when the gate is `ok`.
6. Compare the rewrite with the original: every protected span from step 3 must be
   present and unchanged. Restore the original sentence wherever a change moved a
   fact, a number, a source or a limit.
7. Report: the gate before and after, the findings fixed by rule, the sentences a
   reader should look at because their wording changed most, and the rewrite
   itself. Write it to a file only when the user asked for that.

## Limits to state with the result

A clean gate says the named patterns are gone. It says nothing about whether a fact
is right, whether every shade of meaning survived, or who or what wrote the text.
Never describe a finding as evidence of authorship.
