#!/usr/bin/env python3
"""billdoc.py - render an invoice, quote, estimate, receipt, credit note or
proforma invoice from a JSON spec into a PDF (or print-ready HTML).

Standard library only. The script reads one JSON spec (plus an optional logo
image named in it), writes one output file, and prints a JSON summary with the
computed totals to stdout. It never uses the network and runs no other
programs.

Usage:
    python3 billdoc.py SPEC.json [-o OUTPUT] [--format auto|pdf|html] [--check]

Exit codes: 0 success, 2 the spec has problems (listed in the JSON summary),
1 any other failure.
"""

import argparse
import base64
import datetime
import html
import json
import os
import re
import struct
import sys
import unicodedata
import zlib
from collections import OrderedDict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext

VERSION = "1.0.0"

getcontext().prec = 60  # amounts are capped below 1e15, so every intermediate result is exact

# --------------------------------------------------------------------------
# Font metrics: Helvetica / Helvetica-Bold advance widths (Adobe Core 14 AFM)
# --------------------------------------------------------------------------

_W_CHARS = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xffĀāĂăĄąĆćČčĎďĐđĒēĖėĘęĚěĞğĢģĪīĮįİıĶķĹĺĻļĽľŁłŃńŅņŇňŌōŐőŒœŔŕŖŗŘřŚśŞşŠšŢţŤťŪūŮůŰűŲųŸŹźŻżŽžƒȘșȚțˆˇ˘˙˚˛˜˝–—‘’‚“”„†‡•…‰‹›⁄€™∂∆∑−√≠≤≥◊'
_W_REG = '278,278,355,556,556,889,667,191,333,333,389,584,278,333,278,278,556,556,556,556,556,556,556,556,556,556,278,278,584,584,584,556,1015,667,667,722,722,667,611,778,722,278,500,667,556,833,722,778,667,778,722,667,611,722,667,944,667,667,611,278,278,278,469,556,333,556,556,500,556,556,278,556,556,222,222,500,222,833,556,556,556,556,333,500,278,556,500,722,500,500,500,334,260,334,584,333,556,556,556,556,260,556,333,737,370,556,584,737,333,400,584,333,333,333,556,537,278,333,333,365,556,834,834,834,611,667,667,667,667,667,667,1000,722,667,667,667,667,278,278,278,278,722,722,778,778,778,778,778,584,778,722,722,722,722,667,667,611,556,556,556,556,556,556,889,500,556,556,556,556,278,278,278,278,556,556,556,556,556,556,556,584,611,556,556,556,556,500,556,500,667,556,667,556,667,556,722,500,722,500,722,643,722,556,667,556,667,556,667,556,667,556,778,556,778,556,278,278,278,222,278,278,667,500,556,222,556,222,556,299,556,222,722,556,722,556,722,556,778,556,778,556,1000,944,722,333,722,333,722,333,667,500,667,500,667,500,611,278,611,317,722,556,722,556,722,556,722,556,667,611,500,611,500,611,500,556,667,500,611,278,333,333,333,333,333,333,333,333,556,1000,222,222,222,333,333,333,556,556,350,1000,1000,333,333,167,556,1000,476,612,600,584,453,549,549,549,471'
_W_BOLD = '278,333,474,556,556,889,722,238,333,333,389,584,278,333,278,278,556,556,556,556,556,556,556,556,556,556,333,333,584,584,584,611,975,722,722,722,722,667,611,778,722,278,556,722,611,833,722,778,667,778,722,667,611,722,667,944,667,667,611,333,278,333,584,556,333,556,611,556,611,556,333,611,611,278,278,556,278,889,611,611,611,611,389,556,333,611,556,778,556,556,500,389,280,389,584,333,556,556,556,556,280,556,333,737,370,556,584,737,333,400,584,333,333,333,611,556,278,333,333,365,556,834,834,834,611,722,722,722,722,722,722,1000,722,667,667,667,667,278,278,278,278,722,722,778,778,778,778,778,584,778,722,722,722,722,667,667,611,556,556,556,556,556,556,889,556,556,556,556,556,278,278,278,278,611,611,611,611,611,611,611,584,611,611,611,611,611,556,611,556,722,556,722,556,722,556,722,556,722,556,722,743,722,611,667,556,667,556,667,556,667,556,778,611,778,611,278,278,278,278,278,278,722,556,611,278,611,278,611,400,611,278,722,611,722,611,722,611,778,611,778,611,1000,944,722,389,722,389,722,389,667,556,667,556,667,556,611,333,611,389,722,611,722,611,722,611,722,611,667,611,500,611,500,611,500,556,667,556,611,333,333,333,333,333,333,333,333,333,556,1000,278,278,278,500,500,500,556,556,350,1000,1000,333,333,167,556,1000,494,612,600,584,549,549,549,549,494'
# Latin letters outside Windows-1252 that the core Helvetica glyph set covers
# (Central European, Baltic, Turkish, Romanian). They are drawn through a
# second Helvetica resource with a /Differences encoding, codes 128 and up.
_EXT_GLYPHS = '0100:Amacron 0101:amacron 0102:Abreve 0103:abreve 0104:Aogonek 0105:aogonek 0106:Cacute 0107:cacute 010C:Ccaron 010D:ccaron 010E:Dcaron 010F:dcaron 0110:Dcroat 0111:dcroat 0112:Emacron 0113:emacron 0116:Edotaccent 0117:edotaccent 0118:Eogonek 0119:eogonek 011A:Ecaron 011B:ecaron 011E:Gbreve 011F:gbreve 0122:Gcommaaccent 0123:gcommaaccent 012A:Imacron 012B:imacron 012E:Iogonek 012F:iogonek 0130:Idotaccent 0131:dotlessi 0136:Kcommaaccent 0137:kcommaaccent 0139:Lacute 013A:lacute 013B:Lcommaaccent 013C:lcommaaccent 013D:Lcaron 013E:lcaron 0141:Lslash 0142:lslash 0143:Nacute 0144:nacute 0145:Ncommaaccent 0146:ncommaaccent 0147:Ncaron 0148:ncaron 014C:Omacron 014D:omacron 0150:Ohungarumlaut 0151:ohungarumlaut 0154:Racute 0155:racute 0156:Rcommaaccent 0157:rcommaaccent 0158:Rcaron 0159:rcaron 015A:Sacute 015B:sacute 015E:Scedilla 015F:scedilla 0162:Tcommaaccent 0163:tcommaaccent 0164:Tcaron 0165:tcaron 016A:Umacron 016B:umacron 016E:Uring 016F:uring 0170:Uhungarumlaut 0171:uhungarumlaut 0172:Uogonek 0173:uogonek 0179:Zacute 017A:zacute 017B:Zdotaccent 017C:zdotaccent 0218:Scommaaccent 0219:scommaaccent 021A:Tcommaaccent 021B:tcommaaccent 02C7:caron 02D8:breve 02D9:dotaccent 02DA:ring 02DB:ogonek 02DD:hungarumlaut 2044:fraction 2202:partialdiff 2206:Delta 2211:summation 2212:minus 221A:radical 2260:notequal 2264:lessequal 2265:greaterequal 25CA:lozenge'

WIDTHS = {}
for _c, _r, _b in zip(_W_CHARS, _W_REG.split(','), _W_BOLD.split(',')):
    WIDTHS[_c] = (int(_r), int(_b))
EXT_CODE = {}
EXT_NAMES = []
for _i, _pair in enumerate(_EXT_GLYPHS.split()):
    _cp, _name = _pair.split(':')
    EXT_CODE[chr(int(_cp, 16))] = 128 + _i
    EXT_NAMES.append(_name)

# CJK text uses the standard non-embedded Adobe CJK font collections, which
# every mainstream PDF viewer maps to an installed CJK font.
CJK_FONTS = OrderedDict([
    ('T', {'codec': 'cp950', 'base': 'MHei-Medium', 'cmap': 'UniCNS-UCS2-H', 'ordering': 'CNS1', 'supplement': 3}),
    ('S', {'codec': 'gbk', 'base': 'STSong-Light', 'cmap': 'UniGB-UCS2-H', 'ordering': 'GB1', 'supplement': 4}),
    ('J', {'codec': 'cp932', 'base': 'HeiseiKakuGo-W5', 'cmap': 'UniJIS-UCS2-H', 'ordering': 'Japan1', 'supplement': 4}),
    ('K', {'codec': 'cp949', 'base': 'HYGoThic-Medium', 'cmap': 'UniKS-UCS2-H', 'ordering': 'Korea1', 'supplement': 1}),
])
_CJK_RANGES = (
    (0x1100, 0x11FF), (0x2E80, 0x2FDF), (0x3000, 0x33FF), (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF), (0xAC00, 0xD7AF), (0xF900, 0xFAFF), (0xFE30, 0xFE4F),
    (0xFF00, 0xFFEF),
)
_NO_LINE_START = set('，。、；：！？）」』】〕》〉％,.;:!?)]}')

# Code points are written numerically so the source holds no invisible characters.
_SPACE_LIKE = dict.fromkeys((0x09, 0xA0, 0x2002, 0x2003, 0x2007, 0x2009, 0x200A, 0x202F, 0x3000), ' ')
_SPACE_LIKE.update(dict.fromkeys((0x2010, 0x2011), '-'))  # hyphen variants
_SPACE_LIKE.update(dict.fromkeys((0xAD, 0x200B, 0x200C, 0x200D, 0xFEFF), None))  # zero-width characters


def clean_text(value):
    """Normalise a user string for rendering (NFC, plain spaces, no controls)."""
    s = unicodedata.normalize('NFC', str(value)).replace('\r\n', '\n').replace('\r', '\n')
    s = s.translate(_SPACE_LIKE)
    return ''.join(ch for ch in s if ch == '\n' or unicodedata.category(ch)[0] != 'C')


def _is_cjk(ch):
    cp = ord(ch)
    for lo, hi in _CJK_RANGES:
        if lo <= cp <= hi:
            return True
    return False


