#!/usr/bin/env python3
"""Generate the static Billsmith website (docs/billsmith) served by GitHub Pages.

    python3 tools/make_site.py
"""

import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'billsmith')
REPO = 'https://github.com/williiam/chatgpt-plugins'
PUBLISHER = 'williiam'
PUBLISHER_URL = 'https://github.com/williiam'

STYLE = """
:root{--ink:#1a1c23;--soft:#4a4e58;--muted:#6f7480;--rule:#e2e4ea;--bg:#f6f7f9;--card:#fff;--accent:#1f4fbf}
@media (prefers-color-scheme:dark){:root{--ink:#eceef3;--soft:#c3c7d1;--muted:#9197a5;--rule:#2c303a;--bg:#14161b;--card:#1c1f26;--accent:#8fb0ff}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
header,main,footer{max-width:760px;margin:0 auto;padding:0 20px}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-top:28px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px;font-weight:700;font-size:18px;color:var(--ink);text-decoration:none}
.brand img{width:36px;height:36px;border-radius:9px}
nav a{color:var(--soft);text-decoration:none;margin-left:18px;font-size:15px}nav a:first-child{margin-left:0}
nav a:hover,nav a[aria-current]{color:var(--accent)}
main{padding-top:36px;padding-bottom:48px}
h1{font-size:34px;line-height:1.2;margin:0 0 12px;letter-spacing:-.01em}
h2{font-size:20px;margin:36px 0 8px}
h3{font-size:17px;margin:22px 0 4px}
p,li{color:var(--soft)}a{color:var(--accent)}
.lead{font-size:19px;color:var(--soft);margin:0 0 8px}
.meta{color:var(--muted);font-size:14px}
.card{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:18px 20px;margin:14px 0}
.card p{margin:6px 0}
.prompt{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:14.5px;color:var(--ink);overflow-wrap:anywhere}
ul{padding-left:22px}
footer{border-top:1px solid var(--rule);padding-top:18px;padding-bottom:36px;color:var(--muted);font-size:14px}
footer a{color:var(--muted)}
"""

NAV = [('index.html', 'Overview'), ('support.html', 'Support'), ('privacy.html', 'Privacy'), ('terms.html', 'Terms')]

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{DESCRIPTION}">
<link rel="icon" type="image/png" href="icon.png">
<style>{STYLE}</style>
</head>
<body>
<header>
<a class="brand" href="index.html"><img src="icon.png" alt="">Billsmith</a>
<nav>{NAV}</nav>
</header>
<main>
{BODY}
</main>
<footer>
Billsmith is an independent plugin published by <a href="{PUBLISHER_URL}">{PUBLISHER}</a>. It is not made or endorsed by OpenAI.
</footer>
</body>
</html>
"""

PAGES = {}

PAGES['index.html'] = ('Billsmith Invoice Generator', 'Create invoices, quotes and receipts as PDF files in ChatGPT and Codex.', """
<h1>Invoices, quotes and receipts, straight from a chat</h1>
<p class="lead">Billsmith is a plugin for ChatGPT and Codex. Describe the work, and it produces a clean PDF you can send right away, with every figure calculated exactly.</p>

<h2>What you can ask for</h2>
<div class="card"><p class="prompt">Invoice Acme Robotics for 32 hours of web design at $95/hour, 8.5% sales tax, net 30. From Northwind Studio LLC.</p></div>
<div class="card"><p class="prompt">Quote for Harbor Cafe: new website 3,500 EUR, logo refresh 800 EUR, 19% VAT, valid two weeks.</p></div>
<div class="card"><p class="prompt">Receipt for Maria Lopez: she paid 1,200 USD rent for October by bank transfer today.</p></div>

<h2>What it handles</h2>
<ul>
<li>Invoices, proforma invoices, credit notes, quotes, estimates and receipts</li>
<li>Line items with quantities, units, per-line discounts and detail lines</li>
<li>One or several taxes, mixed rates per line and tax-inclusive prices</li>
<li>Document discounts, shipping, withholding deductions, deposits and part payments</li>
<li>Your logo and brand colour, A4 or Letter pages, multi-page documents</li>
<li>Labels in English, Traditional and Simplified Chinese, Japanese, Korean, Spanish, French, German, Portuguese, Italian and Dutch</li>
</ul>

