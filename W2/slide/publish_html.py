#!/usr/bin/env python3
"""Export a public HTML deck without changing its private presenter original.

Usage: python3 publish_html.py [presenter.html public.html]
Defaults: week1-presenter.html -> week1.html in this script's directory.
"""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile


ATTRIBUTE = re.compile(r'''\s+([^\s=/>]+)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?''')
REMARK_NOTES = re.compile(r"^[ \t]*\?\?\?[ \t]*\r?$.*?(?=^[ \t]*---[ \t]*\r?$|\Z)", re.M | re.S)


class Deck(HTMLParser):
    # Treat remark's Markdown as text; apparent HTML in it is slide content.
    CDATA_CONTENT_ELEMENTS = ("script", "style", "textarea")

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text, self.edits, self.styles = text, [], []
        self.lines = [0] + [m.end() for m in re.finditer("\n", text)]
        self.note_start, self.note_depth = None, 0
        self.style_start = self.textarea_start = self.head_end = None
        self.feed(text)
        self.close()
        if self.note_start is not None or self.textarea_start is not None:
            raise ValueError("Unclosed speaker-note element or source textarea")

    def position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start, raw, attributes = self.position(), self.get_starttag_text(), dict(attrs)
        if tag == "aside":
            if self.note_depth:
                self.note_depth += 1
            elif "notes" in (attributes.get("class") or "").split():
                self.note_start, self.note_depth = start, 1
        if not self.note_depth:
            # Tokenize this genuine start tag, never JavaScript string contents.
            for match in ATTRIBUTE.finditer(raw):
                if match.group(1).lower() == "data-notes":
                    self.edits.append((start + match.start(), start + match.end(), ""))
        if tag == "style":
            self.style_start = (start, start + len(raw), bool(self.note_depth))
        if tag == "textarea" and attributes.get("id") == "source":
            self.textarea_start = start + len(raw)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        start = self.position()
        end = self.text.index(">", start) + 1
        if tag == "head":
            self.head_end = start
        if tag == "style" and self.style_start is not None:
            opening, content, in_notes = self.style_start
            self.styles.append((self.text[content:start].strip(), self.text[opening:end], in_notes))
            self.style_start = None
        if tag == "textarea" and self.textarea_start is not None:
            if not self.note_depth:
                for match in REMARK_NOTES.finditer(self.text[self.textarea_start:start]):
                    self.edits.append((self.textarea_start + match.start(), self.textarea_start + match.end(), ""))
            self.textarea_start = None
        if tag == "aside" and self.note_depth:
            self.note_depth -= 1
            if not self.note_depth:
                self.edits.append((self.note_start, end, ""))
                self.note_start = None


def public_html(text):
    deck = Deck(text)
    # Quarto can nest math accessibility CSS inside notes; retain each rule once.
    retained = {body for body, _, in_notes in deck.styles if not in_notes}
    needed = []
    for body, markup, in_notes in deck.styles:
        if in_notes and re.search(r"MJX|MathJax", body) and body not in retained:
            needed.append(markup)
            retained.add(body)
    if needed:
        if deck.head_end is None:
            raise ValueError("Cannot preserve math styles: missing </head>")
        deck.edits.append((deck.head_end, deck.head_end, "\n".join(needed) + "\n"))
    for start, end, replacement in sorted(deck.edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    if Deck(text).edits:
        raise ValueError("Public export still contains speaker notes")
    return text


def publish_html(source, destination):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve() or (
        destination.exists() and source.samefile(destination)
    ):
        raise ValueError("Source and output must differ; preserve the presenter original")
    result = public_html(source.read_bytes().decode("utf-8"))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(result.encode("utf-8"))
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=here / "week1-presenter.html")
    parser.add_argument("output", nargs="?", type=Path, default=here / "week1.html")
    args = parser.parse_args()
    result = publish_html(args.source, args.output)
    print(f"Published without speaker notes: {result}")


if __name__ == "__main__":
    main()
