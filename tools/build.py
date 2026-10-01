#!/usr/bin/env python3
"""Sync shared skill files, validate a plugin against the OpenAI plugin
directory rules, and write the upload ZIP to dist/.

    python3 tools/build.py billsmith            # sync + validate + zip
    python3 tools/build.py billsmith --check    # validate only, change nothing

Rules checked here mirror https://developers.openai.com/plugins/deploy/submission-errors
for a skills-only package. Standard library only.
"""

import argparse
import json
import os
import re
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES = {'Productivity', 'Creativity', 'Developer Tools', 'Business & Operations', 'Data & Analytics',
              'Communication', 'Education & Research', 'Security', 'Finance', 'Healthcare', 'Travel',
              'Entertainment', 'Other'}
# Files every skill shares; the first skill listed owns the canonical copy.
SHARED = {
    'billsmith': ('create-invoice', ['scripts/billdoc.py', 'references/spec.md', 'assets/icon.png']),
}
SKIP = {'.DS_Store', '__pycache__'}


def one_line(text):
    return '\n' not in text and '\r' not in text


def contrast(hex_color, against):
    def luminance(value):
        channels = []
        for i in (1, 3, 5):
            c = int(value[i:i + 2], 16) / 255.0
            channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    a, b = sorted((luminance(hex_color), luminance(against)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def png_size(path):
    with open(path, 'rb') as handle:
        head = handle.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', head[16:24])


def front_matter(path):
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    if not match:
        return None, ''
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(':')
        if sep:
            fields[key.strip()] = value.strip().strip('"')
    return fields, match.group(2)


def validate(plugin_dir):
    errors = []
    manifest_path = os.path.join(plugin_dir, '.codex-plugin', 'plugin.json')
    try:
        with open(manifest_path, encoding='utf-8') as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        return ['Cannot read %s: %s' % (manifest_path, exc)], None

    def check(condition, message):
        if not condition:
            errors.append(message)

    name = manifest.get('name', '')
    check(re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name) and len(name) <= 64, 'name must be lowercase kebab-case, <= 64 chars')
    check(re.match(r'^\d+\.\d+\.\d+$', manifest.get('version', '')), 'version must be semantic, e.g. 1.0.0')
    check(0 < len(manifest.get('description', '')) <= 1024, 'description is required, <= 1024 chars')
    author = manifest.get('author') or {}
    check(0 < len(author.get('name', '')) <= 120, 'author.name is required, <= 120 chars')
    check(str(author.get('url', 'https://')).startswith('https://'), 'author.url must be HTTPS')
    check(manifest.get('skills') == './skills/', 'skills must be "./skills/"')
    for forbidden in ('mcpServers', 'apps', 'hooks'):
        check(forbidden not in manifest, '%s is not allowed in a skills-only package' % forbidden)
    for forbidden in ('.mcp.json', 'mcp.json', '.app.json', 'hooks'):
        check(not os.path.exists(os.path.join(plugin_dir, forbidden)), '%s is not allowed in a skills-only package' % forbidden)

    ui = manifest.get('interface') or {}
    for key, limit in (('displayName', 30), ('shortDescription', 30), ('developerName', 80)):
        value = ui.get(key, '')
        check(0 < len(value) <= limit and one_line(value), 'interface.%s is required, one line, <= %d chars (now %d)'
              % (key, limit, len(value)))
    check(0 < len(ui.get('longDescription', '')) <= 4000, 'interface.longDescription is required, <= 4000 chars')
    check(ui.get('category') in CATEGORIES, 'interface.category must be a supported category')
    capabilities = ui.get('capabilities')
    check(isinstance(capabilities, list) and len(capabilities) <= 20
          and all(0 < len(c) <= 120 and one_line(c) for c in capabilities), 'interface.capabilities: <= 20 one-line entries, <= 120 chars')
    for key in ('websiteURL', 'supportURL', 'privacyPolicyURL', 'termsOfServiceURL'):
        value = ui.get(key, '')
        check(value.startswith('https://') and len(value) <= 1024 and '@' not in value, 'interface.%s must be an HTTPS URL' % key)
    prompts = ui.get('defaultPrompt', [])
    prompts = [prompts] if isinstance(prompts, str) else prompts
    check(len(prompts) <= 3 and len(set(p.strip().lower() for p in prompts)) == len(prompts)
          and all(0 < len(p) <= 128 and one_line(p) and '@' not in p for p in prompts),
          'interface.defaultPrompt: <= 3 unique one-line prompts, <= 128 chars, no @mentions')
    check('screenshots' not in ui, 'interface.screenshots is not allowed in a skills-only package')
    color = ui.get('brandColor')
    if color is not None:
        check(re.match(r'^#[0-9A-Fa-f]{6}$', color) and contrast(color, '#FFFFFF') >= 2, 'interface.brandColor needs 2:1 contrast on white')
    for key in ('logo', 'composerIcon'):
        value = ui.get(key, '')
        path = os.path.join(plugin_dir, value)
        if not (value.startswith('./') and os.path.isfile(path)):
            errors.append('interface.%s must be a ./ path to an existing file' % key)
            continue
        size = png_size(path)
        check(size and size[0] == size[1] and 48 <= size[0] <= 4096 and os.path.getsize(path) <= 5 * 1024 * 1024,
              'interface.%s must be a square PNG, 48-4096 px, <= 5 MiB' % key)

    extension = (manifest.get('extensions') or {}).get('com.openai') or {}
    for locale, entry in ((extension.get('publication') or {}).get('translations') or {}).items():
        subtitle, description = entry.get('subtitle'), entry.get('description')
        check(subtitle is None or (0 < len(subtitle.strip()) and len(subtitle) <= 30 and one_line(subtitle)),
              'translations.%s.subtitle must be one line, <= 30 chars (now %d)' % (locale, len(subtitle or '')))
        check(description is None or (0 < len(description.strip()) and len(description) <= 4000 and '\t' not in description),
              'translations.%s.description must be <= 4000 chars without tabs' % locale)

    skills_dir = os.path.join(plugin_dir, 'skills')
    skills = sorted(d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))) \
        if os.path.isdir(skills_dir) else []
    check(skills, 'at least one skill is required under skills/')
    seen = set()
    for skill in skills:
        check(not skill.startswith('.'), 'skill directory %s must not be hidden' % skill)
        skill_md = os.path.join(skills_dir, skill, 'SKILL.md')
        if not os.path.isfile(skill_md):
            errors.append('skills/%s/SKILL.md is missing' % skill)
            continue
        fields, body = front_matter(skill_md)
        if fields is None:
            errors.append('skills/%s/SKILL.md must start with YAML front matter' % skill)
            continue
        skill_name, description = fields.get('name', ''), fields.get('description', '')
        check(skill_name == skill, 'skills/%s: front matter name should match the folder name' % skill)
        check(skill_name not in seen, 'skills/%s: duplicate skill name' % skill)
        seen.add(skill_name)
        check(len('%s:%s' % (name, skill_name)) <= 64, 'skills/%s: plugin:skill identity exceeds 64 chars' % skill)
        check(0 < len(description) <= 1024, 'skills/%s: description is required, <= 1024 chars (now %d)' % (skill, len(description)))
        check(body.strip(), 'skills/%s: the instructions are empty' % skill)
        for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', body):
            if not link.startswith(('http://', 'https://')):
                check(os.path.exists(os.path.join(skills_dir, skill, link)), 'skills/%s: broken link %s' % (skill, link))
        agent = os.path.join(skills_dir, skill, 'agents', 'openai.yaml')
        if os.path.isfile(agent):
            with open(agent, encoding='utf-8') as handle:
                text = handle.read()
            for key in ('display_name', 'short_description'):
                check(re.search(r'^\s+%s:\s*"[^"]+"\s*$' % key, text, re.M), 'skills/%s: agents/openai.yaml needs interface.%s' % (skill, key))
            for icon in re.findall(r'^\s+icon_(?:small|large):\s*"([^"]+)"', text, re.M):
                check(os.path.isfile(os.path.join(skills_dir, skill, icon)), 'skills/%s: icon %s is missing' % (skill, icon))
    return errors, manifest