<h2>How it works</h2>
<p>Billsmith is a set of skills with a small bundled script. The script does the arithmetic with exact decimal maths and draws the page, so totals are not estimated by the model and the same input always gives the same document. It runs inside your own ChatGPT or Codex session. Billsmith has no server and no account, and nothing you type is sent to the publisher.</p>

<h2>What it does not do</h2>
<p>Billsmith creates files only. It does not send documents, collect payments, keep customer records or file anything with a tax authority. It does not give tax advice: it applies the rates you provide. It does not produce government e-invoice formats.</p>

<h2>Source</h2>
<p>The plugin is open source under the MIT licence: <a href="{REPO}">github.com/williiam/chatgpt-plugins</a>.</p>
""")

PAGES['support.html'] = ('Support - Billsmith', 'How to get help with the Billsmith plugin.', """
<h1>Support</h1>
<p class="lead">Questions, bug reports and feature requests are welcome.</p>

<h2>Contact</h2>
<div class="card">
<p>Open an issue at <a href="{REPO}/issues">github.com/williiam/chatgpt-plugins/issues</a>. Issues are public, so leave out anything confidential and replace real names and amounts with examples.</p>
<p>Replies normally arrive within three working days.</p>
</div>

<h2>What to include in a bug report</h2>
<ul>
<li>What you asked for, and what you expected</li>
<li>What happened instead, including any warning Billsmith reported</li>
<li>Whether you used ChatGPT or Codex</li>
</ul>

<h2>Common questions</h2>
<h3>Some characters show as question marks, or the result is an HTML file</h3>
<p>The PDF can draw Latin-alphabet languages, Chinese, Japanese and Korean. For other scripts, such as Cyrillic, Arabic or Thai, Billsmith writes a print-ready HTML page. Open it in a browser and choose Print, then Save as PDF.</p>
<h3>My logo was left out</h3>
<p>Use a PNG or JPEG file. Transparent PNG files should be smaller than about 1200 by 1200 pixels.</p>
<h3>Which tax rate should I charge?</h3>
<p>Billsmith applies the rate you give it and cannot tell you which rate applies to your business. Please check with an accountant or your tax authority.</p>
<h3>Can it send the invoice or take payment?</h3>
<p>No. Billsmith only creates the file.</p>
""")

PAGES['privacy.html'] = ('Privacy policy - Billsmith', 'Privacy policy for the Billsmith plugin.', """
<h1>Privacy policy</h1>
<p class="meta">Effective 1 October 2026</p>
<p class="lead">Billsmith does not collect your data. This page explains what that means in detail.</p>

<h2>Who this covers</h2>
<p>This policy covers the Billsmith plugin for ChatGPT and Codex and this website. Billsmith is published by {PUBLISHER} (<a href="{PUBLISHER_URL}">github.com/williiam</a>), referred to below as "the publisher".</p>

<h2>Personal data collected by the plugin</h2>
<p>None. Billsmith consists of instructions and a script that run inside your own ChatGPT or Codex session. It has no server, makes no network requests, uses no analytics and has no account system. The names, addresses, amounts, bank details and logos you provide are used only within your session to create your document. The publisher never receives them and cannot access them.</p>

<h2>Purposes of use</h2>
<p>Because the publisher receives no data from the plugin, the publisher does not use your data for any purpose.</p>

<h2>Recipients</h2>
<p>The publisher does not share, sell or transfer personal data, because it holds none. Your conversation and any files created in it are processed by OpenAI as the provider of ChatGPT and Codex, under <a href="https://openai.com/policies/privacy-policy/">OpenAI's privacy policy</a> and your settings there.</p>

<h2>Retention</h2>
<p>The publisher retains nothing. Documents you create stay in your ChatGPT or Codex session, or on your own device, and are kept or deleted according to your OpenAI settings and your own choices.</p>

<h2>This website and support requests</h2>
<p>This website is static and sets no cookies. It is hosted on GitHub Pages; GitHub may log technical data such as IP addresses to operate the service, as described in the <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub privacy statement</a>. If you open a support issue on GitHub, whatever you post there is public and is handled under GitHub's terms. You can edit or delete your own issues and comments at any time.</p>

