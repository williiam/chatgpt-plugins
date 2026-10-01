---
name: create-invoice
description: Create a professional invoice as a ready-to-send PDF with exact totals. Use when the user asks to make, generate, draft or write an invoice, bill a client, invoice freelance work, hours, services or products, issue a tax, VAT or GST invoice, a proforma invoice or a credit note, in any language (請款單, 請求書, factura, facture, Rechnung, fattura). Handles line items, discounts, shipping, one or several taxes, tax-inclusive prices, withholding deductions, deposits, logos and brand colours. Do not use for quotes or estimates (use create-quote), for receipts of payments already received (use create-receipt), or for bookkeeping, tax advice, sending documents or collecting payments.
---

# Create an invoice

Produce a PDF invoice from the details the user gives. The bundled script lays
out the page and does all of the arithmetic, so the totals are exact and the
result looks the same every time.

Explicit instructions from the user always take priority over the defaults in
this skill.

## Workflow

1. **Collect the details.** Required: who is issuing the invoice (`from.name`),
   who is being billed (`to.name`), at least one line item with a price, and
   the currency. Take everything you can from the conversation and from files
   the user shared (a timesheet, an order, an earlier invoice). If required
   details are missing, ask for all of them in one short message. Do not ask
   about optional details; apply the defaults below and mention them in the
   reply.
2. **Write the spec.** Save a JSON file that follows
   [references/spec.md](references/spec.md). Read that file before writing the
   first spec in a conversation.
3. **Run the script** from this skill's folder, writing the PDF to the folder
   where you save files for the user:

   ```bash
   python3 scripts/billdoc.py invoice.json -o /path/to/output/invoice-INV-2026-014.pdf
   ```

   The script needs only Python 3 and its standard library.
4. **Read the JSON the script prints.** If `ok` is false, fix formatting slips
   in the spec yourself and run it again; ask the user only when information
   is really missing. Pass on anything listed in `warnings`.
5. **Deliver.** Share the file and summarise it in two or three lines: the
   invoice number, the total and the balance due exactly as printed in
   `display_total` and `display_balance_due`, the due date, and any default
   you chose. Offer to adjust it.
6. **Revise** by editing the spec and running the script again. Keep the same
   invoice number unless the user asks for a new one.

## Defaults when the user does not say

- `issue_date`: today's date.
- `number`: `INV-` followed by the issue date and a counter, for example
  `INV-20261001-01`. Say that the number can be changed to fit the user's own
  numbering.
- `due_date`: leave it out unless the user gives payment terms ("net 30",
  "due in two weeks", a date).
- Tax: none. Add tax only at the rate the user states.
- `lang`: the language the user is writing in. For a language without built-in
  labels, translate the labels through `labels`.
- `page_size`: `Letter` for US and Canadian addresses, otherwise `A4`.
- `type`: `invoice`. Use `proforma` or `credit_note` only when the user asks
  for one. For a credit note, enter the credited amounts as positive numbers
  and put the original invoice number in `reference`.

## Rules

- Every amount shown to the user must come from the script output. Do not
  calculate or round totals yourself, and do not restate them differently from
  the script.
- Never invent facts. Names, addresses, tax IDs, registration numbers, bank
  details, tax rates, prices and quantities come from the user or their files.
  Leave an optional field out when the user did not give it.
- Do not decide which tax applies. If the user asks what rate to charge or
  whether they must charge tax, say that it depends on their location and
  registration, suggest confirming with an accountant or the tax authority,
  and offer to apply whatever rate they choose.
- Use `deductions` only when the user says the customer withholds part of the
  payment (withholding tax, TDS, IRPF, 代扣所得稅, 二代健保補充保費).
- Keep the user's wording for item descriptions; tidy spelling only.
- Create documents only for the user's own genuine business. Decline to make a
  document that is meant to mislead someone, such as an invoice in the name of
  a business the user does not represent, a backdated or altered copy of
  someone else's invoice, or paperwork for a transaction that did not happen.
- This skill only creates the file. It cannot send the invoice, take payment,
  or record it in accounting software; say so if asked.

## Examples

"Invoice Acme Robotics for 32 hours of web design at $95/hour, net 30, from
Northwind Studio LLC" has everything required. Use today's date, generate a
number, set `payment_terms_days` to 30, apply no tax, and deliver the PDF.

"Make me an invoice" has nothing required. Ask once: who is it from, who is it
for, what are the items and prices, and which currency.

"幫我開一張請款單給好日子公司，品牌設計 60,000 元，代扣 10% 所得稅" is a Traditional
Chinese invoice in TWD: set `lang` to `zh-TW`, add the deduction, and ask for
the issuer's name if the conversation has not provided it.
