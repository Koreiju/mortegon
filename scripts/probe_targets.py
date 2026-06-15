"""Quick Selenium-driven probe: which archive.org URLs render content?

Standalone diagnostic — does NOT depend on the chunker pipeline. Just
opens a list of URLs, waits up to 8s for body innerText to populate,
and prints (url, body_text_len, first_card_xpath_or_None, title).

Run: python scripts/probe_targets.py
"""
from __future__ import annotations

import os
import sys
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("WFH_NO_PROFILE", "1")


def main() -> None:
    from backend.services.selenium_client import WebBrowserManager

    targets = [
        "https://www.archive.org/",
        "https://archive.org/details/",
        "https://archive.org/details/movies",
        "https://archive.org/details/texts",
        "https://blog.archive.org/",
        "https://en.wikipedia.org/wiki/Internet_Archive",
        "https://news.ycombinator.com/",
    ]

    mgr = WebBrowserManager()
    drv = mgr.get_driver()

    for url in targets:
        try:
            drv.get(url)
        except Exception as exc:
            print(f"  {url}\n    NAV ERROR: {exc}")
            continue
        # Wait for body to populate
        deadline = time.time() + 8.0
        body_len = 0
        while time.time() < deadline:
            try:
                body_len = drv.execute_script(
                    "return document.body && document.body.innerText "
                    "? document.body.innerText.length : 0;"
                )
            except Exception:
                body_len = -1
                break
            if body_len > 200:
                break
            time.sleep(0.1)
        try:
            title = drv.title or ""
        except Exception:
            title = ""
        # Sample a few candidate card-shaped elements
        sample = ""
        try:
            sample = drv.execute_script("""
                var sel = ['article','li.item-ia','.card','[data-collection-id]',
                           '.collection-tile','tile','.item','.search-results .item'];
                for (var i = 0; i < sel.length; i++) {
                    var els = document.querySelectorAll(sel[i]);
                    if (els.length > 0) {
                        return sel[i] + ' x' + els.length;
                    }
                }
                return '(no card-shaped elements matched)';
            """) or ""
        except Exception as exc:
            sample = f"(probe failed: {exc})"
        print(f"  {url}")
        print(f"    title:    {title[:80]}")
        print(f"    body len: {body_len}")
        print(f"    cards:    {sample}")
        print()


if __name__ == "__main__":
    main()
