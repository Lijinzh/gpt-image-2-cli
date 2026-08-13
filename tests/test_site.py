from __future__ import annotations

import runpy
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOC_SECTIONS = {
    "getting-started": "GETTING STARTED",
    "using": "USING",
    "features": "FEATURES",
    "guides": "GUIDES AND TUTORIALS",
    "developer-guide": "DEVELOPER GUIDE",
    "reference": "REFERENCE",
}


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


def parse_site(page: Path | None = None) -> SiteParser:
    parser = SiteParser()
    parser.feed((page or DOCS / "index.html").read_text(encoding="utf-8"))
    return parser


def test_site_has_required_public_content() -> None:
    parser = parse_site()
    content = " ".join(parser.text)
    assert "复制一句话，交给 Codex" in content
    assert "四步进入生成循环" in content
    assert "八部电影，八种像素叙事" in content
    assert "键盘方向键或触摸滑动" in content
    assert "双日落 · 星球大战" in content
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    assert 'data-title="月面黑石 · 2001 太空漫游"' in html
    assert 'data-title="城门决斗 · 特洛伊"' in html
    assert 'data-title="雨夜教堂 · 康斯坦丁灵感"' in html
    assert "Made by Golden Philosophy" in content
    assert "© 2026 Golden Philosophy. All rights reserved." in content
    assert "API KEY SAFETY" in content
    assert "打开意见反馈窗口" in content
    assert "前往 GitHub 提交 Issue" in content
    assert "https://github.com/Lijinzh/gpt-image-2-cli" in (DOCS / "index.html").read_text(
        encoding="utf-8"
    )


def test_site_local_links_and_assets_resolve() -> None:
    pages = [DOCS / "index.html", DOCS / "en" / "index.html"]
    pages.extend(DOCS / section / "index.html" for section in DOC_SECTIONS)
    for page in pages:
        parser = parse_site(page)
        for reference in parser.references:
            parsed = urlparse(reference)
            if parsed.scheme or reference.startswith(("mailto:", "tel:")):
                continue
            if reference.startswith("#"):
                assert reference[1:] in parser.ids
                continue
            path = reference.split("#", 1)[0].split("?", 1)[0]
            if path:
                target = (page.parent / path).resolve()
                assert target.is_file() or (target / "index.html").is_file(), reference


def test_documentation_portal_has_all_sections() -> None:
    for section, marker in DOC_SECTIONS.items():
        page = DOCS / section / "index.html"
        html = page.read_text(encoding="utf-8")
        content = " ".join(parse_site(page).text)
        assert marker in content
        assert 'href="../docs-page.css"' in html
        assert 'src="../docs-page.js"' in html
        assert html.count('class="doc-nav"') == 1
        for expected_section in DOC_SECTIONS:
            assert f'href="../{expected_section}/"' in html
    assert (DOCS / "docs-page.css").is_file()
    assert (DOCS / "docs-page.js").is_file()


def test_homepages_link_to_documentation() -> None:
    chinese = (DOCS / "index.html").read_text(encoding="utf-8")
    english = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert 'href="getting-started/">文档</a>' in chinese
    assert 'href="getting-started/">阅读完整文档</a>' in chinese
    assert 'href="../getting-started/">Docs</a>' in english
    assert 'href="../getting-started/">Read full docs</a>' in english


def test_english_site_is_complete_and_switchable() -> None:
    page = DOCS / "en" / "index.html"
    html = page.read_text(encoding="utf-8")
    content = " ".join(parse_site(page).text)
    assert '<html lang="en">' in html
    assert "Install once. Generate with confidence." in content
    assert "Eight films. Eight pixel-art stories." in content
    assert "Open feedback form" in content
    assert html.count("data-gallery-slide") == 8
    assert html.count("data-gallery-thumb=") == 8
    assert "Switch homepage visual theme" in html
    assert html.count('data-theme="') == 3
    assert 'href="../?lang=zh"' in html
    assert 'href="./?lang=en"' in html
    assert 'aria-current="page">EN</a>' in html
    assert 'hreflang="zh-CN"' in html
    assert 'hreflang="en"' in html


def test_site_javascript_and_css_are_wired() -> None:
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    javascript = (DOCS / "script.js").read_text(encoding="utf-8")
    stylesheet = (DOCS / "styles.css").read_text(encoding="utf-8")
    assert 'src="script.js"' in html
    assert 'href="styles.css"' in html
    assert 'href="assets/icons/pixel-space-operator.svg"' in html
    assert 'src="assets/icons/pixel-space-operator.png"' in html
    assert 'src="assets/examples/star-wars-twin-sunset.png"' in html
    assert 'src="assets/examples/space-odyssey-monolith.png"' in html
    assert 'src="assets/examples/troy-gates-duel.png"' in html
    assert 'src="assets/examples/spider-hero-rooftop.png"' in html
    assert 'src="assets/examples/iron-hero-workshop.png"' in html
    assert 'src="assets/examples/avengers-city-battle.png"' in html
    assert 'src="assets/examples/silence-prison-corridor.png"' in html
    assert 'src="assets/examples/constantine-cathedral.png"' in html
    assert ">GI<" not in html
    assert "data-copy-target" in javascript
    assert "website-feedback" in javascript
    assert "issues/new" in javascript
    assert "showModal" in javascript
    assert "data-gallery-carousel" in html
    assert "data-gallery-next" in html
    assert html.count("data-gallery-slide") == 8
    assert html.count("data-gallery-thumb=") == 8
    assert "data-gallery-copy" in javascript
    assert "data-gallery-use" in javascript
    assert "pointerdown" in javascript
    assert "ArrowRight" in javascript
    assert "gpt-image-site-language" in javascript
    assert "Copied to clipboard" in javascript
    assert "Feedback type" in javascript
    assert "data-theme-switcher" in html
    assert html.count('data-theme="') == 3
    assert "gpt-image-site-visual-theme" in javascript
    assert "applyVisualTheme" in javascript
    assert 'url("assets/examples/star-wars-twin-sunset.png")' in stylesheet
    assert 'url("assets/examples/silence-prison-corridor.png")' in stylesheet
    assert 'url("assets/examples/constantine-cathedral.png")' in stylesheet
    assert "operator-orbit" in stylesheet
    assert "prefers-reduced-motion" in stylesheet
    assert (DOCS / ".nojekyll").is_file()


def test_github_feedback_issue_form_exists() -> None:
    issue_form = ROOT / ".github" / "ISSUE_TEMPLATE" / "feedback.yml"
    content = issue_form.read_text(encoding="utf-8")
    assert issue_form.is_file()
    assert "name: 用户反馈 / User feedback" in content
    assert "  - feedback" in content
    assert "API Key" in content
    assert "required: true" in content


def test_gallery_prompts_match_the_cli_generation_manifest() -> None:
    pages = [
        (DOCS / "index.html").read_text(encoding="utf-8"),
        (DOCS / "en" / "index.html").read_text(encoding="utf-8"),
    ]
    manifest = runpy.run_path(
        str(ROOT / "scripts" / "generate_gallery_images.py"),
        run_name="gallery_manifest",
    )
    scenes = manifest["SCENES"]
    assert len(scenes) == 8
    for html in pages:
        for scene in scenes:
            assert scene.filename in html
            assert f'data-prompt="{scene.prompt}"' in html
