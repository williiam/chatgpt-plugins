# Document spec reference

`scripts/billdoc.py` turns one JSON object into a PDF. All amounts are plain
numbers (`1250`, `19.99`, or the string `"19.99"`), never formatted strings such
as `"$1,250"`. All dates are `YYYY-MM-DD`. Leave out any field you do not need;
do not send empty placeholders.

## Contents

- [Minimal example](#minimal-example)
- [Top-level fields](#top-level-fields)
- [Parties](#parties-from-to-ship_to)
- [Line items](#line-items)
- [Taxes](#taxes)
- [Discounts, shipping, deductions, payments](#discounts-shipping-deductions-payments)
- [Language, numbers and dates](#language-numbers-and-dates)
- [Look and layout](#look-and-layout)
- [Script output](#script-output)
- [Full example](#full-example)

## Minimal example

```json
{
  "type": "invoice",
  "number": "INV-2026-014",
  "issue_date": "2026-10-01",
  "currency": "USD",
  "from": {"name": "Northwind Studio LLC"},
  "to": {"name": "Acme Robotics Inc."},
  "items": [
    {"description": "Website design", "quantity": 32, "unit": "hrs", "unit_price": 95}
  ]
}
```

## Top-level fields

| Field | Required | Meaning |
| --- | --- | --- |
| `type` | no (default `invoice`) | `invoice`, `quote`, `estimate`, `receipt`, `credit_note`, `proforma` |
| `number` | yes | Document number shown on the page and used in the file name |
| `issue_date` | yes | Date of the document |
| `currency` | yes | 3-letter ISO code: `USD`, `EUR`, `GBP`, `TWD`, `JPY`, ... |
| `from` | yes | The business or person issuing the document |
| `to` | yes | The customer (for a receipt: the payer) |
| `items` | yes | Non-empty list of line items |
| `ship_to` | no | Delivery address when it differs from `to` |
| `due_date` or `payment_terms_days` | no | Invoice / proforma only. `payment_terms_days: 30` means issue date + 30 days |
| `valid_until` or `valid_days` | no | Quote / estimate / proforma only |
| `payment_date`, `payment_method` | no | Mainly for receipts, e.g. `"payment_method": "Bank transfer"` |
| `reference`, `po_number` | no | Short reference values shown next to the dates |
| `custom_fields` | no | Extra short facts: `[{"label": "Project", "value": "Website relaunch"}]` |
| `notes`, `terms`, `payment_details` | no | Free text blocks (string, or list of lines) under the items |
| `footer` | no | One short line at the bottom of every page |
| `title` | no | Replaces the heading, e.g. `"TAX INVOICE"` |

## Parties (`from`, `to`, `ship_to`)

```json
{
  "name": "Northwind Studio LLC",
  "address": ["120 Harbor Street, Suite 4", "Portland, OR 97204", "United States"],
  "email": "billing@northwind.example",
  "phone": "+1 503 555 0142",
  "website": "northwind.example",
  "tax_id": "93-1234567",
  "tax_id_label": "EIN",
  "extra": ["Company no. 01234567"]
}
```

Only `name` is required. `address` is a string with line breaks or a list of
lines. `tax_id_label` renames the tax ID line (VAT ID, GSTIN, ABN, 統一編號 ...).

## Line items

| Field | Required | Meaning |
| --- | --- | --- |
| `description` | yes | What was sold or done |
| `unit_price` | yes | Price for one unit. Negative values are allowed for credit lines |
| `quantity` | no (default 1) | May be fractional, e.g. `6.5` |
| `unit` | no | Shown after the quantity: `hrs`, `days`, `pcs` |
| `details` | no | Smaller second line under the description |
| `discount_percent` or `discount_amount` | no | Discount on this line only |
| `tax_rate` | no | Overrides the document tax rate for this line (single-tax documents only) |
| `taxable` | no | `false` exempts the line from every document tax |

## Taxes

Give the tax exactly as the user states it. One tax:

```json
"tax": {"label": "VAT", "rate": 20}
```

Several taxes on the same base (for example GST + PST, or CGST + SGST):

```json
"taxes": [{"label": "GST", "rate": 5}, {"label": "PST", "rate": 7}]
```

- Mixed rates in one document: keep a single `tax` and set `tax_rate` on the
  lines that differ (`0` for zero-rated lines). A tax-rate column appears
  automatically.
- `"prices_include_tax": true` when the prices already contain the tax. The
  total then stays equal to the sum of the lines and the tax is shown as an
  "Includes ..." line.
- No tax fields means no tax line at all.

## Discounts, shipping, deductions, payments

```json
"discount": {"percent": 5, "label": "Loyalty discount"},
"shipping": {"amount": 25, "taxable": false},
"deductions": [{"label": "Withholding tax", "rate": 10}],
"amount_paid": 1000
```

- `discount` takes `percent` or `amount` and applies to the subtotal before tax.
- `shipping` may be a bare number. Set `taxable: true` to tax it like the items.
- `deductions` are subtracted after the total, for amounts the customer withholds
  and pays to an authority on the seller's behalf (withholding tax, TDS, IRPF,
  代扣所得稅, 二代健保補充保費). A `rate` is applied to the pre-tax amount; use
  `amount` for a fixed value.
- `amount_paid` records a deposit or part payment; the document then ends with
  a balance due. For a `receipt` it defaults to the full amount.

## Language, numbers and dates

| Field | Meaning |
| --- | --- |
| `lang` | Language of the built-in labels: `en`, `zh-TW`, `zh-CN`, `ja`, `ko`, `es`, `fr`, `de`, `pt`, `it`, `nl`. Default `en` |
| `labels` | Override any label, e.g. `{"bill_to": "Client", "total": "Total due"}`. Use this to translate labels into a language not listed above |
| `number_format` | `"1,234.56"`, `"1.234,56"`, `"1 234,56"`, `"1'234.56"` or `"1,23,456.78"`. Defaults follow `lang` |
| `date_format` | Tokens `YYYY`, `MMMM`, `MMM`, `MM`, `M`, `DD`, `D`, e.g. `"DD/MM/YYYY"`, `"D MMMM YYYY"`. Month names are English |
| `currency_symbol` | Replaces the default sign, e.g. `"Rs"` |
| `currency_position` | `"prefix"` or `"suffix"` |
| `decimals` | Decimal places for amounts when the currency default is not wanted |

Label keys: `title_invoice`, `title_quote`, `title_estimate`, `title_receipt`,
`title_credit_note`, `title_proforma`, `number_invoice`, `number_quote`,
`number_estimate`, `number_receipt`, `number_credit_note`, `number_proforma`,
`issue_date`, `due_date`, `valid_until`, `payment_date`, `payment_method`,
`reference`, `po_number`, `bill_to`, `prepared_for`, `received_from`,
`credit_to`, `ship_to`, `tax_id`, `description`, `quantity`, `unit_price`,
`discount`, `tax_rate`, `tax`, `amount`, `subtotal`, `shipping`, `total`,
`includes` (must contain `{tax}`), `amount_paid`, `balance_due`, `amount_due`,
`notes`, `terms`, `payment_details`, `page` (must contain `{page}` and
`{pages}`).

The PDF can draw Latin-alphabet languages (Western, Central and Northern
European, Turkish, Romanian, Baltic) and Chinese, Japanese and Korean. For
other scripts (Cyrillic, Greek, Arabic, Hebrew, Thai, Devanagari, Vietnamese
and so on) the script writes a print-ready `.html` file instead and says so in
`warnings`.

## Look and layout

| Field | Meaning |
| --- | --- |
| `logo` | Path to a PNG or JPEG file, absolute or relative to the spec file |
| `accent_color` | Hex colour for the heading and table header, e.g. `"#107A57"` |
| `page_size` | `"A4"` (default) or `"Letter"` (use for US and Canadian customers) |

## Script output

The script prints one JSON object. On success:

```json
{
  "ok": true,
  "type": "invoice",
  "number": "INV-2026-014",
  "currency": "USD",
  "totals": {"subtotal": "7085.97", "discount": "354.30", "shipping": "25.00", "tax": "560.08",
             "total": "7316.75", "deductions": "0.00", "amount_paid": "1000.00", "balance_due": "6316.75"},
  "tax_lines": [{"label": "Sales tax (8.5%)", "amount": "560.08"}],
  "display_total": "$7,316.75",
  "display_balance_due": "$6,316.75",
  "format": "pdf",
  "pages": 1,
  "file": "/absolute/path/invoice-INV-2026-014.pdf",
  "warnings": []
}
```

On a problem with the spec it exits with code 2 and prints
`{"ok": false, "errors": ["items[0].unit_price is required.", ...]}`. Fix the
spec when the error is a formatting slip; ask the user when information is
missing.

`--check` validates and prints the totals without writing a file.
`--format html` writes the HTML version on request.

## Full example

```json
{
  "type": "invoice",
  "number": "INV-2026-014",
  "issue_date": "2026-10-01",
  "payment_terms_days": 30,
  "currency": "USD",
  "page_size": "Letter",
  "logo": "logo.png",
  "accent_color": "#1F4FBF",
  "from": {
    "name": "Northwind Studio LLC",
    "address": ["120 Harbor Street, Suite 4", "Portland, OR 97204"],
    "email": "billing@northwind.example",
    "tax_id": "93-1234567",
    "tax_id_label": "EIN"
  },
  "to": {
    "name": "Acme Robotics Inc.",
    "address": "500 Market Street\nSan Francisco, CA 94105",
    "email": "ap@acme.example"
  },
  "po_number": "PO-7781",
  "items": [
    {"description": "Brand identity design", "details": "Logo suite and brand book", "unit_price": 4200},
    {"description": "Website design", "quantity": 32, "unit": "hrs", "unit_price": 95, "discount_percent": 10},
    {"description": "Stock photography licence", "quantity": 3, "unit_price": 49.99, "taxable": false}
  ],
  "tax": {"label": "Sales tax", "rate": 8.5},
  "discount": {"percent": 5, "label": "Loyalty discount"},
  "shipping": 25,
  "amount_paid": 1000,
  "notes": "Thank you for your business.",
  "payment_details": ["Bank: First Pacific Bank", "Account: 000123456789"],
  "terms": "Payment is due within 30 days."
}
```