class TextEngine(object):
    """Maps characters to PDF fonts and measures / wraps text."""

    def __init__(self, lang, sample):
        order = {'zh-TW': 'TSJK', 'zh-CN': 'STJK', 'ja': 'JTSK', 'ko': 'KTSJ'}.get(lang)
        cjk = [ch for ch in sample if _is_cjk(ch)]
        if order is None:
            if any(0x3040 <= ord(ch) <= 0x30FF for ch in cjk):
                order = 'JTSK'
            elif any(0xAC00 <= ord(ch) <= 0xD7AF or 0x1100 <= ord(ch) <= 0x11FF for ch in cjk):
                order = 'KTSJ'
            elif all(self._encodable(ch, 'cp950') for ch in cjk):
                order = 'TSJK'
            else:
                order = 'STJK'
        self.order = order
        self.has_cjk = bool(cjk)
        self._cache = {}
        self.unsupported = set()

    @staticmethod
    def _encodable(ch, codec):
        try:
            ch.encode(codec)
            return True
        except (UnicodeEncodeError, LookupError):
            return False

    def font_key(self, ch):
        """'L' Helvetica, 'X' extended Latin, 'T'/'S'/'J'/'K' CJK, or None."""
        key = self._cache.get(ch, 0)
        if key != 0:
            return key
        key = None
        if ch in WIDTHS:
            key = 'X' if ch in EXT_CODE else 'L'
        elif ord(ch) <= 0xFFFF and (_is_cjk(ch) or (self.has_cjk and not 0x0370 <= ord(ch) <= 0x058F)):
            for k in self.order:
                if self._encodable(ch, CJK_FONTS[k]['codec']):
                    key = k
                    break
        self._cache[ch] = key
        return key

    def supports(self, text):
        return all(self.font_key(ch) is not None for ch in text if ch != '\n')

    def runs(self, text):
        """Split text into [(font_key, string)] runs; unsupported chars -> '?'."""
        out = []
        for ch in text:
            key = self.font_key(ch)
            if key is None:
                self.unsupported.add(ch)
                key, ch = 'L', '?'
            if out and out[-1][0] == key:
                out[-1][1].append(ch)
            else:
                out.append((key, [ch]))
        return [(k, ''.join(chars)) for k, chars in out]

    def char_width(self, ch, bold):
        key = self.font_key(ch)
        if key is None:
            return WIDTHS['?'][1 if bold else 0]
        if key in ('L', 'X'):
            return WIDTHS[ch][1 if bold else 0]
        return 1000

    def width(self, text, size, bold=False):
        return sum(self.char_width(ch, bold) for ch in text) * size / 1000.0

    def fit(self, text, size, bold, max_width):
        """Truncate with an ellipsis so the text fits max_width."""
        if self.width(text, size, bold) <= max_width + 0.01:
            return text
        limit = max_width - self.width('...', size, bold)
        used, kept = 0.0, []
        for ch in text:
            used += self.char_width(ch, bold) * size / 1000.0
            if used > limit:
                break
            kept.append(ch)
        return ''.join(kept).rstrip() + '...'

    def wrap(self, text, size, bold, max_width):
        """Greedy line wrapping. Latin breaks at spaces, CJK between characters."""
        lines = []
        for para in text.split('\n'):
            tokens = []
            for ch in para:
                if ch == ' ':
                    if tokens and tokens[-1] == ' ':
                        continue
                    tokens.append(' ')
                    continue
                wide = self.font_key(ch) in CJK_FONTS
                if tokens and tokens[-1] != ' ':
                    prev_wide = self.font_key(tokens[-1][-1]) in CJK_FONTS
                    if (not wide and not prev_wide) or ch in _NO_LINE_START:
                        tokens[-1] += ch
                        continue
                tokens.append(ch)
            line = ''
            for tok in tokens:
                if tok == ' ' and not line:
                    continue
                if self.width((line + tok).rstrip(), size, bold) <= max_width:
                    line += tok
                    continue
                if line.strip():
                    lines.append(line.rstrip())
                line = '' if tok == ' ' else tok
                while self.width(line, size, bold) > max_width and len(line) > 1:
                    used, cut = 0.0, 0
                    for cut, ch in enumerate(line):
                        used += self.char_width(ch, bold) * size / 1000.0
                        if used > max_width and cut > 0:
                            break
                    lines.append(line[:cut])
                    line = line[cut:]
            lines.append(line.rstrip())
        return lines


# --------------------------------------------------------------------------
# Labels, currencies and formats
# --------------------------------------------------------------------------

DOC_TYPES = ('invoice', 'quote', 'estimate', 'receipt', 'credit_note', 'proforma')
TYPE_ALIASES = {
    'quotation': 'quote', 'creditnote': 'credit_note', 'credit': 'credit_note',
    'pro_forma': 'proforma', 'proforma_invoice': 'proforma', 'pro_forma_invoice': 'proforma',
    'bill': 'invoice', 'sales_receipt': 'receipt', 'payment_receipt': 'receipt',
}

_LABEL_KEYS = (
    'title_invoice title_quote title_estimate title_receipt title_credit_note title_proforma '
    'number_invoice number_quote number_estimate number_receipt number_credit_note number_proforma '
    'issue_date due_date valid_until payment_date payment_method reference po_number '
    'bill_to prepared_for received_from credit_to ship_to tax_id '
    'description quantity unit_price discount tax_rate tax amount '
    'subtotal shipping total includes amount_paid balance_due amount_due '
    'notes terms payment_details page'
).split()


def _labels(*values):
    assert len(values) == len(_LABEL_KEYS), len(values)
    return dict(zip(_LABEL_KEYS, values))


LABELS = {
    'en': _labels(
        'INVOICE', 'QUOTE', 'ESTIMATE', 'RECEIPT', 'CREDIT NOTE', 'PROFORMA INVOICE',
        'Invoice no.', 'Quote no.', 'Estimate no.', 'Receipt no.', 'Credit note no.', 'Invoice no.',
        'Date', 'Due date', 'Valid until', 'Payment date', 'Payment method', 'Reference', 'PO number',
        'Bill to', 'Prepared for', 'Received from', 'Credit to', 'Ship to', 'Tax ID',
        'Description', 'Qty', 'Unit price', 'Discount', 'Tax', 'Tax', 'Amount',
        'Subtotal', 'Shipping', 'Total', 'Includes {tax}', 'Amount paid', 'Balance due', 'Amount due',
        'Notes', 'Terms', 'Payment details', 'Page {page} of {pages}'),
    'zh-TW': _labels(
        '請款單', '報價單', '估價單', '收據', '折讓單', '形式發票',
        '請款單號', '報價單號', '估價單號', '收據編號', '折讓單號', '發票號碼',
        '日期', '付款期限', '有效期限', '付款日期', '付款方式', '參考編號', '訂單編號',
        '請款對象', '客戶', '付款人', '客戶', '送貨地址', '統一編號',
        '項目', '數量', '單價', '折扣', '稅率', '稅額', '金額',
        '小計', '運費', '總計', '內含{tax}', '已付金額', '應付餘額', '應付金額',
        '備註', '條款', '付款資訊', '第 {page} 頁，共 {pages} 頁'),
    'zh-CN': _labels(
        '账单', '报价单', '估价单', '收据', '贷项通知单', '形式发票',
        '账单编号', '报价单号', '估价单号', '收据编号', '贷项单号', '发票编号',
        '日期', '付款期限', '有效期至', '付款日期', '付款方式', '参考编号', '订单编号',
        '客户', '客户', '付款方', '客户', '收货地址', '税号',
        '项目', '数量', '单价', '折扣', '税率', '税额', '金额',
        '小计', '运费', '总计', '含{tax}', '已付金额', '应付余额', '应付金额',
        '备注', '条款', '付款信息', '第 {page} 页，共 {pages} 页'),
    'ja': _labels(
        '請求書', '見積書', '見積書', '領収書', 'クレジットノート', 'プロフォーマインボイス',
        '請求書番号', '見積書番号', '見積書番号', '領収書番号', 'クレジットノート番号', '請求書番号',
        '発行日', 'お支払期限', '有効期限', 'お支払日', 'お支払方法', '参照番号', '注文番号',
        '請求先', 'お客様', 'お客様', 'お客様', '納品先', '登録番号',
        '品目', '数量', '単価', '割引', '税率', '消費税', '金額',
        '小計', '送料', '合計', 'うち{tax}', 'お支払済額', '残額', 'ご請求金額',
        '備考', '取引条件', 'お振込先', '{page} / {pages} ページ'),
    'ko': _labels(
        '청구서', '견적서', '견적서', '영수증', '크레딧 노트', '프로포마 인보이스',
        '청구서 번호', '견적서 번호', '견적서 번호', '영수증 번호', '크레딧 노트 번호', '청구서 번호',
        '발행일', '지급 기한', '유효 기한', '결제일', '결제 방법', '참조 번호', '주문 번호',
        '청구 대상', '수신', '결제자', '고객', '배송지', '사업자등록번호',
        '품목', '수량', '단가', '할인', '세율', '세금', '금액',
        '소계', '배송비', '합계', '{tax} 포함', '지급액', '미지급 잔액', '청구 금액',
        '비고', '거래 조건', '결제 정보', '{page} / {pages} 페이지'),
    'es': _labels(
        'FACTURA', 'PRESUPUESTO', 'PRESUPUESTO', 'RECIBO', 'NOTA DE CRÉDITO', 'FACTURA PROFORMA',
        'N.º de factura', 'N.º de presupuesto', 'N.º de presupuesto', 'N.º de recibo', 'N.º de nota de crédito', 'N.º de factura',
        'Fecha', 'Vencimiento', 'Válido hasta', 'Fecha de pago', 'Forma de pago', 'Referencia', 'N.º de pedido',
        'Facturar a', 'Preparado para', 'Recibido de', 'Cliente', 'Enviar a', 'ID fiscal',
        'Descripción', 'Cant.', 'Precio unitario', 'Descuento', 'Impuesto', 'Impuesto', 'Importe',
        'Subtotal', 'Envío', 'Total', 'Incluye {tax}', 'Importe pagado', 'Saldo pendiente', 'Importe a pagar',
        'Notas', 'Condiciones', 'Datos de pago', 'Página {page} de {pages}'),
    'fr': _labels(
        'FACTURE', 'DEVIS', 'DEVIS', 'REÇU', 'AVOIR', 'FACTURE PRO FORMA',
        'Facture n°', 'Devis n°', 'Devis n°', 'Reçu n°', 'Avoir n°', 'Facture n°',
        'Date', 'Échéance', 'Valable jusqu’au', 'Date de paiement', 'Mode de paiement', 'Référence', 'N° de commande',
        'Facturé à', 'Préparé pour', 'Reçu de', 'Client', 'Livré à', 'N° fiscal',
        'Description', 'Qté', 'Prix unitaire', 'Remise', 'Taxe', 'Taxe', 'Montant',
        'Sous-total', 'Livraison', 'Total', 'Dont {tax}', 'Montant payé', 'Solde dû', 'Montant dû',
        'Notes', 'Conditions', 'Coordonnées de paiement', 'Page {page} sur {pages}'),
    'de': _labels(
        'RECHNUNG', 'ANGEBOT', 'KOSTENVORANSCHLAG', 'QUITTUNG', 'GUTSCHRIFT', 'PROFORMA-RECHNUNG',
        'Rechnungsnr.', 'Angebotsnr.', 'Angebotsnr.', 'Quittungsnr.', 'Gutschriftsnr.', 'Rechnungsnr.',
        'Datum', 'Fällig am', 'Gültig bis', 'Zahlungsdatum', 'Zahlungsart', 'Referenz', 'Bestellnr.',
        'Rechnung an', 'Angebot für', 'Erhalten von', 'Kunde', 'Lieferadresse', 'Steuernr.',
        'Beschreibung', 'Menge', 'Einzelpreis', 'Rabatt', 'Steuer', 'Steuer', 'Betrag',
        'Zwischensumme', 'Versand', 'Gesamt', 'Enthält {tax}', 'Bereits bezahlt', 'Offener Betrag', 'Zu zahlen',
        'Hinweise', 'Bedingungen', 'Zahlungsdetails', 'Seite {page} von {pages}'),
    'pt': _labels(
        'FATURA', 'ORÇAMENTO', 'ORÇAMENTO', 'RECIBO', 'NOTA DE CRÉDITO', 'FATURA PROFORMA',
        'Fatura n.º', 'Orçamento n.º', 'Orçamento n.º', 'Recibo n.º', 'Nota de crédito n.º', 'Fatura n.º',
        'Data', 'Vencimento', 'Válido até', 'Data de pagamento', 'Forma de pagamento', 'Referência', 'N.º do pedido',
        'Faturar a', 'Preparado para', 'Recebido de', 'Cliente', 'Enviar para', 'ID fiscal',
        'Descrição', 'Qtd.', 'Preço unitário', 'Desconto', 'Imposto', 'Imposto', 'Valor',
        'Subtotal', 'Frete', 'Total', 'Inclui {tax}', 'Valor pago', 'Saldo devedor', 'Valor a pagar',
        'Observações', 'Condições', 'Dados para pagamento', 'Página {page} de {pages}'),
    'it': _labels(
        'FATTURA', 'PREVENTIVO', 'PREVENTIVO', 'RICEVUTA', 'NOTA DI CREDITO', 'FATTURA PROFORMA',
        'Fattura n.', 'Preventivo n.', 'Preventivo n.', 'Ricevuta n.', 'Nota di credito n.', 'Fattura n.',
        'Data', 'Scadenza', 'Valido fino al', 'Data di pagamento', 'Metodo di pagamento', 'Riferimento', 'N. ordine',
        'Fatturare a', 'Preparato per', 'Ricevuto da', 'Cliente', 'Spedire a', 'P. IVA',
        'Descrizione', 'Q.tà', 'Prezzo unitario', 'Sconto', 'Imposta', 'Imposta', 'Importo',
        'Subtotale', 'Spedizione', 'Totale', 'Include {tax}', 'Importo pagato', 'Saldo dovuto', 'Importo dovuto',
        'Note', 'Condizioni', 'Dati di pagamento', 'Pagina {page} di {pages}'),
    'nl': _labels(
        'FACTUUR', 'OFFERTE', 'OFFERTE', 'KWITANTIE', 'CREDITNOTA', 'PROFORMAFACTUUR',
        'Factuurnr.', 'Offertenr.', 'Offertenr.', 'Kwitantienr.', 'Creditnotanr.', 'Factuurnr.',
        'Datum', 'Vervaldatum', 'Geldig tot', 'Betaaldatum', 'Betaalmethode', 'Referentie', 'Bestelnr.',
        'Factuur aan', 'Opgesteld voor', 'Ontvangen van', 'Klant', 'Verzenden naar', 'Btw-nr.',
        'Omschrijving', 'Aantal', 'Stukprijs', 'Korting', 'Btw', 'Btw', 'Bedrag',
        'Subtotaal', 'Verzending', 'Totaal', 'Inclusief {tax}', 'Betaald bedrag', 'Openstaand saldo', 'Te betalen',
        'Opmerkingen', 'Voorwaarden', 'Betaalgegevens', 'Pagina {page} van {pages}'),
}

