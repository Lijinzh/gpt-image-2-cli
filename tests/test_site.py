from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.references: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if identifier := attributes.get("id"):
            self.ids.add(identifier)
        for name in ("href", "src"):
            if reference := attributes.get(name):
                self.references.append(reference)

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def parse_site() -> SiteParser:
    parser = SiteParser()
    parser.feed((DOCS / "index.html").read_text(encoding="utf-8"))
    return parser


def test_site_has_required_public_content() -> None:
    parser = parse_site()
    content = " ".join(parser.text)
    assert "复制一句话，交给 Codex" in content
    assert "四步进入生成循环" in content
    assert "实际生成输出" in content
    assert "API KEY SAFETY" in content
    assert "https://github.com/Lijinzh/gpt-image-2-cli" in (DOCS / "index.html").read_text(
        encoding="utf-8"
    )


def test_site_local_links_and_assets_resolve() -> None:
    parser = parse_site()
    for reference in parser.references:
        parsed = urlparse(reference)
        if parsed.scheme or reference.startswith(("mailto:", "tel:")):
            continue
        if reference.startswith("#"):
            assert reference[1:] in parser.ids
            continue
        path = reference.split("#", 1)[0].split("?", 1)[0]
        if path:
            assert (DOCS / path).is_file(), reference


def test_site_javascript_and_css_are_wired() -> None:
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    javascript = (DOCS / "script.js").read_text(encoding="utf-8")
    stylesheet = (DOCS / "styles.css").read_text(encoding="utf-8")
    assert 'src="script.js"' in html
    assert 'href="styles.css"' in html
    assert "data-copy-target" in javascript
    assert "prefers-reduced-motion" in stylesheet
    assert (DOCS / ".nojekyll").is_file()
