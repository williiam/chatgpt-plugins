"""Tests for the Billsmith document engine.

Run with:  python3 -m unittest discover -s tests -v
Optional extras (skipped when missing): pypdf for PDF parsing, Pillow for JPEG logos.
"""

import copy
import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, 'plugins', 'billsmith', 'skills', 'create-invoice', 'scripts', 'billdoc.py')
_spec = importlib.util.spec_from_file_location('billdoc', ENGINE)
billdoc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(billdoc)

try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None
try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

BASE = {
    'type': 'invoice', 'number': 'INV-1', 'issue_date': '2026-10-01', 'currency': 'USD',
    'from': {'name': 'Seller Co'}, 'to': {'name': 'Buyer Co'},
    'items': [{'description': 'Work', 'quantity': 2, 'unit_price': 100}],
}


def spec(**changes):
    out = copy.deepcopy(BASE)
    out.update(changes)
    return out


def png(width, height, color_type, pixel, palette=None, trns=None):
    """Build a tiny PNG in pure Python. pixel is the bytes of one pixel."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xFFFFFFFF)
    rows = b''.join(b'\x00' + pixel * width for _ in range(height))
    out = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, color_type, 0, 0, 0))
    if palette:
        out += chunk(b'PLTE', palette)
    if trns:
        out += chunk(b'tRNS', trns)
    return out + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def run_spec(self, data, fmt='auto', name='out.pdf'):
        return billdoc.generate(data, os.path.join(self.dir, name), fmt, self.dir)


class TotalsTest(unittest.TestCase):
    def totals(self, data):
        return billdoc.generate(data, check_only=True)['totals']

    def test_simple(self):
        t = self.totals(spec())
        self.assertEqual(t['subtotal'], '200.00')
        self.assertEqual(t['total'], '200.00')
        self.assertEqual(t['balance_due'], '200.00')

    def test_tax_discount_shipping_paid(self):
        t = self.totals(spec(
            items=[{'description': 'A', 'quantity': 1, 'unit_price': 4200},
                   {'description': 'B', 'quantity': 32, 'unit_price': 95, 'discount_percent': 10},
                   {'description': 'C', 'quantity': 3, 'unit_price': '49.99', 'taxable': False}],
            taxes=[{'label': 'Sales tax', 'rate': 8.5}], discount={'percent': 5},
            shipping={'amount': 25}, amount_paid=1000))
        self.assertEqual(t, {'subtotal': '7085.97', 'discount': '354.30', 'shipping': '25.00', 'tax': '560.08',
                             'total': '7316.75', 'deductions': '0.00', 'amount_paid': '1000.00',
                             'balance_due': '6316.75'})

    def test_inclusive_tax(self):
        t = self.totals(spec(items=[{'description': 'A', 'unit_price': 120}], tax={'label': 'VAT', 'rate': 20},
                             prices_include_tax=True))
        self.assertEqual((t['subtotal'], t['tax'], t['total']), ('120.00', '20.00', '120.00'))

    def test_mixed_item_rates(self):
        s = billdoc.generate(spec(items=[{'description': 'A', 'unit_price': 100, 'tax_rate': 20},
                                         {'description': 'B', 'unit_price': 100, 'tax_rate': 5},
                                         {'description': 'C', 'unit_price': 100, 'tax_rate': 0}],
                                  tax={'label': 'VAT', 'rate': 20}), check_only=True)
        self.assertEqual(s['totals']['tax'], '25.00')
        self.assertEqual([l['label'] for l in s['tax_lines']], ['VAT (20%)', 'VAT (5%)', 'VAT (0%)'])

    def test_two_document_taxes(self):
        s = billdoc.generate(spec(items=[{'description': 'A', 'unit_price': 1000}],
                                  taxes=[{'label': 'GST', 'rate': 5}, {'label': 'PST', 'rate': 7}],
                                  currency='CAD'), check_only=True)
        self.assertEqual(s['totals']['tax'], '120.00')
        self.assertEqual(s['totals']['total'], '1120.00')
        self.assertEqual(s['display_total'], 'CA$1,120.00')

    def test_deductions_use_pre_tax_base(self):
        t = self.totals(spec(currency='TWD', items=[{'description': 'A', 'unit_price': 90000}],
                             tax={'label': '營業稅', 'rate': 5},
                             deductions=[{'label': '代扣所得稅', 'rate': 10}, {'label': '二代健保', 'rate': 2.11}]))
        self.assertEqual((t['tax'], t['total'], t['deductions'], t['balance_due']), ('4500', '94500', '10899', '83601'))

    def test_half_up_rounding(self):
        t = self.totals(spec(items=[{'description': 'A', 'unit_price': '0.125'}]))
        self.assertEqual(t['total'], '0.13')

    def test_receipt_defaults_to_fully_paid(self):
        t = self.totals(spec(type='receipt'))
        self.assertEqual((t['amount_paid'], t['balance_due']), ('200.00', '0.00'))

    def test_taxable_shipping(self):
        t = self.totals(spec(tax={'rate': 10}, shipping={'amount': 50, 'taxable': True}))
        self.assertEqual((t['tax'], t['total']), ('25.00', '275.00'))


class FormatTest(unittest.TestCase):
    def display(self, **changes):
        return billdoc.generate(spec(**changes), check_only=True)['display_total']

    def test_currency_styles(self):
        item = [{'description': 'A', 'unit_price': '1234567.5'}]
        self.assertEqual(self.display(items=item), '$1,234,567.50')
        self.assertEqual(self.display(items=item, currency='EUR', lang='de'), '1.234.567,50 €')
        self.assertEqual(self.display(items=item, currency='EUR', lang='fr'), '1 234 567,50 €')
        self.assertEqual(self.display(items=item, currency='EUR'), '€1,234,567.50')
        self.assertEqual(self.display(items=item, currency='JPY', lang='ja'), '¥1,234,568')
        self.assertEqual(self.display(items=item, currency='INR', currency_symbol='Rs'), 'Rs 12,34,567.50')
        self.assertEqual(self.display(items=item, currency='CHF', number_format="1'234.56"), "CHF 1'234'567.50")
        self.assertEqual(self.display(items=item, currency='PLN', lang='pl'), '1,234,567.50 zł')

    def test_dates(self):
        d = billdoc.datetime.date(2026, 3, 5)
        self.assertEqual(billdoc.format_date(d, 'MMM D, YYYY'), 'Mar 5, 2026')
        self.assertEqual(billdoc.format_date(d, 'DD/MM/YYYY'), '05/03/2026')
        self.assertEqual(billdoc.format_date(d, 'YYYY年M月D日'), '2026年3月5日')
        self.assertEqual(billdoc.format_date(d, 'D MMMM YYYY'), '5 March 2026')

    def test_due_date_from_terms(self):
        model = billdoc.build_model(spec(payment_terms_days=30))
        self.assertIn(('Due date', 'Oct 31, 2026'), model['view']['meta'])

    def test_labels_cover_every_language(self):
        for lang, table in billdoc.LABELS.items():
            self.assertEqual(set(table), set(billdoc.LABELS['en']), lang)
            table['includes'].format(tax='x')
            table['page'].format(page=1, pages=2)

    def test_label_override_and_title(self):
        model = billdoc.build_model(spec(labels={'bill_to': 'Client'}, title='TAX INVOICE'))
        self.assertEqual(model['view']['buyer_label'], 'Client')
        self.assertEqual(model['view']['title'], 'TAX INVOICE')


class ValidationTest(unittest.TestCase):
    def errors(self, data):
        with self.assertRaises(billdoc.SpecError) as ctx:
            billdoc.build_model(data)
        return ' '.join(ctx.exception.errors)

    def test_missing_required(self):
        text = self.errors({'type': 'invoice'})
        for needle in ('currency', 'number', 'issue_date', 'from', 'to', 'items'):
            self.assertIn(needle, text)

    def test_bad_values(self):
        self.assertIn('unit_price', self.errors(spec(items=[{'description': 'A', 'unit_price': '12,5'}])))
        self.assertIn('YYYY-MM-DD', self.errors(spec(issue_date='10/01/2026')))
        self.assertIn('accent_color', self.errors(spec(accent_color='blue')))
        self.assertIn('not both', self.errors(spec(discount={'percent': 5, 'amount': 5})))
        self.assertIn('type must be', self.errors(spec(type='memo')))
        self.assertIn('larger than the subtotal', self.errors(spec(discount={'amount': 500})))

    def test_item_rate_conflicts_with_two_taxes(self):
        text = self.errors(spec(taxes=[{'rate': 5}, {'rate': 7}],
                                items=[{'description': 'A', 'unit_price': 1, 'tax_rate': 0}]))
        self.assertIn('taxable', text)

    def test_out_of_range_input_is_rejected_not_crashed(self):
        self.assertIn('out of range', self.errors(spec(items=[{'description': 'A', 'unit_price': '9' * 40}])))
        self.assertIn('out of range', self.errors(spec(amount_paid=1e308)))
        self.assertIn('too long', self.errors(spec(to={'name': 'x' * 601})))
        self.assertIn('too many', self.errors(spec(custom_fields=[{'label': 'a', 'value': 'b'}] * 11)))
        self.assertIn('implausible year', self.errors(spec(issue_date='9999-12-31', payment_terms_days=30)))
        self.assertIn('number_format', self.errors(spec(number_format={})))

    def test_large_amounts_stay_exact(self):
        s = billdoc.generate(spec(items=[{'description': 'A', 'quantity': 999999, 'unit_price': '999999999999.99'}],
                                  tax={'rate': 7.5}), check_only=True)
        subtotal = 999999 * 99999999999999  # in cents, exact integer arithmetic
        self.assertEqual(s['totals']['subtotal'], '%d.%02d' % divmod(subtotal, 100))
        tax = (subtotal * 75 + 500) // 1000  # 7.5%, rounded half up
        self.assertEqual(s['totals']['tax'], '%d.%02d' % divmod(tax, 100))

    def test_unknown_field_warns(self):
        model = billdoc.build_model(spec(colour='red'))
        self.assertTrue(any('colour' in w for w in model['warnings']))

    def test_cli_reports_errors_as_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'bad.json')
            with open(path, 'w') as handle:
                json.dump({'type': 'invoice'}, handle)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = billdoc.main([path])
            self.assertEqual(code, 2)
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload['ok'])
            self.assertTrue(payload['errors'])


class TextEngineTest(unittest.TestCase):
    def test_font_selection(self):
        engine = billdoc.TextEngine('en', 'Zażółć 請款 テスト 한국어')
        self.assertEqual(engine.font_key('A'), 'L')
        self.assertEqual(engine.font_key('€'), 'L')
        self.assertEqual(engine.font_key('ł'), 'X')
        self.assertEqual(engine.font_key('ス'), 'J')
        self.assertEqual(engine.font_key('한'), 'K')
        self.assertIsNone(engine.font_key('Ж'))
        self.assertIsNone(engine.font_key('\U0001F600'))

    def test_chinese_variants(self):
        self.assertEqual(billdoc.TextEngine('en', '請款單').font_key('請'), 'T')
        self.assertEqual(billdoc.TextEngine('en', '账单').font_key('账'), 'S')
        self.assertEqual(billdoc.TextEngine('zh-CN', '日期').font_key('日'), 'S')

    def test_wrap(self):
        engine = billdoc.TextEngine('en', '')
        lines = engine.wrap('alpha beta gamma delta', 10, False, 60)
        self.assertTrue(all(engine.width(l, 10) <= 60 for l in lines))
        self.assertEqual(' '.join(lines), 'alpha beta gamma delta')
        long_word = engine.wrap('x' * 80, 10, False, 60)
        self.assertGreater(len(long_word), 1)
        self.assertEqual(''.join(long_word), 'x' * 80)
        self.assertEqual(engine.wrap('a\n\nb', 10, False, 60), ['a', '', 'b'])
        cjk = billdoc.TextEngine('zh-TW', '品').wrap('品牌識別設計與規範，交付檔案。', 10, False, 45)
        self.assertTrue(all(not l.startswith(('，', '。')) for l in cjk))

    def test_width_matches_metrics(self):
        engine = billdoc.TextEngine('en', '')
        self.assertAlmostEqual(engine.width('Hello', 10), (722 + 556 + 222 + 222 + 556) / 100.0)


class RenderTest(TempDirCase):
    def read_pdf(self, path):
        if pypdf is None:
            self.skipTest('pypdf not installed')
        return pypdf.PdfReader(path)

    def test_pdf_is_written(self):
        s = self.run_spec(spec())
        self.assertEqual((s['format'], s['pages']), ('pdf', 1))
        with open(s['file'], 'rb') as handle:
            data = handle.read()
        self.assertTrue(data.startswith(b'%PDF-1.4'))
        self.assertTrue(data.rstrip().endswith(b'%%EOF'))

    def test_pdf_text_round_trip(self):
        s = self.run_spec(spec(to={'name': 'Żółć Sp. z o.o.'}, notes='Grüße aus Köln'))
        text = self.read_pdf(s['file']).pages[0].extract_text()
        for needle in ('INVOICE', 'INV-1', 'Seller Co', 'Grüße aus Köln', '$200.00'):
            self.assertIn(needle, text)

    def test_many_items_paginate(self):
        items = [{'description': 'Line item number %d' % i, 'details': 'Detail text', 'unit_price': i} for i in range(1, 90)]
        s = self.run_spec(spec(items=items, notes='n\n' * 40))
        self.assertGreaterEqual(s['pages'], 3)
        reader = self.read_pdf(s['file'])
        self.assertEqual(len(reader.pages), s['pages'])
        self.assertIn('Page 2 of %d' % s['pages'], reader.pages[1].extract_text())
        self.assertIn('Description', reader.pages[1].extract_text())

    def test_row_taller_than_a_page_flows_across_pages(self):
        s = self.run_spec(spec(items=[{'description': 'Long', 'details': 'word ' * 1100, 'unit_price': 1},
                                      {'description': 'x' * 590, 'unit_price': 1}]))
        self.assertGreaterEqual(s['pages'], 2)
        reader = self.read_pdf(s['file'])
        self.assertIn('Description', reader.pages[1].extract_text())

    def test_column_headers_are_not_truncated(self):
        s = self.run_spec(spec(items=[{'description': 'One thing', 'unit_price': 5}]))
        text = self.read_pdf(s['file']).pages[0].extract_text()
        for header in ('Description', 'Qty', 'Unit price', 'Amount'):
            self.assertIn(header, text)

    def test_default_output_name(self):
        cwd = os.getcwd()
        os.chdir(self.dir)
        try:
            s = billdoc.generate(spec(number='INV 2026/007'))
        finally:
            os.chdir(cwd)
        self.assertEqual(os.path.basename(s['file']), 'invoice-INV-2026-007.pdf')

    def test_unsupported_script_falls_back_to_html(self):
        s = self.run_spec(spec(to={'name': 'ООО Ромашка'}))
        self.assertEqual(s['format'], 'html')
        self.assertTrue(s['file'].endswith('.html'))
        with open(s['file'], encoding='utf-8') as handle:
            page = handle.read()
        self.assertIn('ООО Ромашка', page)
        self.assertTrue(any('HTML' in w for w in s['warnings']))

    def test_forced_pdf_marks_unsupported(self):
        s = self.run_spec(spec(to={'name': 'ООО Ромашка'}), fmt='pdf')
        self.assertEqual(s['format'], 'pdf')
        self.assertTrue(any('"?"' in w for w in s['warnings']))

    def test_currency_sign_fallback(self):
        s = self.run_spec(spec(currency='INR'))
        self.assertEqual(s['display_total'], 'INR 200.00')
        self.assertTrue(any('INR' in w for w in s['warnings']))
        self.assertEqual(self.run_spec(spec(currency='INR'), fmt='html')['display_total'], '₹200.00')

    def test_html_escapes(self):
        s = self.run_spec(spec(notes='<script>alert(1)</script>'), fmt='html')
        with open(s['file'], encoding='utf-8') as handle:
            page = handle.read()
        self.assertNotIn('<script>alert', page)
        self.assertIn('&lt;script&gt;', page)

    def test_png_logos(self):
        cases = {
            'rgb.png': png(8, 4, 2, b'\x10\x80\xf0'),
            'rgba.png': png(8, 4, 6, b'\x10\x80\xf0\x80'),
            'gray_alpha.png': png(8, 4, 4, b'\x40\x80'),
            'palette.png': png(8, 4, 3, b'\x01', palette=b'\x00\x00\x00\xff\x00\x00', trns=b'\x00\xff'),
        }
        for name, blob in cases.items():
            with open(os.path.join(self.dir, name), 'wb') as handle:
                handle.write(blob)
            s = self.run_spec(spec(logo=name), name=name + '.pdf')
            self.assertEqual(s['warnings'], [], name)
            if pypdf is not None:
                page = pypdf.PdfReader(s['file']).pages[0]
                self.assertEqual(len(page.images), 1, name)

    def test_jpeg_logo(self):
        if Image is None:
            self.skipTest('Pillow not installed')
        Image.new('RGB', (40, 20), (200, 30, 30)).save(os.path.join(self.dir, 'logo.jpg'))
        s = self.run_spec(spec(logo='logo.jpg'))
        self.assertEqual(s['warnings'], [])

    def test_bad_logo_is_a_warning_not_a_failure(self):
        with open(os.path.join(self.dir, 'logo.gif'), 'wb') as handle:
            handle.write(b'GIF89a')
        s = self.run_spec(spec(logo='logo.gif'))
        self.assertTrue(any('logo' in w.lower() for w in s['warnings']))
        s = self.run_spec(spec(logo='missing.png'))
        self.assertTrue(any('logo' in w.lower() for w in s['warnings']))

    def test_every_type_and_language_renders(self):
        for doc_type in billdoc.DOC_TYPES:
            for lang in billdoc.LABELS:
                s = self.run_spec(spec(type=doc_type, lang=lang, valid_days=14, payment_terms_days=14,
                                       tax={'rate': 10}, amount_paid=50), name='%s-%s.pdf' % (doc_type, lang))
                self.assertEqual(s['format'], 'pdf', (doc_type, lang, s['warnings']))


if __name__ == '__main__':
    unittest.main()