# code: (symbol, decimals)
CURRENCIES = {
    'USD': ('$', 2), 'EUR': ('€', 2), 'GBP': ('£', 2), 'JPY': ('¥', 0), 'CNY': ('¥', 2),
    'TWD': ('NT$', 0), 'HKD': ('HK$', 2), 'SGD': ('S$', 2), 'AUD': ('A$', 2), 'CAD': ('CA$', 2),
    'NZD': ('NZ$', 2), 'KRW': ('₩', 0), 'INR': ('₹', 2), 'CHF': ('CHF', 2), 'SEK': ('kr', 2),
    'NOK': ('kr', 2), 'DKK': ('kr', 2), 'PLN': ('zł', 2), 'CZK': ('Kč', 2), 'HUF': ('Ft', 0),
    'RON': ('lei', 2), 'MXN': ('MX$', 2), 'BRL': ('R$', 2), 'ARS': ('AR$', 2), 'CLP': ('CLP$', 0),
    'COP': ('COL$', 2), 'PEN': ('S/', 2), 'ZAR': ('R', 2), 'AED': ('AED', 2), 'SAR': ('SAR', 2),
    'ILS': ('₪', 2), 'TRY': ('₺', 2), 'THB': ('฿', 2), 'VND': ('₫', 0), 'IDR': ('Rp', 0),
    'MYR': ('RM', 2), 'PHP': ('₱', 2), 'RUB': ('₽', 2), 'UAH': ('₴', 2), 'NGN': ('₦', 2),
    'KES': ('KSh', 2), 'EGP': ('E£', 2), 'PKR': ('Rs', 2), 'BDT': ('৳', 2), 'KWD': ('KWD', 3),
    'BHD': ('BHD', 3), 'ISK': ('kr', 0),
}
SUFFIX_CURRENCIES = {'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'VND', 'ISK'}

NUMBER_FORMATS = {
    '1,234.56': (',', '.', False),
    '1.234,56': ('.', ',', False),
    '1 234,56': (' ', ',', False),
    "1'234.56": ("'", '.', False),
    '1,23,456.78': (',', '.', True),
}
DEFAULT_NUMBER_FORMAT = {'de': '1.234,56', 'es': '1.234,56', 'it': '1.234,56', 'pt': '1.234,56',
                         'nl': '1.234,56', 'fr': '1 234,56'}
DEFAULT_DATE_FORMAT = {'en': 'MMM D, YYYY', 'zh-TW': 'YYYY年M月D日', 'zh-CN': 'YYYY年M月D日',
                       'ja': 'YYYY年M月D日', 'ko': 'YYYY. M. D.', 'de': 'DD.MM.YYYY', 'fr': 'DD/MM/YYYY',
                       'es': 'DD/MM/YYYY', 'it': 'DD/MM/YYYY', 'pt': 'DD/MM/YYYY', 'nl': 'DD-MM-YYYY'}
MONTHS = ('January February March April May June July August September October November December').split()
PAGE_SIZES = {'A4': (595.28, 841.89), 'LETTER': (612.0, 792.0)}

KNOWN_KEYS = {
    'type', 'title', 'number', 'issue_date', 'due_date', 'payment_terms_days', 'valid_until', 'valid_days',
    'payment_date', 'payment_method', 'reference', 'po_number', 'custom_fields', 'lang', 'language',
    'currency', 'currency_symbol', 'currency_position', 'decimals', 'number_format', 'date_format',
    'from', 'to', 'ship_to', 'items', 'taxes', 'tax', 'tax_rate', 'tax_label', 'prices_include_tax',
    'discount', 'shipping', 'deductions', 'amount_paid', 'notes', 'terms', 'payment_details', 'footer',
    'logo', 'accent_color', 'page_size', 'labels',
}


def normalise_lang(value):
    v = str(value or 'en').strip().replace('_', '-').lower()
    if v.startswith('zh'):
        if any(t in v for t in ('hant', 'tw', 'hk', 'mo')):
            return 'zh-TW'
        return 'zh-CN'
    base = v.split('-')[0]
    return base if base in LABELS else 'en'


class SpecError(Exception):
    def __init__(self, errors):
        Exception.__init__(self, '; '.join(errors))
        self.errors = list(errors)


def to_decimal(value, field, errors, default=None, minimum=None):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        errors.append('%s must be a number.' % field)
        return default
    try:
        d = Decimal(str(value).strip())
    except InvalidOperation:
        errors.append('%s must be a plain number such as 1250 or 19.99 (got %r).' % (field, value))
        return default
    if not d.is_finite():
        errors.append('%s must be a finite number.' % field)
        return default
    if abs(d) >= Decimal('1e15') or d.as_tuple().exponent < -10:
        errors.append('%s is out of range.' % field)
        return default
    if minimum is not None and d < minimum:
        errors.append('%s must be at least %s.' % (field, minimum))
        return default
    return d


def parse_date(value, field, errors):
    if value in (None, ''):
        return None
    try:
        parsed = datetime.date.fromisoformat(str(value).strip())
    except ValueError:
        errors.append('%s must be a date in YYYY-MM-DD form (got %r).' % (field, value))
        return None
    if not 1900 <= parsed.year <= 2200:
        errors.append('%s has an implausible year (%d).' % (field, parsed.year))
        return None
    return parsed


def format_date(d, pattern):
    reps = {'YYYY': '%04d' % d.year, 'MMMM': MONTHS[d.month - 1], 'MMM': MONTHS[d.month - 1][:3],
            'MM': '%02d' % d.month, 'DD': '%02d' % d.day, 'M': str(d.month), 'D': str(d.day)}
    return re.sub('YYYY|MMMM|MMM|MM|DD|M|D', lambda m: reps[m.group(0)], pattern)


def group_digits(digits, sep, indian):
    if indian and len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        head = re.sub(r'(?<=\d)(?=(\d\d)+$)', sep, head)
        return head + sep + tail
    return re.sub(r'(?<=\d)(?=(\d{3})+$)', sep, digits)


class Formatter(object):
    def __init__(self, symbol, decimals, number_format, position):
        self.symbol = symbol
        self.decimals = decimals
        self.tsep, self.dsep, self.indian = NUMBER_FORMATS[number_format]
        self.position = position
        self.quantum = Decimal(1).scaleb(-decimals)

    def round(self, d):
        return d.quantize(self.quantum, rounding=ROUND_HALF_UP)

    def plain(self, d, decimals=None):
        """Localised number with a fixed number of decimals."""
        decimals = self.decimals if decimals is None else decimals
        q = d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
        text = format(abs(q), 'f')
        whole, _, frac = text.partition('.')
        out = group_digits(whole, self.tsep, self.indian)
        if decimals:
            out += self.dsep + frac
        return ('-' if q < 0 else '') + out

    def trimmed(self, d):
        """Localised number without trailing zeros (quantities, rates)."""
        q = d.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP).normalize()
        text = format(abs(q), 'f')
        whole, _, frac = text.partition('.')
        out = group_digits(whole, self.tsep, self.indian)
        if frac:
            out += self.dsep + frac
        return ('-' if q < 0 else '') + out

    def money(self, d, decimals=None):
        body = self.plain(abs(d), decimals)
        sign = '-' if self.round(d) < 0 else ''
        if not self.symbol:
            return sign + body
        if self.position == 'suffix':
            return sign + body + ' ' + self.symbol
        gap = ' ' if self.symbol[-1].isalpha() else ''
        return sign + self.symbol + gap + body

    def unit_price(self, d):
        """Unit prices may carry more precision than the currency (e.g. 0.125)."""
        exponent = -d.normalize().as_tuple().exponent
        return self.money(d, max(self.decimals, min(exponent, 4)))