def sync(plugin, plugin_dir, write):
    """Copy shared files from the owning skill into the others. Returns stale paths."""
    stale = []
    if plugin not in SHARED:
        return stale
    owner, files = SHARED[plugin]
    skills_dir = os.path.join(plugin_dir, 'skills')
    for skill in sorted(os.listdir(skills_dir)):
        if skill == owner or not os.path.isdir(os.path.join(skills_dir, skill)):
            continue
        for rel in files:
            with open(os.path.join(skills_dir, owner, rel), 'rb') as handle:
                source = handle.read()
            target = os.path.join(skills_dir, skill, rel)
            current = None
            if os.path.isfile(target):
                with open(target, 'rb') as handle:
                    current = handle.read()
            if current != source:
                stale.append(os.path.relpath(target, ROOT))
                if write:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, 'wb') as handle:
                        handle.write(source)
    return stale


def package(plugin, plugin_dir, version):
    os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
    out = os.path.join(ROOT, 'dist', '%s-%s.zip' % (plugin, version))
    entries = []
    for folder, dirs, files in os.walk(plugin_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for name in sorted(files):
            if name in SKIP or name.endswith('.pyc'):
                continue
            path = os.path.join(folder, name)
            entries.append((path, plugin + '/' + os.path.relpath(path, plugin_dir).replace(os.sep, '/')))
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, arcname in entries:
            info = zipfile.ZipInfo(arcname, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(path, 'rb') as handle:
                archive.writestr(info, handle.read())
    return out, len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plugin')
    parser.add_argument('--check', action='store_true', help='validate only; do not sync or write the ZIP')
    args = parser.parse_args()
    plugin_dir = os.path.join(ROOT, 'plugins', args.plugin)
    if not os.path.isdir(plugin_dir):
        sys.exit('No such plugin: %s' % plugin_dir)

    stale = sync(args.plugin, plugin_dir, write=not args.check)
    errors, manifest = validate(plugin_dir)
    if args.check and stale:
        errors.append('shared files are out of date (run without --check): %s' % ', '.join(stale))
    elif stale:
        print('synced: %s' % ', '.join(stale))
    if errors:
        print('%d problem(s):' % len(errors))
        for error in errors:
            print('  - ' + error)
        sys.exit(1)
    if args.check:
        print('OK: %s %s passes the package checks' % (manifest['name'], manifest['version']))
        return
    out, count = package(args.plugin, plugin_dir, manifest['version'])
    print('OK: wrote %s (%d files, %.1f KB)' % (os.path.relpath(out, ROOT), count, os.path.getsize(out) / 1024.0))


if __name__ == '__main__':
    main()
