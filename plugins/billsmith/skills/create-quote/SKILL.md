---
name: create-quote
description: Create a professional price quote or estimate as a ready-to-send PDF with exact totals. Use when the user asks to make, generate, draft or write a quote, quotation, estimate, price proposal or bid for a client, job or project, in any language (報價單, 估價單, 見積書, presupuesto, devis, Angebot, preventivo). Handles line items, optional discounts, shipping, taxes, validity dates, logos and brand colours. Do not use for invoices (use create-invoice), for receipts (use create-receipt), or for deciding what price the user should charge.
---

# Create a quote or estimate

Produce a PDF quote from the details the user gives. The bundled script lays
out the page and does all of the arithmetic, so the totals are exact and the
result looks the same every time.

Explicit instructions from the user always take priority over the defaults in
this skill.

## Workflow

1. **Collect the details.** Required: who is issuing the quote (`from.name`),
   who it is for (`to.name`), at least one line item with a price, and the
   currency. Take everything you can from the conversation and from files the
   user shared. If required details are missing, ask for all of them in one
   short message. Do not ask about optional details; apply the defaults below
   and mention them in the reply.
2. **Write the spec.** Save a JSON file that follows
   [references/spec.md](references/spec.md) with `"type": "quote"` (or
   `"estimate"` when the user calls it an estimate). Read that file before
   writing the first spec in a conversation.
3. **Run the script** from this skill's folder, writing the PDF to the folder
   where you save files for the user:

   ```bash
   python3 scripts/billdoc.py quote.json -o /path/to/output/quote-Q-2026-031.pdf
   ```

   The script needs only Python 3 and its standard library.
4. **Read the JSON the script prints.** If `ok` is false, fix formatting slips
   in the spec yourself and run it again; ask the user only when information
   is really missing. Pass on anything listed in `warnings`.
5. **Deliver.** Share the file and summarise it in two or three lines: the
   quote number, the total exactly as printed in `display_total`, how long the
   quote is valid, and any default you chose. Offer to adjust it.
6. **Revise** by editing the spec and running the script again. When the
   client accepts, offer to turn the same details into an invoice.

## Defaults when the user does not say

- `issue_date`: today's date.
- `number`: `Q-` followed by the issue date and a counter, for example
  `Q-20261001-01`. Say that the number can be changed.
- `valid_days`: 30, and say so in the reply.
- Tax: none. Add tax only at the rate the user states.
- `lang`: the language the user is writing in. For a language without built-in
  labels, translate the labels through `labels`.
- `page_size`: `Letter` for US and Canadian addresses, otherwise `A4`.
- Put scope, assumptions, exclusions and the delivery timeline in `notes`, and
  payment conditions (deposit, milestones) in `terms`, when the user mentions
  them.

## Rules

- Every amount shown to the user must come from the script output. Do not
  calculate or round totals yourself.
- Never invent facts. Names, addresses, tax IDs, prices, quantities and tax
  rates come from the user or their files. Leave an optional field out when
  the user did not give it.
- Do not set prices for the user. If they ask what to charge, you may discuss
  it, but put a price on the quote only after they confirm it.
- Optional or alternative items that should not count toward the total belong
  in `notes`, not in `items`.
- Do not decide which tax applies. Suggest confirming with an accountant or
  the tax authority and offer to apply whatever rate the user chooses.
- Create documents only for the user's own genuine business. Decline to make a
  quote in the name of a business the user does not represent or one meant to
  mislead someone.
- This skill only creates the file. It cannot send it or collect a signature;
  say so if asked.

## Examples

"Quote for Harbor Cafe: new website 3,500 EUR, logo refresh 800 EUR, 19% VAT,
valid two weeks, from Studio Lumen" has everything required. Use today's date,
generate a number, set `valid_days` to 14 and the tax to VAT 19%.

"I need an estimate for a kitchen remodel" has nothing required. Ask once: who
is it from, who is it for, what are the items and prices, and which currency.