# --------------------------------------------------------------------------
# Spec -> computed model
# --------------------------------------------------------------------------

def _text(value):
    if value is None:
        return ''
    if isinstance(value, (list, tuple)):
        return '\n'.join(clean_text(v).strip() for v in value if str(v).strip())
    return clean_text(value).strip()


def _party(raw, field, labels, errors, required=True):
    if raw is None:
        if required:
            errors.append('%s is required (an object with at least "name").' % field)
        return None
    if isinstance(raw, str):
        raw = {'name': raw}
    if not isinstance(raw, dict):
        errors.append('%s must be an object.' % field)
        return None
    name = _text(raw.get('name'))
    if not name:
        errors.append('%s.name is required.' % field)
    lines = []
    for key in ('address', 'email', 'phone', 'website'):
        value = _text(raw.get(key))
        if value:
            lines.extend(value.split('\n'))
    tax_id = _text(raw.get('tax_id'))
    if tax_id:
        lines.append('%s: %s' % (_text(raw.get('tax_id_label')) or labels['tax_id'], tax_id))
    extra = _text(raw.get('extra'))
    if extra:
        lines.extend(extra.split('\n'))
    return {'name': name, 'lines': lines}


def _rate_label(label, rate, fmt):
    if rate is None or '%' in label:
        return label
    return '%s (%s%%)' % (label, fmt.trimmed(rate))


LIST_LIMITS = {'items': 500, 'custom_fields': 10, 'taxes': 5, 'deductions': 8}
LONG_TEXT = ('notes', 'terms', 'payment_details', 'details')


def check_sizes(value, path, errors):
    """Reject oversized input early so a page never overflows or stalls."""
    if isinstance(value, str):
        cap = 6000 if path[-1].split('[')[0] in LONG_TEXT else 600
        if len(value) > cap:
            errors.append('%s is too long (maximum %d characters).' % ('.'.join(path), cap))
    elif isinstance(value, dict):
        for key, item in value.items():
            check_sizes(item, path + [str(key)], errors)
    elif isinstance(value, list):
        cap = LIST_LIMITS.get(path[-1], 40)
        if len(value) > cap:
            errors.append('%s has too many entries (maximum %d).' % ('.'.join(path), cap))
            return
        for index, item in enumerate(value):
            check_sizes(item, path[:-1] + ['%s[%d]' % (path[-1], index)], errors)


