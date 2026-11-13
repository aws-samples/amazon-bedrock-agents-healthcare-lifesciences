"""Static checks that the frontend stays compatible with its Content-Security-Policy.

The CloudFront policy sets script-src 'self', so the browser refuses inline
scripts, inline event handlers (onclick="..."), javascript: URLs, and eval.
Markup uses data-click / data-change / data-submit (see frontend/actions.js).
"""

import pathlib
import re

import pytest

FRONTEND = pathlib.Path(__file__).resolve().parents[2] / "frontend"
SOURCES = sorted(FRONTEND.glob("*.html")) + sorted(FRONTEND.glob("*.js"))
INLINE_HANDLER = re.compile(r"""\son[a-z]+\s*=\s*["'\\]""", re.IGNORECASE)


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_no_inline_event_handlers(path):
    text = path.read_text()
    if path.name == "actions.js":
        # Its header comment describes the onclick="..." pattern it replaces.
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    assert not INLINE_HANDLER.search(text)


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_no_eval_or_javascript_urls(path):
    text = path.read_text()
    assert "javascript:" not in text
    assert not re.search(r"\beval\(|new Function\(|set(Timeout|Interval)\(\s*['\"`]", text)


@pytest.mark.parametrize("page", sorted(FRONTEND.glob("*.html")), ids=lambda p: p.name)
def test_pages_use_only_external_same_origin_scripts(page):
    html = page.read_text()
    scripts = re.findall(r"<script\b[^>]*>", html)
    assert scripts, "page has no scripts"
    for tag in scripts:
        src = re.search(r'src="([^"]+)"', tag)
        assert src, f"inline <script> block: {tag}"
        assert not re.match(r"https?:|//", src.group(1)), f"external script: {tag}"
    assert html.index('src="actions.js') < min(
        html.index(f'src="{name}') for name in ("app.js", "project.js", "settings.js") if f'src="{name}' in html
    ), "actions.js must load before the page script"


def test_every_action_in_markup_has_a_handler():
    text = "\n".join(p.read_text() for p in SOURCES)
    used = set(re.findall(r"""data-(?:click|change|submit)=\\?["']([A-Za-z]+)""", text))
    registered = set(re.findall(r"Actions\.on\('([A-Za-z]+)'", text))
    assert used, "no actions found"
    assert used <= registered, f"actions without a handler: {sorted(used - registered)}"