<h2>Your controls</h2>
<p>You decide what information to put into a document. You can remove the plugin at any time from the plugins page in ChatGPT or Codex, and manage or delete your conversations and files in your OpenAI settings.</p>

<h2>Children</h2>
<p>Billsmith is a business tool and is not directed at children under 13.</p>

<h2>Changes</h2>
<p>If this policy changes, the new version will be posted here with a new effective date.</p>

<h2>Contact</h2>
<p>Questions about this policy: open an issue at <a href="{REPO}/issues">github.com/williiam/chatgpt-plugins/issues</a>.</p>
""")

PAGES['terms.html'] = ('Terms of service - Billsmith', 'Terms of service for the Billsmith plugin.', """
<h1>Terms of service</h1>
<p class="meta">Effective 1 October 2026</p>
<p class="lead">By installing or using Billsmith you agree to these terms.</p>

<h2>The service</h2>
<p>Billsmith is a plugin for ChatGPT and Codex that creates invoices, quotes, estimates, receipts and related documents from the details you provide. It is published by {PUBLISHER} (<a href="{PUBLISHER_URL}">github.com/williiam</a>) and its source code is available under the MIT licence. Your use of ChatGPT and Codex themselves is governed by your agreement with OpenAI.</p>

<h2>Your responsibilities</h2>
<ul>
<li>You are responsible for the accuracy of everything you put into a document, including names, amounts, tax rates and payment details. Review each document before you send it.</li>
<li>You are responsible for making sure your documents meet the legal, tax and invoicing requirements that apply to you.</li>
<li>Use Billsmith only for genuine transactions of your own business or of a business you are authorised to act for. Do not use it to create false, misleading or fraudulent documents, or documents in the name of someone you do not represent.</li>
</ul>

<h2>No professional advice</h2>
<p>Billsmith does not provide tax, legal or accounting advice. It applies the rates and terms you supply. Consult a qualified professional for advice about your situation.</p>

<h2>No warranty</h2>
<p>Billsmith is provided "as is", without warranty of any kind, express or implied, including warranties of merchantability, fitness for a particular purpose and non-infringement.</p>

<h2>Limitation of liability</h2>
<p>To the fullest extent permitted by law, the publisher is not liable for any indirect, incidental, special or consequential damages, or for any loss of profits, revenue or data, arising from your use of Billsmith or from documents created with it.</p>

<h2>Changes</h2>
<p>These terms may be updated. The new version will be posted here with a new effective date, and continued use after that date means you accept it.</p>

<h2>Contact</h2>
<p>Questions about these terms: open an issue at <a href="{REPO}/issues">github.com/williiam/chatgpt-plugins/issues</a>.</p>
""")


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (title, description, body) in PAGES.items():
        nav = ''.join('<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if href == name else '', label)
                      for href, label in NAV)
        page = SHELL
        for key, value in (('{BODY}', body.strip()), ('{TITLE}', title), ('{DESCRIPTION}', description),
                           ('{STYLE}', STYLE), ('{NAV}', nav), ('{REPO}', REPO), ('{PUBLISHER_URL}', PUBLISHER_URL),
                           ('{PUBLISHER}', PUBLISHER)):
            page = page.replace(key, value)
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as handle:
            handle.write(page)
    shutil.copyfile(os.path.join(ROOT, 'plugins', 'billsmith', 'assets', 'icon.png'), os.path.join(OUT, 'icon.png'))
    with open(os.path.join(ROOT, 'docs', '.nojekyll'), 'w'):
        pass
    with open(os.path.join(ROOT, 'docs', 'index.html'), 'w', encoding='utf-8') as handle:
        handle.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                     '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                     '<title>williiam plugins</title>\n<meta http-equiv="refresh" content="0; url=billsmith/">\n'
                     '</head>\n<body>\n<p><a href="billsmith/">Billsmith Invoice Generator</a></p>\n</body>\n</html>\n')
    print('wrote %d pages to %s' % (len(PAGES), os.path.relpath(OUT, ROOT)))


if __name__ == '__main__':
    main()
