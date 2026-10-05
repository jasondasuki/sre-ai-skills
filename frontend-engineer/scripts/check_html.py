#!/usr/bin/env python3
"""Static checks for a hand-built or generated HTML page or fragment (stdlib only).

Usage: check_html.py FILE [--allow-scripts] [--allow-external]

Errors (exit 1): mismatched or unclosed tags, duplicate ids, in-page links to a missing id,
<svg> without role/<title>/<desc>, <img> without alt, <table> without <th>, external
resources, and <script> unless --allow-scripts. Warnings (exit 0): heading level jumps,
more than one <h1>, links that open a new tab without rel="noopener".
"""
import re
import sys
from html.parser import HTMLParser

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
# Tags inside <svg> that html.parser lowercases but that are self-closed by convention.
SVG_SELF = {'path', 'rect', 'circle', 'line', 'polyline', 'polygon', 'ellipse', 'stop', 'use'}


class Checker(HTMLParser):
    def __init__(self, allow_scripts, allow_external):
        super().__init__(convert_charrefs=True)
        self.allow_scripts, self.allow_external = allow_scripts, allow_external
        self.stack, self.errors, self.warnings = [], [], []
        self.ids, self.links = {}, []
        self.last_heading, self.h1 = 0, 0
        self.svgs = []        # [has_role, has_title, has_desc, line]
        self.tables = []      # [has_th, line]
        self.in_svg = 0

    def err(self, msg):
        self.errors.append(f'line {self.getpos()[0]}: {msg}')

    def warn(self, msg):
        self.warnings.append(f'line {self.getpos()[0]}: {msg}')

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            if a['id'] in self.ids:
                self.err(f'duplicate id "{a["id"]}"')
            self.ids[a['id']] = self.getpos()[0]
        href = a.get('href') or ''
        if tag == 'a' and href.startswith('#') and len(href) > 1:
            self.links.append((href[1:], self.getpos()[0]))
        if tag == 'a' and a.get('target') == '_blank' and 'noopener' not in (a.get('rel') or ''):
            self.warn('target=_blank link without rel="noopener"')
        for key in ('src', 'href'):
            val = a.get(key) or ''
            if re.match(r'(https?:)?//', val) and tag in ('script', 'img', 'link', 'iframe', 'source', 'video', 'audio') \
                    and not self.allow_external:
                self.err(f'external resource <{tag} {key}="{val[:60]}">')
        if re.search(r'url\(\s*[\'"]?(https?:)?//', a.get('style') or '') and not self.allow_external:
            self.err('external url() in a style attribute')
        if tag == 'script' and not self.allow_scripts:
            self.err('<script> is not allowed here (use CSS-only interaction, or pass --allow-scripts)')
        if tag == 'img' and 'alt' not in a:
            self.err('<img> without alt')
        if tag == 'svg':
            self.in_svg += 1
            self.svgs.append([a.get('role') == 'img', False, False, self.getpos()[0]])
        if self.in_svg and tag == 'title':
            self.svgs[-1][1] = True
        if self.in_svg and tag == 'desc':
            self.svgs[-1][2] = True
        if tag == 'table':
            self.tables.append([False, self.getpos()[0]])
        if tag == 'th' and self.tables:
            self.tables[-1][0] = True
        m = re.fullmatch(r'h([1-6])', tag)
        if m:
            n = int(m.group(1))
            self.h1 += n == 1
            if self.last_heading and n > self.last_heading + 1:
                self.warn(f'heading jumps from h{self.last_heading} to h{n}')
            self.last_heading = n
        if tag in VOID or (self.in_svg and tag in SVG_SELF):
            return
        self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        # Self-closing syntax (<path/>): process attributes, but never push.
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1][0] == tag and tag not in VOID:
            self.stack.pop()
        if tag == 'svg':
            self.in_svg -= 1

    def handle_endtag(self, tag):
        if tag in VOID or (self.in_svg and tag in SVG_SELF):
            return
        if tag == 'svg':
            self.in_svg = max(0, self.in_svg - 1)
        if not self.stack:
            self.err(f'stray </{tag}>')
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        names = [t for t, _ in self.stack]
        if tag in names:
            while self.stack[-1][0] != tag:
                t, ln = self.stack.pop()
                self.err(f'<{t}> opened on line {ln} is not closed before </{tag}>')
            self.stack.pop()
        else:
            self.err(f'stray </{tag}>')

    def finish(self):
        for t, ln in self.stack:
            self.errors.append(f'line {ln}: <{t}> is never closed')
        for target, ln in self.links:
            if target not in self.ids:
                self.errors.append(f'line {ln}: link to #{target} has no matching id')
        for role, title, desc, ln in self.svgs:
            if not (role and title and desc):
                self.errors.append(f'line {ln}: <svg> needs role="img", <title> and <desc>')
        for has_th, ln in self.tables:
            if not has_th:
                self.errors.append(f'line {ln}: <table> has no <th> header cells')
        if self.h1 > 1:
            self.warnings.append(f'{self.h1} <h1> elements; use one per page')


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        print(__doc__)
        return 2
    text = open(args[0], encoding='utf-8').read()
    c = Checker('--allow-scripts' in argv, '--allow-external' in argv)
    c.feed(text)
    c.close()
    c.finish()
    for w in c.warnings:
        print('WARN:  ' + w)
    for e in c.errors:
        print('ERROR: ' + e)
    print(f'{len(c.errors)} error(s), {len(c.warnings)} warning(s), {len(c.ids)} id(s), {len(c.svgs)} svg(s)')
    return 1 if c.errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
