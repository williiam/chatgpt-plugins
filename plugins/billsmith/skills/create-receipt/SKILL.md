---
name: create-receipt
description: Create a payment receipt as a ready-to-send PDF with exact totals, for a payment the user's business has received. Use when the user asks to make, generate or write a receipt, sales receipt, payment receipt, rent receipt, deposit receipt or proof of payment for a customer, tenant or client, in any language (收據, 領収書, recibo, reçu, Quittung, ricevuta). Handles line items, taxes, payment date and method, part payments and logos. Do not use for invoices requesting payment (use create-invoice), for quotes (use create-quote), or to recreate a receipt from a shop or other business where the user was the buyer.
---

# Create a payment receipt

Produce a PDF receipt for a payment the user (or the business they act for)
has received. The bundled script lays out the page and does all of the
arithmetic, so the totals are exact and the result looks the same every time.

Explicit instructions from the user always take priority over the defaults in
this skill.

## Workflow

1. **Collect the details.** Required: who received the payment (`from.name`),
   who paid (`to.name`), what the payment was for (at least one line item with
   an amount), and the currency. Take everything you can from the conversation
   and from files the user shared, such as the invoice being paid. If required
   details are missing, ask for all of them in one short message. Do not ask
   about optional details; apply the defaults below and mention them in the
   reply.
2. **Write the spec.** Save a JSON file that follows
   [references/spec.md](references/spec.md) with `"type": "receipt"`. Read
   that file before writing the first spec in a conversation.
3. **Run the script** from this skill's folder, writing the PDF to the folder
   where you save files for the user:

   ```bash
   python3 scripts/billdoc.py receipt.json -o /path/to/output/receipt-R-2026-052.pdf
   ```

   The script needs only Python 3 and its standard library.
4. **Read the JSON the script prints.** If `ok` is false, fix formatting slips
   in the spec yourself and run it again; ask the user only when information
   is really missing. Pass on anything listed in `warnings`.
5. **Deliver.** Share the file and summarise it in two or three lines: the
   receipt number, the amount paid, the payment date and method, any balance
   still due as printed in `display_balance_due`, and any default you chose.
6. **Revise** by editing the spec and running the script again.

## Defaults when the user does not say

- `issue_date` and `payment_date`: today's date.
- `number`: `R-` followed by the issue date and a counter, for example
  `R-20261001-01`. Say that the number can be changed.
- `amount_paid`: leave it out for a payment in full. Set it only for a deposit
  or part payment; the receipt then shows the balance still due.
- `payment_method`: leave it out unless the user states it. Write it in words
  ("Bank transfer", "Cash", "Card"). Never include card numbers, bank logins
  or other payment credentials.
- `reference`: the number of the invoice being paid, when there is one.
- Tax: none. Add tax only at the rate the user states.
- `lang`: the language the user is writing in. For a language without built-in
  labels, translate the labels through `labels`.
- `page_size`: `Letter` for US and Canadian addresses, otherwise `A4`.

## Rules

- Every amount shown to the user must come from the script output. Do not
  calculate or round totals yourself.
- Never invent facts. Names, addresses, tax IDs, amounts, dates and payment
  methods come from the user or their files. Leave an optional field out when
  the user did not give it.
- A receipt records a real payment received by the issuer. Decline requests
  to produce a receipt in the name of a shop, landlord, employer or other
  business the user does not represent, to recreate or alter a receipt for
  something the user bought, or to document a payment that did not happen,
  for example for an expense claim, a refund, a warranty or a visa
  application. Offer what is legitimate instead, such as asking the seller
  for a duplicate.
- Do not decide which tax applies. Suggest confirming with an accountant or
  the tax authority and offer to apply whatever rate the user chooses.
- This skill only creates the file. It cannot send it or confirm that a
  payment arrived; say so if asked.

## Examples

"Receipt for Maria Lopez, she paid 1,200 USD rent for October by bank transfer
today, from Elm Street Rentals" has everything required. Use today's date for
both dates, generate a number, and deliver the PDF.

"Jordan paid a 500 GBP deposit on the 2,000 GBP wedding photography package"
is a part payment: one item at 2,000, `amount_paid` 500, and the receipt shows
1,500 still due. Ask who is issuing the receipt if the conversation has not
said.

"Make me a receipt from Apple for the laptop I bought" must be declined: the
user is the buyer, not the seller.
