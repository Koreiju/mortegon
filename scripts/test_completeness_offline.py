"""Offline completeness audit -- pick the most content-rich noetic snapshot,
run the pipeline, and verify that no tagged content is lost between
tagger -> trie -> chunker -> render.

Reports:
  - tagged xpaths (from content_tagger) vs. chunk-member-subtree coverage
  - media URLs tagged (images/video) vs. URLs present in chunk html_raw
  - rendered text coverage of tagged visible strings (sampled)
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from backend.dom.pipeline import run_pipeline


import os
SNAPSHOT = Path(os.environ.get("SNAPSHOT", "snapshots/noetic.org_blog_our-bodies-know__1776989279_b8c6a0cd.html"))


def _xpath_in_subtree(needle: str, root: str) -> bool:
    if needle == root:
        return True
    if not root.endswith("/"):
        root = root + "/"
    return needle.startswith(root)


def main() -> None:
    html = SNAPSHOT.read_text(encoding="utf-8", errors="replace")
    print(f"Loaded snapshot: {SNAPSHOT.name} ({len(html)} bytes)")

    result = run_pipeline(
        html_source=html,
        url="https://noetic.org/blog/our-bodies-know/",
        persist=False,
        render_instances=True,
        embed_instances=False,
    )

    trie = result.trie
    chunks = result.chunks
    instances = result.instances
    tagged = result.tagged

    print(f"\npatterns={len(trie.patterns)}  chunks={len(chunks)}  instances={len(instances)}")

    # Build xpath->tags index from all_tags (xpath is the authoritative field)
    tags_by_xpath: dict[str, list] = defaultdict(list)
    for tag in tagged.all_tags:
        tags_by_xpath[tag.xpath].append(tag)
    tag_paths = set(tags_by_xpath.keys())

    # bucket index for per-category reporting
    tag_by_bucket: dict[str, set[str]] = defaultdict(set)
    for tag in tagged.all_tags:
        tag_by_bucket[f"{tag.category}/{tag.subcategory}"].add(tag.xpath)

    print(f"tagged xpaths: {len(tag_paths)} across {len(tag_by_bucket)} buckets")

    # 1. Subtree coverage
    member_roots: list[str] = []
    for ch in chunks:
        member_roots.extend(ch.member_xpaths or [])
    print(f"chunk member roots: {len(member_roots)}")

    def covered(xp: str) -> bool:
        for root in member_roots:
            if _xpath_in_subtree(xp, root):
                return True
        return False

    uncovered = [xp for xp in tag_paths if not covered(xp)]
    print(f"uncovered tagged xpaths: {len(uncovered)}")
    for xp in uncovered[:10]:
        tlist = tags_by_xpath[xp]
        kinds = {(t.category, t.subcategory) for t in tlist}
        value_preview = next((t.value for t in tlist if t.value), "")[:60]
        print(f"    {xp}  kinds={sorted(kinds)}  value={value_preview!r}")

    print("\n  bucket -> (tagged, uncovered):")
    for bucket, xps in sorted(tag_by_bucket.items()):
        u = sum(1 for xp in xps if not covered(xp))
        flag = "  <-- LOSS" if u else ""
        print(f"    {bucket}: {len(xps)} tagged, {u} uncovered{flag}")

    # 2. Media URL coverage in instance html_raw
    image_urls = {t.value for t in tagged.all_tags
                  if t.category == "media" and t.subcategory == "images" and t.value}
    video_urls = {t.value for t in tagged.all_tags
                  if t.category == "media" and t.subcategory == "video" and t.value}

    html_raw_blob = "\n".join(getattr(i, "html_raw", "") or "" for i in instances)
    missing_imgs = [u for u in image_urls if u not in html_raw_blob]
    missing_vids = [u for u in video_urls if u not in html_raw_blob]
    print(
        f"\nmedia URL coverage: images tagged={len(image_urls)} missing={len(missing_imgs)}, "
        f"videos tagged={len(video_urls)} missing={len(missing_vids)}"
    )
    for u in missing_imgs[:10]:
        print(f"    missing image: {u}")
    for u in missing_vids[:10]:
        print(f"    missing video: {u}")

    # 3. Rendered-text coverage of visible text tags (values, not xpaths!)
    visible_vals = sorted({t.value.strip() for t in tagged.all_tags
                           if t.category == "text" and t.subcategory == "visible"
                           and isinstance(t.value, str) and t.value.strip()})

    rendered_parts: list[str] = []
    for inst in instances:
        rt = getattr(inst, "rendered_text", "") or ""
        if rt:
            rendered_parts.append(rt)
        # also include raw html so we catch text that's inside attributes
        hr = getattr(inst, "html_raw", "") or ""
        if hr:
            rendered_parts.append(hr)
    rendered_blob = "\n".join(rendered_parts).lower()

    hits = sum(1 for t in visible_vals if t.lower()[:40] in rendered_blob)
    total = max(1, len(visible_vals))
    print(f"\nvisible-text value coverage: {hits}/{len(visible_vals)} "
          f"({100.0 * hits / total:.1f}%)")
    missing_visible = [t for t in visible_vals if t.lower()[:40] not in rendered_blob]
    for t in missing_visible[:10]:
        print(f"    missing visible text: {t[:80]!r}")


if __name__ == "__main__":
    sys.exit(main() or 0)