def build_model(spec):
    """Validate the spec and compute every amount. Raises SpecError."""
    errors, warnings = [], []
    if not isinstance(spec, dict):
        raise SpecError(['The spec must be a JSON object.'])
    for key, value in spec.items():
        check_sizes(value, [str(key)], errors)
    if errors:
        raise SpecError(errors)
    for key in sorted(set(spec) - KNOWN_KEYS):
        warnings.append('Unknown field "%s" was ignored.' % key)

    doc_type = str(spec.get('type') or 'invoice').strip().lower().replace('-', '_').replace(' ', '_')
    doc_type = TYPE_ALIASES.get(doc_type, doc_type)
    if doc_type not in DOC_TYPES:
        errors.append('type must be one of: %s.' % ', '.join(DOC_TYPES))
        doc_type = 'invoice'

    lang = normalise_lang(spec.get('lang') or spec.get('language'))
    labels = dict(LABELS['en'])
    labels.update(LABELS[lang])
    custom = spec.get('labels') or {}
    if not isinstance(custom, dict):
        errors.append('labels must be an object of label overrides.')
        custom = {}
    for key, value in custom.items():
        if key not in labels:
            warnings.append('Unknown label "%s" was ignored.' % key)
        elif _text(value):
            labels[key] = _text(value).replace('\n', ' ')
    for key in ('includes', 'page'):
        try:
            labels[key].format(tax='', page=1, pages=1)
        except (KeyError, IndexError, ValueError):
            errors.append('labels.%s has an invalid placeholder.' % key)
            labels[key] = LABELS['en'][key]

    # ---- currency and formats
    currency = str(spec.get('currency') or '').strip().upper()
    if not re.match(r'^[A-Z]{3}$', currency):
        errors.append('currency is required as a 3-letter ISO code such as USD, EUR or TWD.')
        currency = 'USD'
    symbol, decimals = CURRENCIES.get(currency, (currency, 2))
    if spec.get('currency_symbol') is not None:
        symbol = _text(spec.get('currency_symbol')).replace('\n', ' ')
    if spec.get('decimals') is not None:
        dec = spec.get('decimals')
        if isinstance(dec, int) and not isinstance(dec, bool) and 0 <= dec <= 4:
            decimals = dec
        else:
            errors.append('decimals must be a whole number from 0 to 4.')
    number_format = spec.get('number_format')
    if number_format is None:
        number_format = DEFAULT_NUMBER_FORMAT.get(lang, '1,234.56')
        if currency == 'INR' and lang == 'en':
            number_format = '1,23,456.78'
    elif not isinstance(number_format, str) or number_format not in NUMBER_FORMATS:
        errors.append('number_format must be one of: %s.' % ', '.join(sorted(NUMBER_FORMATS)))
        number_format = '1,234.56'
    position = spec.get('currency_position')
    if position is None:
        comma_decimal = NUMBER_FORMATS[number_format][1] == ','
        position = 'suffix' if (currency in SUFFIX_CURRENCIES or
                                (currency == 'EUR' and comma_decimal and lang != 'nl')) else 'prefix'
    elif position not in ('prefix', 'suffix'):
        errors.append('currency_position must be "prefix" or "suffix".')
        position = 'prefix'
    fmt = Formatter(symbol, decimals, number_format, position)
    date_format = spec.get('date_format') or DEFAULT_DATE_FORMAT.get(lang, 'MMM D, YYYY')
    if not isinstance(date_format, str) or 'YYYY' not in date_format or not re.search('M', date_format) \
            or not re.search('D', date_format):
        errors.append('date_format must contain YYYY, a month token (M, MM, MMM, MMMM) and a day token (D, DD).')
        date_format = 'YYYY-MM-DD'

    # ---- identity and dates
    number = _text(spec.get('number')).replace('\n', ' ')
    if not number:
        errors.append('number is required (for example INV-2026-001).')
    count = len(errors)
    issue_date = parse_date(spec.get('issue_date'), 'issue_date', errors)
    if issue_date is None and len(errors) == count:
        errors.append('issue_date is required in YYYY-MM-DD form.')

    def days_after(field):
        raw = spec.get(field)
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0 or raw > 3650:
            errors.append('%s must be a whole number of days from 0 to 3650.' % field)
            return None
        return issue_date + datetime.timedelta(days=raw) if issue_date else None

    due_date = parse_date(spec.get('due_date'), 'due_date', errors) or days_after('payment_terms_days')
    valid_until = parse_date(spec.get('valid_until'), 'valid_until', errors) or days_after('valid_days')
    payment_date = parse_date(spec.get('payment_date'), 'payment_date', errors)
    if issue_date and due_date and due_date < issue_date:
        warnings.append('due_date is earlier than issue_date.')
    if issue_date and valid_until and valid_until < issue_date:
        warnings.append('valid_until is earlier than issue_date.')

    seller = _party(spec.get('from'), 'from', labels, errors)
    buyer = _party(spec.get('to'), 'to', labels, errors)
    ship_to = _party(spec.get('ship_to'), 'ship_to', labels, errors, required=False)

    # ---- taxes declared for the whole document
    doc_taxes = []
    raw_taxes = spec.get('taxes')
    if raw_taxes is None and spec.get('tax') is not None:
        raw_taxes = [spec.get('tax')]
    if raw_taxes is None and spec.get('tax_rate') is not None:
        raw_taxes = [{'rate': spec.get('tax_rate'), 'label': spec.get('tax_label')}]
    if raw_taxes is not None and not isinstance(raw_taxes, list):
        errors.append('taxes must be a list of {"label", "rate"} objects.')
        raw_taxes = []
    for i, tax in enumerate(raw_taxes or []):
        if isinstance(tax, (int, float, str)) and not isinstance(tax, bool):
            tax = {'rate': tax}
        if not isinstance(tax, dict):
            errors.append('taxes[%d] must be an object with "label" and "rate".' % i)
            continue
        rate = to_decimal(tax.get('rate'), 'taxes[%d].rate' % i, errors, minimum=0)
        if rate is None:
            if tax.get('rate') is None:
                errors.append('taxes[%d].rate is required (a percentage such as 20).' % i)
            continue
        if rate >= 100:
            errors.append('taxes[%d].rate must be below 100.' % i)
            continue
        doc_taxes.append((_text(tax.get('label')).replace('\n', ' ') or labels['tax'], rate))
    inclusive = spec.get('prices_include_tax', False)
    if not isinstance(inclusive, bool):
        errors.append('prices_include_tax must be true or false.')
        inclusive = False

    # ---- line items
    raw_items = spec.get('items')
    if not isinstance(raw_items, list) or not raw_items:
        errors.append('items is required: a non-empty list of line items.')
        raw_items = []
    items = []
    groups = OrderedDict()
    subtotal = Decimal(0)
    for i, raw in enumerate(raw_items):
        field = 'items[%d]' % i
        if not isinstance(raw, dict):
            errors.append('%s must be an object.' % field)
            continue
        description = _text(raw.get('description'))
        if not description:
            errors.append('%s.description is required.' % field)
        if raw.get('unit_price') is None:
            errors.append('%s.unit_price is required.' % field)
        quantity = to_decimal(raw.get('quantity'), field + '.quantity', errors, default=Decimal(1))
        price = to_decimal(raw.get('unit_price'), field + '.unit_price', errors, default=Decimal(0))
        gross = quantity * price
        discount_text = ''
        line_discount = Decimal(0)
        if raw.get('discount_percent') is not None and raw.get('discount_amount') is not None:
            errors.append('%s: use discount_percent or discount_amount, not both.' % field)
        elif raw.get('discount_percent') is not None:
            pct = to_decimal(raw.get('discount_percent'), field + '.discount_percent', errors, Decimal(0), 0)
            if pct > 100:
                errors.append('%s.discount_percent cannot exceed 100.' % field)
                pct = Decimal(0)
            line_discount = gross * pct / 100
            if pct:
                discount_text = '-%s%%' % fmt.trimmed(pct)
        elif raw.get('discount_amount') is not None:
            line_discount = to_decimal(raw.get('discount_amount'), field + '.discount_amount', errors, Decimal(0), 0)
            if line_discount:
                discount_text = fmt.money(-line_discount)
        net = fmt.round(gross - line_discount)
        if raw.get('tax_rate') is not None:
            if len(doc_taxes) > 1:
                errors.append('%s.tax_rate cannot be combined with several document taxes; '
                              'use "taxable": false on exempt items instead.' % field)
                taxes = tuple(doc_taxes)
            else:
                rate = to_decimal(raw.get('tax_rate'), field + '.tax_rate', errors, Decimal(0), 0)
                if rate >= 100:
                    errors.append('%s.tax_rate must be below 100.' % field)
                    rate = Decimal(0)
                taxes = ((doc_taxes[0][0] if doc_taxes else labels['tax'], rate),)
        elif raw.get('taxable') is False:
            taxes = ()
        else:
            taxes = tuple(doc_taxes)
        groups[taxes] = groups.get(taxes, Decimal(0)) + net
        subtotal += net
        qty_text = fmt.trimmed(quantity)
        unit = _text(raw.get('unit')).replace('\n', ' ')
        if unit:
            qty_text += ' ' + unit
        items.append({
            'description': description,
            'details': _text(raw.get('details')),
            'quantity': qty_text,
            'unit_price': fmt.unit_price(price),
            'discount': discount_text,
            'tax': ' + '.join(fmt.trimmed(r) + '%' for _, r in taxes) if taxes else '-',
            'amount': fmt.money(net),
            'net': net,
        })

    # ---- document discount, shipping
    discount = Decimal(0)
    discount_label = labels['discount']
    raw_discount = spec.get('discount')
    if raw_discount is not None:
        if isinstance(raw_discount, (int, float, str)) and not isinstance(raw_discount, bool):
            raw_discount = {'amount': raw_discount}
        if not isinstance(raw_discount, dict):
            errors.append('discount must be an object with "percent" or "amount".')
        else:
            if _text(raw_discount.get('label')):
                discount_label = _text(raw_discount.get('label')).replace('\n', ' ')
            if raw_discount.get('percent') is not None and raw_discount.get('amount') is not None:
                errors.append('discount: use percent or amount, not both.')
            elif raw_discount.get('percent') is not None:
                pct = to_decimal(raw_discount.get('percent'), 'discount.percent', errors, Decimal(0), 0)
                if pct > 100:
                    errors.append('discount.percent cannot exceed 100.')
                    pct = Decimal(0)
                discount = fmt.round(subtotal * pct / 100)
                discount_label = _rate_label(discount_label, pct, fmt)
            else:
                discount = fmt.round(to_decimal(raw_discount.get('amount'), 'discount.amount', errors, Decimal(0), 0))
            if discount > subtotal > 0:
                errors.append('discount is larger than the subtotal.')
                discount = Decimal(0)
    shipping = Decimal(0)
    shipping_label = labels['shipping']
    shipping_taxable = False
    raw_shipping = spec.get('shipping')
    if raw_shipping is not None:
        if isinstance(raw_shipping, (int, float, str)) and not isinstance(raw_shipping, bool):
            raw_shipping = {'amount': raw_shipping}
        if not isinstance(raw_shipping, dict):
            errors.append('shipping must be a number or an object with "amount".')
        else:
            shipping = fmt.round(to_decimal(raw_shipping.get('amount'), 'shipping.amount', errors, Decimal(0), 0))
            if _text(raw_shipping.get('label')):
                shipping_label = _text(raw_shipping.get('label')).replace('\n', ' ')
            shipping_taxable = raw_shipping.get('taxable') is True

    # ---- taxes
    factor = (subtotal - discount) / subtotal if subtotal else Decimal(1)
    tax_lines = OrderedDict()
    for label, rate in doc_taxes:
        tax_lines[(label, rate)] = Decimal(0)
    for taxes, base in groups.items():
        adjusted = base * factor
        if shipping_taxable and taxes == tuple(doc_taxes):
            adjusted += shipping
        rate_sum = sum((r for _, r in taxes), Decimal(0))
        for label, rate in taxes:
            if inclusive:
                amount = adjusted * rate / (100 + rate_sum)
            else:
                amount = adjusted * rate / 100
            tax_lines[(label, rate)] = tax_lines.get((label, rate), Decimal(0)) + amount
    if shipping_taxable and doc_taxes and tuple(doc_taxes) not in groups:
        rate_sum = sum((r for _, r in doc_taxes), Decimal(0))
        for label, rate in doc_taxes:
            tax_lines[(label, rate)] += shipping * rate / ((100 + rate_sum) if inclusive else 100)
    if shipping_taxable and not doc_taxes:
        warnings.append('shipping.taxable was ignored because the document has no taxes.')
    tax_lines = OrderedDict((k, fmt.round(v)) for k, v in tax_lines.items())
    tax_total = sum(tax_lines.values(), Decimal(0))
    total = subtotal - discount + shipping + (Decimal(0) if inclusive else tax_total)
    net_base = subtotal - discount - (tax_total if inclusive else Decimal(0))

    # ---- deductions (withholding), payments
    deductions = []
    raw_deductions = spec.get('deductions') or []
    if not isinstance(raw_deductions, list):
        errors.append('deductions must be a list of {"label", "rate" or "amount"} objects.')
        raw_deductions = []
    for i, raw in enumerate(raw_deductions):
        field = 'deductions[%d]' % i
        if not isinstance(raw, dict) or not _text(raw.get('label')):
            errors.append('%s must be an object with a "label" and a "rate" or "amount".' % field)
            continue
        label = _text(raw.get('label')).replace('\n', ' ')
        if raw.get('rate') is not None and raw.get('amount') is not None:
            errors.append('%s: use rate or amount, not both.' % field)
        elif raw.get('rate') is not None:
            rate = to_decimal(raw.get('rate'), field + '.rate', errors, Decimal(0), 0)
            deductions.append((_rate_label(label, rate, fmt), fmt.round(net_base * rate / 100)))
        elif raw.get('amount') is not None:
            deductions.append((label, fmt.round(to_decimal(raw.get('amount'), field + '.amount', errors, Decimal(0), 0))))
        else:
            errors.append('%s needs a "rate" or an "amount".' % field)
    deduction_total = sum((a for _, a in deductions), Decimal(0))
    payable = total - deduction_total
    paid = to_decimal(spec.get('amount_paid'), 'amount_paid', errors, None, 0)
    if paid is None:
        paid = payable if doc_type == 'receipt' else Decimal(0)
    paid = fmt.round(paid)
    balance = payable - paid
    if total < 0:
        warnings.append('The total is negative.')
    if balance < 0:
        warnings.append('amount_paid is larger than the amount payable; the balance is negative.')

    accent = spec.get('accent_color') or '#1F4FBF'
    if not isinstance(accent, str) or not re.match(r'^#[0-9A-Fa-f]{6}$', accent):
        errors.append('accent_color must be a hex colour such as #1F4FBF.')
        accent = '#1F4FBF'
    page_size = str(spec.get('page_size') or 'A4').upper()
    if page_size not in PAGE_SIZES:
        errors.append('page_size must be "A4" or "Letter".')
        page_size = 'A4'
    custom_fields = []
    raw_fields = spec.get('custom_fields') or []
    if not isinstance(raw_fields, list):
        errors.append('custom_fields must be a list of {"label", "value"} objects.')
        raw_fields = []
    for i, raw in enumerate(raw_fields):
        if not isinstance(raw, dict) or not _text(raw.get('label')) or not _text(raw.get('value')):
            errors.append('custom_fields[%d] must be an object with "label" and "value".' % i)
            continue
        custom_fields.append((_text(raw.get('label')).replace('\n', ' '), _text(raw.get('value')).replace('\n', ' ')))

    if errors:
        raise SpecError(errors)

    # ---- view model shared by both renderers
    def fdate(d):
        return format_date(d, date_format)

    meta = [(labels['number_' + doc_type], number), (labels['issue_date'], fdate(issue_date))]
    if due_date and doc_type in ('invoice', 'proforma'):
        meta.append((labels['due_date'], fdate(due_date)))
    if valid_until and doc_type in ('quote', 'estimate', 'proforma'):
        meta.append((labels['valid_until'], fdate(valid_until)))
    if payment_date:
        meta.append((labels['payment_date'], fdate(payment_date)))
    for key in ('payment_method', 'reference', 'po_number'):
        value = _text(spec.get(key)).replace('\n', ' ')
        if value:
            meta.append((labels[key], value))
    meta.extend(custom_fields)

    columns = [('description', labels['description'], 'left'), ('quantity', labels['quantity'], 'right'),
               ('unit_price', labels['unit_price'], 'right')]
    if any(item['discount'] for item in items):
        columns.append(('discount', labels['discount'], 'right'))
    if len(groups) > 1:
        columns.append(('tax', labels['tax_rate'], 'right'))
    columns.append(('amount', labels['amount'], 'right'))

    rows = []  # (label, value, style)
    extras = bool(discount or shipping or tax_lines)
    if extras:
        rows.append((labels['subtotal'], fmt.money(subtotal), 'normal'))
    if discount:
        rows.append((discount_label, fmt.money(-discount), 'normal'))
    if shipping:
        rows.append((shipping_label, fmt.money(shipping), 'normal'))
    tax_rows = [(_rate_label(label, rate, fmt), amount) for (label, rate), amount in tax_lines.items()]
    if not inclusive:
        rows.extend((label, fmt.money(amount), 'normal') for label, amount in tax_rows)
    settles = bool(deductions or paid) or doc_type == 'receipt'
    rows.append((labels['total'], fmt.money(total), 'bold' if settles else 'highlight'))
    if inclusive:
        rows.extend((labels['includes'].format(tax=label), fmt.money(amount), 'muted') for label, amount in tax_rows)
    rows.extend((label, fmt.money(-amount), 'normal') for label, amount in deductions)
    if doc_type == 'receipt':
        rows.append((labels['amount_paid'], fmt.money(paid), 'highlight'))
        if balance:
            rows.append((labels['balance_due'], fmt.money(balance), 'normal'))
    elif settles:
        if paid:
            rows.append((labels['amount_paid'], fmt.money(-paid), 'normal'))
        rows.append((labels['balance_due' if paid else 'amount_due'], fmt.money(balance), 'highlight'))

    blocks = []
    for key in ('notes', 'payment_details', 'terms'):
        value = _text(spec.get(key))
        if value:
            blocks.append((labels[key], value))

    buyer_label = {'invoice': 'bill_to', 'proforma': 'bill_to', 'quote': 'prepared_for',
                   'estimate': 'prepared_for', 'receipt': 'received_from', 'credit_note': 'credit_to'}[doc_type]
    rgb = tuple(int(accent[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    view = {
        'type': doc_type, 'lang': lang, 'number': number,
        'title': _text(spec.get('title')).replace('\n', ' ') or labels['title_' + doc_type],
        'meta': meta, 'seller': seller, 'buyer_label': labels[buyer_label], 'buyer': buyer,
        'ship_label': labels['ship_to'], 'ship_to': ship_to,
        'columns': columns, 'items': items, 'totals': rows, 'blocks': blocks,
        'footer': _text(spec.get('footer')).replace('\n', ' '), 'page_label': labels['page'],
        'accent': accent, 'accent_rgb': rgb, 'on_accent': (0.1, 0.1, 0.12) if luminance > 0.6 else (1.0, 1.0, 1.0),
        'page_size': page_size, 'logo': _text(spec.get('logo')),
    }
    raw_totals = OrderedDict([
        ('subtotal', subtotal), ('discount', discount), ('shipping', shipping), ('tax', tax_total),
        ('total', total), ('deductions', deduction_total), ('amount_paid', paid), ('balance_due', balance),
    ])
    summary = {
        'type': doc_type, 'number': number, 'currency': currency,
        'prices_include_tax': inclusive,
        'totals': OrderedDict((k, format(fmt.round(v), 'f')) for k, v in raw_totals.items()),
        'tax_lines': [{'label': label, 'amount': format(amount, 'f')} for label, amount in tax_rows],
        'display_total': fmt.money(total),
        'display_balance_due': fmt.money(balance),
    }
    return {'view': view, 'summary': summary, 'warnings': warnings, 'formatter': fmt, 'currency': currency}


def view_strings(view):
    """Every string that will be drawn, for script-support checks."""
    out = [view['title'], view['buyer_label'], view['ship_label'], view['footer'], view['page_label']]
    for label, value in view['meta']:
        out.extend((label, value))
    for party in (view['seller'], view['buyer'], view['ship_to']):
        if party:
            out.append(party['name'])
            out.extend(party['lines'])
    for _, label, _ in view['columns']:
        out.append(label)
    for item in view['items']:
        out.extend(item[k] for k in ('description', 'details', 'quantity', 'unit_price', 'discount', 'tax', 'amount'))
    for label, value, _ in view['totals']:
        out.extend((label, value))
    for heading, body in view['blocks']:
        out.extend((heading, body))
    return out


# --------------------------------------------------------------------------
# Logo images
# --------------------------------------------------------------------------

class ImageError(Exception):
    pass


def _png_unfilter(raw, width, height, bpp):
    stride = width * bpp
    if len(raw) < (stride + 1) * height:
        raise ImageError('the PNG data is truncated')
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for row in range(height):
        kind = raw[pos]
        cur = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += stride + 1
        if kind == 1:
            for i in range(bpp, stride):
                cur[i] = (cur[i] + cur[i - bpp]) & 255
        elif kind == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 255
        elif kind == 3:
            for i in range(stride):
                left = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
        elif kind == 4:
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                cur[i] = (cur[i] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 255
        elif kind != 0:
            raise ImageError('the PNG uses an unknown filter')
        out[row * stride:(row + 1) * stride] = cur
        prev = cur
    return out


def load_image(path):
    """Return a dict describing a PDF image XObject for a PNG or JPEG file."""
    with open(path, 'rb') as handle:
        data = handle.read()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        pos, idat, palette, trns, header = 8, [], None, None, None
        while pos + 8 <= len(data):
            length, kind = struct.unpack('>I4s', data[pos:pos + 8])
            body = data[pos + 8:pos + 8 + length]
            pos += 12 + length
            if kind == b'IHDR':
                header = struct.unpack('>IIBBBBB', body)
            elif kind == b'PLTE':
                palette = body
            elif kind == b'tRNS':
                trns = body
            elif kind == b'IDAT':
                idat.append(body)
            elif kind == b'IEND':
                break
        if not header or not idat:
            raise ImageError('the PNG file is incomplete')
        width, height, depth, color, _, _, interlace = header
        if interlace:
            raise ImageError('interlaced PNG files are not supported')
        if depth == 16 or (color in (2, 4, 6) and depth != 8):
            raise ImageError('only 8-bit PNG files are supported')
        raw = b''.join(idat)
        image = {'width': width, 'height': height, 'bits': depth, 'filter': 'FlateDecode', 'smask': None}
        if color in (4, 6) or (color == 3 and trns and depth == 8 and min(trns) < 255):
            if width * height > 1600000:
                raise ImageError('the transparent PNG is too large (keep it under about 1200 x 1200 pixels)')
            channels = {3: 1, 4: 2, 6: 4}[color]
            pixels = _png_unfilter(zlib.decompress(raw), width, height, channels)
            if color == 6:
                rgb = bytearray(width * height * 3)
                rgb[0::3], rgb[1::3], rgb[2::3] = pixels[0::4], pixels[1::4], pixels[2::4]
                image.update(space='/DeviceRGB', data=zlib.compress(bytes(rgb)))
                alpha = bytes(pixels[3::4])
            elif color == 4:
                image.update(space='/DeviceGray', data=zlib.compress(bytes(pixels[0::2])))
                alpha = bytes(pixels[1::2])
            else:
                table = bytes(trns) + b'\xff' * (256 - len(trns))
                image.update(space='[/Indexed /DeviceRGB %d <%s>]' % (len(palette) // 3 - 1, palette.hex()),
                             data=zlib.compress(bytes(pixels)))
                alpha = bytes(pixels).translate(table)
            image['smask'] = zlib.compress(alpha)
            return image
        colors = 3 if color == 2 else 1
        if color == 3:
            if not palette:
                raise ImageError('the PNG palette is missing')
            image['space'] = '[/Indexed /DeviceRGB %d <%s>]' % (len(palette) // 3 - 1, palette.hex())
        else:
            image['space'] = '/DeviceRGB' if color == 2 else '/DeviceGray'
        image['data'] = raw
        image['parms'] = '<< /Predictor 15 /Colors %d /BitsPerComponent %d /Columns %d >>' % (colors, depth, width)
        return image
    if data[:2] == b'\xff\xd8':
        pos = 2
        while pos + 4 <= len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                pos += 2
                continue
            length = struct.unpack('>H', data[pos + 2:pos + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                depth, height, width, channels = struct.unpack('>BHHB', data[pos + 4:pos + 10])
                if channels not in (1, 3) or depth != 8:
                    raise ImageError('only 8-bit grayscale or RGB JPEG files are supported')
                return {'width': width, 'height': height, 'bits': 8, 'filter': 'DCTDecode', 'smask': None,
                        'space': '/DeviceRGB' if channels == 3 else '/DeviceGray', 'data': data}
            pos += 2 + length
        raise ImageError('the JPEG file has no image header')
    raise ImageError('the logo must be a PNG or JPEG file')


# --------------------------------------------------------------------------
# Minimal PDF writer
# --------------------------------------------------------------------------

class Pdf(object):
    """Collects page content in top-left-origin coordinates and writes a PDF."""

    def __init__(self, width, height, engine):
        self.width, self.height = width, height
        self.engine = engine
        self.pages = []
        self.fonts = set()
        self.images = []

    def new_page(self):
        self.pages.append([])

    def _emit(self, text):
        self.pages[-1].append(text)

    def rect(self, x, y, w, h, color):
        self._emit('%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f' % (color + (x, self.height - y - h, w, h)))

    def line(self, x1, y1, x2, y2, color, width=0.5):
        self._emit('%.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S'
                   % (color + (width, x1, self.height - y1, x2, self.height - y2)))

    def text(self, x, y, text, size, bold=False, color=(0, 0, 0), align='left'):
        """Draw one line of text; y is the baseline measured from the page top."""
        if not text:
            return
        engine = self.engine
        if align == 'right':
            x -= engine.width(text, size, bold)
        elif align == 'center':
            x -= engine.width(text, size, bold) / 2.0
        parts = ['BT %.3f %.3f %.3f rg' % color]
        for key, chunk in engine.runs(text):
            if key == 'L':
                name, payload = ('FLB' if bold else 'FL'), chunk.encode('cp1252').hex()
            elif key == 'X':
                name, payload = ('FXB' if bold else 'FX'), bytes(EXT_CODE[ch] for ch in chunk).hex()
            else:
                name, payload = 'F' + key, chunk.encode('utf-16-be').hex()
            self.fonts.add(name)
            mode = ''
            if key in CJK_FONTS and bold and size >= 9:
                # The CJK collections have no bold face: thicken with a hairline stroke.
                # Small sizes are left regular because the stroke clogs the glyphs.
                mode = '%.3f %.3f %.3f RG %.3f w 2 Tr ' % (color + (size * 0.02,))
            parts.append('/%s %.2f Tf %s1 0 0 1 %.2f %.2f Tm <%s> Tj%s'
                         % (name, size, mode, x, self.height - y, payload, ' 0 Tr' if mode else ''))
            x += engine.width(chunk, size, bold)
        parts.append('ET')
        self._emit(' '.join(parts))

    def image(self, image, x, y, w, h):
        if image not in self.images:
            self.images.append(image)
        self._emit('q %.2f 0 0 %.2f %.2f %.2f cm /Im%d Do Q'
                   % (w, h, x, self.height - y - h, self.images.index(image) + 1))

    def build(self, title):
        objects = []

        def add(body):
            objects.append(body if isinstance(body, bytes) else body.encode('latin-1'))
            return len(objects)

        def stream(dictionary, data):
            return ('<< %s /Length %d >>\nstream\n' % (dictionary, len(data))).encode('latin-1') + data + b'\nendstream'

        add('')  # 1: catalog, filled in below
        add('')  # 2: page tree
        font_refs = []
        for name in sorted(self.fonts):
            if name in ('FL', 'FLB'):
                ref = add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica%s /Encoding /WinAnsiEncoding >>'
                          % ('-Bold' if name == 'FLB' else ''))
            elif name in ('FX', 'FXB'):
                ref = add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica%s /Encoding << /Type /Encoding '
                          '/BaseEncoding /WinAnsiEncoding /Differences [128 %s] >> >>'
                          % ('-Bold' if name == 'FXB' else '', ' '.join('/' + n for n in EXT_NAMES)))
            else:
                info = CJK_FONTS[name[1]]
                descriptor = add('<< /Type /FontDescriptor /FontName /%s /Flags 4 /FontBBox [0 -120 1000 880] '
                                 '/ItalicAngle 0 /Ascent 880 /Descent -120 /CapHeight 880 /StemV 93 >>' % info['base'])
                descendant = add('<< /Type /Font /Subtype /CIDFontType0 /BaseFont /%s /CIDSystemInfo << /Registry '
                                 '(Adobe) /Ordering (%s) /Supplement %d >> /FontDescriptor %d 0 R /DW 1000 >>'
                                 % (info['base'], info['ordering'], info['supplement'], descriptor))
                ref = add('<< /Type /Font /Subtype /Type0 /BaseFont /%s /Encoding /%s /DescendantFonts [%d 0 R] >>'
                          % (info['base'], info['cmap'], descendant))
            font_refs.append('/%s %d 0 R' % (name, ref))
        image_refs = []
        for index, image in enumerate(self.images):
            extra = ''
            if image.get('smask'):
                mask = add(stream('/Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceGray '
                                  '/BitsPerComponent 8 /Filter /FlateDecode' % (image['width'], image['height']),
                                  image['smask']))
                extra += ' /SMask %d 0 R' % mask
            if image.get('parms'):
                extra += ' /DecodeParms ' + image['parms']
            ref = add(stream('/Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent %d '
                             '/Filter /%s%s' % (image['width'], image['height'], image['space'], image['bits'],
                                                image['filter'], extra), image['data']))
            image_refs.append('/Im%d %d 0 R' % (index + 1, ref))
        resources = add('<< /Font << %s >> /XObject << %s >> >>' % (' '.join(font_refs), ' '.join(image_refs)))
        kids = []
        for content in self.pages:
            body = zlib.compress('\n'.join(content).encode('latin-1'))
            content_ref = add(stream('/Filter /FlateDecode', body))
            kids.append(add('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources %d 0 R /Contents %d 0 R >>'
                            % (self.width, self.height, resources, content_ref)))
        info = add('<< /Title <%s> /Producer (Billsmith %s) >>'
                   % ((b'\xfe\xff' + title.encode('utf-16-be')).hex(), VERSION))
        objects[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
        objects[1] = ('<< /Type /Pages /Kids [%s] /Count %d >>'
                      % (' '.join('%d 0 R' % k for k in kids), len(kids))).encode('latin-1')
        out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets = []
        for number, body in enumerate(objects, 1):
            offsets.append(len(out))
            out += ('%d 0 obj\n' % number).encode('latin-1') + body + b'\nendobj\n'
        xref = len(out)
        out += ('xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)).encode('latin-1')
        for offset in offsets:
            out += ('%010d 00000 n \n' % offset).encode('latin-1')
        out += ('trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n'
                % (len(objects) + 1, info, xref)).encode('latin-1')
        return bytes(out)


# --------------------------------------------------------------------------
# PDF layout
# --------------------------------------------------------------------------

INK = (0.10, 0.11, 0.14)
SOFT = (0.27, 0.29, 0.33)
MUTED = (0.45, 0.47, 0.52)
RULE = (0.87, 0.88, 0.90)
MARGIN = 48.0
TOP = 50.0


def render_pdf(view, engine, logo):
    page_w, page_h = PAGE_SIZES[view['page_size']]
    pdf = Pdf(page_w, page_h, engine)
    left, right = MARGIN, page_w - MARGIN
    content_w = right - left
    bottom = page_h - 64.0
    accent, on_accent = view['accent_rgb'], view['on_accent']
    pdf.new_page()

    def heading(text):
        return text.upper()

    # ---- header: seller on the left, title and document facts on the right
    y_left = TOP
    left_w = content_w * 0.52
    seller = view['seller']
    if logo:
        scale = min(170.0 / logo['width'], 62.0 / logo['height'])
        w, h = logo['width'] * scale, logo['height'] * scale
        pdf.image(logo, left, y_left, w, h)
        y_left += h + 12
        name_size = 11.0
    else:
        name_size = 14.0
    for line in engine.wrap(seller['name'], name_size, True, left_w):
        pdf.text(left, y_left + name_size * 0.8, line, name_size, True, INK)
        y_left += name_size * 1.25
    y_left += 3
    for raw in seller['lines']:
        for line in engine.wrap(raw, 9, False, left_w):
            pdf.text(left, y_left + 7.5, line, 9, False, SOFT)
            y_left += 12

    right_w = content_w * 0.44
    y_right = TOP
    title_size = 22.0
    while title_size > 12 and engine.width(view['title'], title_size, True) > right_w:
        title_size -= 1
    pdf.text(right, y_right + title_size * 0.8, engine.fit(view['title'], title_size, True, right_w),
             title_size, True, accent, 'right')
    y_right += title_size * 1.2 + 8
    value_w = max(engine.width(value, 9.5, True) for _, value in view['meta'])
    value_w = min(value_w, right_w * 0.62)
    for label, value in view['meta']:
        pdf.text(right, y_right + 8, engine.fit(value, 9.5, True, value_w), 9.5, True, INK, 'right')
        pdf.text(right - value_w - 10, y_right + 8,
                 engine.fit(label, 8.5, False, right_w - value_w - 10), 8.5, False, MUTED, 'right')
        y_right += 14.5

    y = max(y_left, y_right) + 18
    pdf.line(left, y, right, y, RULE, 0.6)
    y += 16

    # ---- parties
    parties = [(view['buyer_label'], view['buyer'])]
    if view['ship_to']:
        parties.append((view['ship_label'], view['ship_to']))
    col_w = (content_w - 24) / 2.0
    ends = []
    for index, (label, party) in enumerate(parties):
        x = left + index * (col_w + 24)
        py = y
        pdf.text(x, py + 6.5, heading(label), 7.5, True, accent)
        py += 13
        for line in engine.wrap(party['name'], 10.5, True, col_w):
            pdf.text(x, py + 8.5, line, 10.5, True, INK)
            py += 13.5
        for raw in party['lines']:
            for line in engine.wrap(raw, 9, False, col_w):
                pdf.text(x, py + 7.5, line, 9, False, SOFT)
                py += 12
        ends.append(py)
    y = max(ends) + 20

    # ---- line items
    columns = view['columns']
    pad = 8.0
    widths = {}
    for key, label, _ in columns[1:]:
        widest = max([engine.width(label, 8, True)] + [engine.width(item[key], 9.5) for item in view['items']])
        widths[key] = widest + 2 * pad
    widths['description'] = max(content_w - sum(widths.values()), 120.0)
    scale = content_w / sum(widths.values())
    if scale < 0.999:  # only when the numeric columns alone are wider than the page
        for key in widths:
            widths[key] *= scale

    def table_header(top):
        pdf.rect(left, top, content_w, 22, accent)
        x = left
        for key, label, align in columns:
            w = widths[key]
            label = engine.fit(label, 8, True, w - 2 * pad)
            if align == 'right':
                pdf.text(x + w - pad, top + 14.2, label, 8, True, on_accent, 'right')
            else:
                pdf.text(x + pad, top + 14.2, label, 8, True, on_accent)
            x += w
        return top + 22

    y = table_header(y)
    desc_w = widths['description'] - 2 * pad
    for item in view['items']:
        # (text, size, colour, line height, baseline offset)
        cell = [(line, 9.5, INK, 12.5, 8.0) for line in engine.wrap(item['description'], 9.5, False, desc_w)]
        if item['details']:
            cell[-1] = cell[-1][:3] + (14.5, 8.0)
            cell.extend((line, 8.5, MUTED, 11.0, 7.0) for line in engine.wrap(item['details'], 8.5, False, desc_w))
        row_h = 8 + sum(part[3] for part in cell) + 6
        if y + row_h > bottom and row_h <= bottom - TOP - 22:
            pdf.new_page()
            y = table_header(TOP)
        x = left + widths['description']
        for key, _, _ in columns[1:]:
            w = widths[key]
            pdf.text(x + w - pad, y + 16, engine.fit(item[key], 9.5, False, w - pad), 9.5, False, INK, 'right')
            x += w
        y += 8
        for line, size, color, line_h, offset in cell:
            if y + line_h > bottom:  # only rows taller than a whole page reach this
                pdf.new_page()
                y = table_header(TOP) + 8
            pdf.text(left + pad, y + offset, line, size, False, color)
            y += line_h
        y += 6
        pdf.line(left, y, right, y, RULE, 0.5)
    y += 16

    # ---- totals (right) and notes (left)
    totals = view['totals']
    sizes = {'normal': 9.5, 'muted': 8.5, 'bold': 10.5, 'highlight': 11.5}
    heights = {'normal': 18.0, 'muted': 15.0, 'bold': 22.0, 'highlight': 30.0}
    block_w = 0.0
    for label, value, style in totals:
        bold = style in ('bold', 'highlight')
        block_w = max(block_w, engine.width(label, sizes[style], bold) + engine.width(value, sizes[style], bold) + 44)
    block_w = min(max(block_w, 220.0), content_w)
    block_h = sum(heights[style] for _, _, style in totals) + 6
    if y + block_h > bottom:
        pdf.new_page()
        y = TOP
    totals_top = y
    x0 = right - block_w
    for label, value, style in totals:
        h = heights[style]
        size = sizes[style]
        if style == 'highlight':
            y += 4
            pdf.rect(x0, y, block_w, h - 4, accent)
            pdf.text(x0 + 10, y + 17.3, label, size, True, on_accent)
            pdf.text(right - 10, y + 17.3, value, size, True, on_accent, 'right')
            y += h - 4
            continue
        if style == 'bold':
            pdf.line(x0, y + 2, right, y + 2, RULE, 0.8)
            y += 4
            h -= 4
        color = MUTED if style == 'muted' else INK
        pdf.text(x0 + 10, y + h * 0.5 + size * 0.36, label, size, style == 'bold', color if style != 'normal' else SOFT)
        pdf.text(right - 10, y + h * 0.5 + size * 0.36, value, size, style == 'bold', color, 'right')
        y += h
    y_after_totals = y

    notes_w = content_w - block_w - 28
    side_by_side = notes_w >= 190
    if side_by_side:
        y = totals_top
    else:
        notes_w = content_w
        y = y_after_totals + 18
    for heading_text, body in view['blocks']:
        lines = engine.wrap(body, 9, False, notes_w)
        if y + 14 + 12 > bottom:
            pdf.new_page()
            y = TOP
        pdf.text(left, y + 6.5, heading(heading_text), 7.5, True, accent)
        y += 14
        for line in lines:
            if y + 12 > bottom:
                pdf.new_page()
                y = TOP
            pdf.text(left, y + 7.5, line, 9, False, SOFT)
            y += 12
        y += 12

    # ---- footers
    count = len(pdf.pages)
    for index in range(count):
        page = pdf.pages[index]
        pdf.pages.append(page)  # make this page current for drawing
        if view['footer']:
            pdf.text(page_w / 2.0, page_h - 34, engine.fit(view['footer'], 8, False, content_w - 120),
                     8, False, MUTED, 'center')
        if count > 1:
            pdf.text(right, page_h - 34, view['page_label'].format(page=index + 1, pages=count),
                     8, False, MUTED, 'right')
        pdf.pages.pop()
    return pdf.build('%s %s' % (view['title'], view['number'])), count


# --------------------------------------------------------------------------
# HTML renderer (used for scripts the PDF fonts cannot draw, or on request)
# --------------------------------------------------------------------------

HTML_STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f3f4f6;color:#1a1c23;font:14px/1.45 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans","PingFang TC","Microsoft JhengHei",sans-serif}
.sheet{max-width:820px;margin:24px auto;background:#fff;padding:48px;box-shadow:0 1px 4px rgba(0,0,0,.12)}
.head{display:flex;justify-content:space-between;gap:32px}.seller .name{font-size:19px;font-weight:700}
.seller img{max-width:220px;max-height:80px;display:block;margin-bottom:12px}.muted{color:#5b606b}
.docinfo{text-align:right}.docinfo h1{margin:0 0 10px;font-size:30px;color:var(--accent);letter-spacing:.02em}
.docinfo table{margin-left:auto;border-collapse:collapse}.docinfo td{padding:2px 0 2px 14px;text-align:right}
.docinfo td.k{color:#727680;font-size:12.5px}.docinfo td.v{font-weight:600}
hr{border:0;border-top:1px solid #dfe1e6;margin:24px 0 20px}.parties{display:flex;gap:32px}.parties>div{flex:1}
.tag{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);margin-bottom:4px}
.party .name{font-weight:700;font-size:15px}table.items{width:100%;border-collapse:collapse;margin-top:26px}
table.items th{background:var(--accent);color:var(--on-accent);font-size:11.5px;text-transform:uppercase;
letter-spacing:.04em;padding:8px 10px;text-align:right}table.items th.l,table.items td.l{text-align:left}
table.items td{padding:10px;border-bottom:1px solid #dfe1e6;text-align:right;vertical-align:top;white-space:nowrap}
table.items td.l{white-space:normal}.details{color:#727680;font-size:12.5px;white-space:pre-line}
.below{display:flex;justify-content:space-between;gap:32px;margin-top:22px}.blocks{flex:1;white-space:pre-line}
.blocks .tag{margin-top:14px}.blocks .tag:first-child{margin-top:0}table.totals{border-collapse:collapse;min-width:290px}
table.totals td{padding:5px 12px}table.totals td.v{text-align:right;white-space:nowrap}
table.totals tr.bold td{font-weight:700;font-size:15.5px;border-top:1.5px solid #dfe1e6;padding-top:8px}
table.totals tr.muted td{color:#727680;font-size:12.5px}
table.totals tr.highlight td{background:var(--accent);color:var(--on-accent);font-weight:700;font-size:16.5px;
padding:9px 12px}.footer{margin-top:36px;text-align:center;color:#727680;font-size:12px}
@media print{body{background:#fff}.sheet{margin:0;max-width:none;box-shadow:none;padding:0}
table.items thead{display:table-header-group}table.items tr,table.totals{break-inside:avoid}
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}@page{size:PAGE_SIZE;margin:14mm}
"""


def render_html(view, logo_path, warnings):
    e = html.escape

    def party_html(party):
        lines = ''.join('<div class="muted">%s</div>' % e(line) for line in party['lines'])
        return '<div class="name">%s</div>%s' % (e(party['name']).replace('\n', '<br>'), lines)

    logo_tag = ''
    if logo_path:
        try:
            with open(logo_path, 'rb') as handle:
                blob = handle.read()
            kinds = ((b'\x89PNG', 'png'), (b'\xff\xd8', 'jpeg'), (b'GIF8', 'gif'), (b'RIFF', 'webp'), (b'<svg', 'svg+xml'),
                     (b'<?xm', 'svg+xml'))
            kind = next((mime for magic, mime in kinds if blob.startswith(magic)), None)
            if kind is None or len(blob) > 3000000:
                warnings.append('The logo was left out: use a PNG, JPEG, GIF, WebP or SVG file under 3 MB.')
            else:
                logo_tag = '<img alt="" src="data:image/%s;base64,%s">' % (kind, base64.b64encode(blob).decode('ascii'))
        except OSError as exc:
            warnings.append('The logo was left out: %s.' % exc.strerror)
    meta = ''.join('<tr><td class="k">%s</td><td class="v">%s</td></tr>' % (e(k), e(v)) for k, v in view['meta'])
    parties = '<div class="party"><div class="tag">%s</div>%s</div>' % (e(view['buyer_label']), party_html(view['buyer']))
    if view['ship_to']:
        parties += '<div class="party"><div class="tag">%s</div>%s</div>' % (e(view['ship_label']), party_html(view['ship_to']))
    head = ''.join('<th%s>%s</th>' % (' class="l"' if align == 'left' else '', e(label))
                   for _, label, align in view['columns'])
    body = []
    for item in view['items']:
        cells = []
        for key, _, align in view['columns']:
            if key == 'description':
                details = '<div class="details">%s</div>' % e(item['details']) if item['details'] else ''
                cells.append('<td class="l">%s%s</td>' % (e(item['description']).replace('\n', '<br>'), details))
            else:
                cells.append('<td>%s</td>' % e(item[key]))
        body.append('<tr>%s</tr>' % ''.join(cells))
    totals = ''.join('<tr class="%s"><td>%s</td><td class="v">%s</td></tr>' % (style, e(label), e(value))
                     for label, value, style in view['totals'])
    blocks = ''.join('<div class="tag">%s</div><div class="muted">%s</div>' % (e(h), e(b)) for h, b in view['blocks'])
    footer = '<div class="footer">%s</div>' % e(view['footer']) if view['footer'] else ''
    on_accent = '#1a1c23' if view['on_accent'][0] < 0.5 else '#ffffff'
    style = HTML_STYLE.replace('PAGE_SIZE', 'letter' if view['page_size'] == 'LETTER' else 'A4')
    return (
        '<!doctype html>\n<html lang="%s"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>%s %s</title><style>:root{--accent:%s;--on-accent:%s}%s</style></head><body><div class="sheet">'
        '<div class="head"><div class="seller">%s%s</div><div class="docinfo"><h1>%s</h1><table>%s</table></div></div>'
        '<hr><div class="parties">%s</div><table class="items"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
        '<div class="below"><div class="blocks">%s</div><table class="totals">%s</table></div>%s</div></body></html>\n'
    ) % (e(view['lang']), e(view['title']), e(view['number']), view['accent'], on_accent, style, logo_tag,
         party_html(view['seller']), e(view['title']), meta, parties, head, ''.join(body), blocks, totals, footer)


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def generate(spec, out_path=None, fmt='auto', base_dir='.', check_only=False):
    """Build the document described by spec. Returns the JSON-ready summary."""
    model = build_model(spec)
    view, warnings, formatter = model['view'], model['warnings'], model['formatter']
    summary = OrderedDict(ok=True)
    summary.update(model['summary'])

    strings = view_strings(view)
    engine = TextEngine(view['lang'], ''.join(strings))
    if formatter.symbol and not engine.supports(formatter.symbol) and fmt != 'html':
        # The PDF fonts cannot draw this currency sign: fall back to the ISO code.
        spec = dict(spec, currency_symbol=model['currency'], currency_position='prefix')
        model = build_model(spec)
        view, formatter = model['view'], model['formatter']
        summary.update(model['summary'])
        strings = view_strings(view)
        engine = TextEngine(view['lang'], ''.join(strings))
        warnings.append('The currency sign is not available in the PDF fonts, so the code %s is shown instead.'
                        % model['currency'])
    missing = sorted(set(ch for s in strings for ch in s if ch != '\n' and engine.font_key(ch) is None))
    if fmt == 'auto':
        fmt = 'html' if missing else 'pdf'
        if missing:
            warnings.append('Some text uses characters the built-in PDF fonts cannot draw (%s), so a print-ready '
                            'HTML file was produced instead. Open it in a browser and print to PDF.'
                            % ' '.join(missing[:12]))
    elif fmt == 'pdf' and missing:
        warnings.append('These characters cannot be drawn in the PDF and appear as "?": %s' % ' '.join(missing[:12]))

    summary['format'] = fmt
    if check_only:
        summary['file'] = None
        summary['warnings'] = warnings
        return summary

    logo_path = view['logo']
    if logo_path and not os.path.isabs(logo_path):
        logo_path = os.path.join(base_dir, logo_path)
    if not out_path:
        stem = re.sub(r'[^A-Za-z0-9._-]+', '-', '%s-%s' % (view['type'].replace('_', '-'), view['number'])).strip('-.')
        out_path = (stem or view['type']) + '.' + fmt
    elif not out_path.lower().endswith('.' + fmt):
        out_path = os.path.splitext(out_path)[0] + '.' + fmt

    if fmt == 'pdf':
        logo = None
        if logo_path:
            try:
                logo = load_image(logo_path)
            except OSError as exc:
                warnings.append('The logo was left out: %s.' % (exc.strerror or exc))
            except (ImageError, zlib.error, struct.error, ValueError, IndexError) as exc:
                warnings.append('The logo was left out: %s.' % exc)
        data, pages = render_pdf(view, engine, logo)
        summary['pages'] = pages
    else:
        data = render_html(view, logo_path, warnings).encode('utf-8')
    with open(out_path, 'wb') as handle:
        handle.write(data)
    summary['file'] = os.path.abspath(out_path)
    summary['warnings'] = warnings
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description='Render an invoice, quote or receipt from a JSON spec.')
    parser.add_argument('spec', help='path to the JSON spec, or - to read it from standard input')
    parser.add_argument('-o', '--output', help='output file path (default: <type>-<number>.pdf in the current folder)')
    parser.add_argument('--format', choices=('auto', 'pdf', 'html'), default='auto',
                        help='auto writes a PDF, or HTML when the text needs fonts the PDF cannot use')
    parser.add_argument('--check', action='store_true', help='validate and compute totals without writing a file')
    args = parser.parse_args(argv)

    def finish(payload, code):
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
        return code

    try:
        if args.spec == '-':
            raw, base_dir = sys.stdin.read(), '.'
        else:
            with open(args.spec, 'r', encoding='utf-8-sig') as handle:
                raw = handle.read()
            base_dir = os.path.dirname(os.path.abspath(args.spec))
        spec = json.loads(raw)
    except OSError as exc:
        return finish({'ok': False, 'errors': ['Cannot read the spec file: %s' % (exc.strerror or exc)]}, 1)
    except ValueError as exc:
        return finish({'ok': False, 'errors': ['The spec is not valid JSON: %s' % exc]}, 2)
    try:
        return finish(generate(spec, args.output, args.format, base_dir, args.check), 0)
    except SpecError as exc:
        return finish({'ok': False, 'errors': exc.errors}, 2)
    except OSError as exc:
        return finish({'ok': False, 'errors': ['Cannot write the output file: %s' % (exc.strerror or exc)]}, 1)
    except Exception as exc:  # keep the output machine-readable whatever happens
        return finish({'ok': False, 'errors': ['Unexpected error: %s: %s' % (type(exc).__name__, exc)]}, 1)


if __name__ == '__main__':
    sys.exit(main())
