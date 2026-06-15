# Test Generation Task: ctvnews_ca.html

Analyze the attached files and generate executable Python regression tests
following the patterns and rules from your system instructions.

## Attached Files

| File | Purpose | How to use |
|------|---------|------------|
| `source.html` | Original HTML page | Pass 1: Ground truth construction |
| `distilled.html` | Pipeline output | Pass 2: Gap analysis |
| `quality_report.txt` | Content tags, leaks, samples | Cross-reference with distilled |
| `selector_tree.json` | Universal xpath tree | Structural template reference |

## Chunk Inventory

- **Total chunks:** 93
- **Structural chunks:** 22
- **Text/Nav chunks:** 69
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `article.custom.false` (freq=18, pq_sig=`article(div(a(img)),h3(a),div)`)
  - Chunk 1: `article.image.list` (freq=20, pq_sig=`article(div(figure(a(img)),h2(a)),hr)`)
  - Chunk 2: `article.image.list` (freq=8, pq_sig=`article(div(figure(a(img,div(svg(path),span))),h2(`)
  - Chunk 3: `article.image.list` (freq=5, pq_sig=`div(div(div(article(div(figure(a),h2(a)),hr))))`)
  - Chunk 4: `li.chain.item` (freq=5, pq_sig=`li(div(a,button(span(svg(path)))),div(ul(li(a))))`)
  - Chunk 5: `div.custom.false` (freq=12, pq_sig=`div(a(h3),time)`)
  - Chunk 6: `article.custom.false` (freq=6, pq_sig=`article(div(a(img,div(div(svg(path))))),h2(a),div)`)
  - Chunk 7: `article.custom.false` (freq=4, pq_sig=`article(div(a(img)),h2(a),div)`)
  - Chunk 8: `a.canadas.challenges` (freq=2, pq_sig=`h2(a)`)
  - Chunk 9: `span.custom.duration` (freq=2, pq_sig=`div(span)`)
  - Chunk 10: `a.ca.ctvnews` (freq=4, pq_sig=`a(h2,svg(path))`)
  - Chunk 11: `article.grid.large` (freq=3, pq_sig=`div(div(div(article(figure(a(img)),div(div(h2)))))`)
  - Chunk 12: `article.grid.large` (freq=3, pq_sig=`div(div(div(article(figure(a(img,div)),div(div(h2)`)
  - Chunk 13: `div.footer.group` (freq=3, pq_sig=`div(h2,ul(li(a(span)),li(a(span)),li(a(span))))`)
  - Chunk 14: `ul.chain.header` (freq=3, pq_sig=`ul(li(a),li(a),li(a),li(a,a,a,a))`)
  - Chunk 15: `ul.chain.header` (freq=2, pq_sig=`ul(li(a),li(a,a))`)
  - Chunk 16: `ul.chain.header` (freq=2, pq_sig=`ul(li(a),li(a),li(a,a,a))`)
  - Chunk 17: `div.anchor.center` (freq=15, pq_sig=`div(a,button(span(svg(path))))`)
  - Chunk 18: `div.custom.header` (freq=13, pq_sig=`div(a(h2,svg(path)))`)
  - Chunk 19: `div.custom.image` (freq=13, pq_sig=`div(a(img))`)
  - Chunk 20: `div.false.large` (freq=6, pq_sig=`div(div(h2(a)))`)
  - Chunk 21: `li.footer.group` (freq=9, pq_sig=`li(a(span))`)

**Text/Nav chunks:**
  - Chunk 24: `[nav_content:a×113]` (freq=113)
  - Chunk 28: `[nav_content:a×21]` (freq=21)
  - Chunk 29: `[nav_content:a×17]` (freq=17)
  - Chunk 30: `[nav_content:a×19]` (freq=19)
  - Chunk 28: `[nav_content:a×21]` (freq=21)
  - Chunk 29: `[nav_content:a×17]` (freq=17)
  - Chunk 30: `[nav_content:a×19]` (freq=19)
  - Chunk 31: `[text_content:h2×1]` (freq=1)
  - Chunk 32: `[text_content:h2×1]` (freq=1)
  - Chunk 33: `[text_content:h2×1]` (freq=1)
  - Chunk 34: `[text_content:h2×1]` (freq=1)
  - Chunk 35: `[text_content:h2×1]` (freq=1)
  - Chunk 36: `[text_content:h3×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h3×1]` (freq=1)
  - Chunk 39: `[text_content:h3×1]` (freq=1)
  - Chunk 40: `[text_content:h3×1]` (freq=1)
  - Chunk 41: `[text_content:h3×1]` (freq=1)
  - Chunk 42: `[text_content:h3×1]` (freq=1)
  - Chunk 43: `[text_content:h3×1]` (freq=1)
  - Chunk 44: `[text_content:h2×1]` (freq=1)
  - Chunk 45: `[text_content:h3×1]` (freq=1)
  - Chunk 46: `[text_content:h3×1]` (freq=1)
  - Chunk 47: `[text_content:h3×1]` (freq=1)
  - Chunk 48: `[text_content:h3×1]` (freq=1)
  - Chunk 49: `[text_content:h2×1]` (freq=1)
  - Chunk 50: `[text_content:h2×1]` (freq=1)
  - Chunk 51: `[text_content:h2×1]` (freq=1)
  - Chunk 52: `[text_content:h3×1]` (freq=1)
  - Chunk 53: `[text_content:h2×1]` (freq=1)
  - Chunk 54: `[text_content:h2×1]` (freq=1)
  - Chunk 55: `[text_content:h2×1]` (freq=1)
  - Chunk 56: `[text_content:h2×1]` (freq=1)
  - Chunk 57: `[text_content:h3×1]` (freq=1)
  - Chunk 58: `[text_content:h3×1]` (freq=1)
  - Chunk 59: `[text_content:h3×1]` (freq=1)
  - Chunk 60: `[text_content:h3×1]` (freq=1)
  - Chunk 61: `[text_content:h3×1]` (freq=1)
  - Chunk 62: `[text_content:h3×1]` (freq=1)
  - Chunk 63: `[text_content:h3×1]` (freq=1)
  - Chunk 64: `[text_content:h3×1]` (freq=1)
  - Chunk 65: `[text_content:h2×1]` (freq=1)
  - Chunk 66: `[text_content:h2×1]` (freq=1)
  - Chunk 67: `[text_content:h2×1]` (freq=1)
  - Chunk 68: `[text_content:h2×1]` (freq=1)
  - Chunk 69: `[text_content:h2×1]` (freq=1)
  - Chunk 70: `[text_content:h2×1]` (freq=1)
  - Chunk 71: `[text_content:h2×1]` (freq=1)
  - Chunk 72: `[text_content:h2×1]` (freq=1)
  - Chunk 73: `[text_content:h2×1]` (freq=1)
  - Chunk 74: `[text_content:h2×1]` (freq=1)
  - Chunk 75: `[text_content:h2×1]` (freq=1)
  - Chunk 76: `[text_content:h2×1]` (freq=1)
  - Chunk 77: `[text_content:h2×1]` (freq=1)
  - Chunk 78: `[text_content:h2×1]` (freq=1)
  - Chunk 79: `[text_content:h2×1]` (freq=1)
  - Chunk 80: `[text_content:h2×1]` (freq=1)
  - Chunk 81: `[text_content:h3×1]` (freq=1)
  - Chunk 82: `[text_content:h3×1]` (freq=1)
  - Chunk 83: `[text_content:h3×1]` (freq=1)
  - Chunk 84: `[text_content:h3×1]` (freq=1)
  - Chunk 85: `[text_content:h3×1]` (freq=1)
  - Chunk 86: `[text_content:h3×1]` (freq=1)
  - Chunk 87: `[text_content:h3×1]` (freq=1)
  - Chunk 88: `[text_content:h3×1]` (freq=1)
  - Chunk 89: `[text_content:h3×1]` (freq=1)
  - Chunk 90: `[text_content:h3×1]` (freq=1)
  - Chunk 91: `[text_content:h3×1]` (freq=1)
  - Chunk 92: `[text_content:h3×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: ctvnews_ca.html ===
Chunks: 93 (structural=22, functional=9, text=62)
Categories: {'card': 16, 'menu_item': 9, 'structural': 4, 'search_input': 1, 'pagination': 1, 'text_singleton': 62}
Content: 337 tagged, 308 preserved (91%)
Leaks: 29 total, 14 high-importance

--- Chunk 0: article.custom.false ---
  type=card freq=18 excl=0.18
  pattern_xpath: ///article[contains(@data-style-alignment,'unset')][contains(@data-style-direction,'vertical')][contains(@class,'stack')][contains(@data-style-inline,'false')][contains(@data-style-justification,'start')]
  tree_sig: article(div(a(img)),h3(a),div)
  content: [HREF=2 IMG=4 TEXT=1]

--- Chunk 1: article.image.list ---
  type=card freq=20 excl=0.21
  pattern_xpath: ///article[contains(@class,'show')][contains(@class,'image')][contains(@class,'medium')][contains(@class,'table')][contains(@class,'top')]
  tree_sig: article(div(figure(a(img)),h2(a)),hr)
  content: [ATTR=1 HREF=2 IMG=5 TEXT=1]

--- Chunk 2: article.image.list ---
  type=card freq=8 excl=0.21
  pattern_xpath: ///article[contains(@class,'show')][contains(@class,'image')][contains(@class,'medium')][contains(@class,'table')][contains(@class,'top')]
  tree_sig: article(div(figure(a(img,div(svg(path),span))),h2(a)),hr)
  content: [ATTR=1 HREF=2 IMG=5 TEXT=2]

--- Chunk 3: article.image.list ---
  type=card freq=5 excl=0.21
  pattern_xpath: ///article[contains(@class,'show')][contains(@class,'image')][contains(@class,'medium')][contains(@class,'table')][contains(@class,'top')]
  tree_sig: div(div(div(article(div(figure(a),h2(a)),hr))))
  content: [ATTR=1 HREF=2 IMG=5 TEXT=1]

--- Chunk 4: li.chain.item ---
  type=menu_item freq=5 excl=0.27
  pattern_xpath: ///li[contains(@class,'section')][contains(@data-testid,'section')][contains(@data-testid,'chain')][contains(@data-testid,'item')][contains(@data-testid,'nav')]
  tree_sig: li(div(a,button(span(svg(path)))),div(ul(li(a))))
  content: [ATTR=1 HREF=2 TEXT=2]

--- Chunk 5: div.custom.false ---
  type=card freq=12 excl=0.41
  pattern_xpath: ///div[contains(@class,'simple')][contains(@class,'wrapper')][contains(@data-style-alignment,'unset')][contains(@data-style-direction,'vertical')][contains(@class,'stack')]
  tree_sig: div(a(h3),time)
  content: [HREF=1 TEXT=2]

--- Chunk 6: article.custom.false ---
  type=card freq=6 excl=0.18
  pattern_xpath: ///article[contains(@data-style-alignment,'unset')][contains(@data-style-direction,'vertical')][contains(@class,'stack')][contains(@data-style-inline,'false')][contains(@data-style-justification,'start')]
  tree_sig: article(div(a(img,div(div(svg(path))))),h2(a),div)
  content: [HREF=2 IMG=4 TEXT=1]

--- Chunk 7: article.custom.false ---
  type=card freq=4 excl=0.18
  pattern_xpath: ///article[contains(@data-style-alignment,'unset')][contains(@data-style-direction,'vertical')][contains(@class,'stack')][contains(@data-style-inline,'false')][contains(@data-style-justification,'start')]
  tree_sig: article(div(a(img)),h2(a),div)
  content: [HREF=2 IMG=4 TEXT=1]

--- Chunk 8: a.canadas.challenges ---
  type=structural freq=2 excl=0.14
  pattern_xpath: ///a[contains(@class,'link')]
  tree_sig: h2(a)
  content: [HREF=1 TEXT=1]

--- Chunk 9: span.custom.duration ---
  type=structural freq=2 excl=0.23
  pattern_xpath: ///span[contains(@class,'duration')][contains(@class,'item')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')]
  tree_sig: div(span)
  content: [TEXT=1]

--- Chunk 10: a.ca.ctvnews ---
  type=card freq=4 excl=0.06
  pattern_xpath: ///div[contains(@class,'grid')][contains(@class,'quad')][contains(@class,'children')]/a[contains(@class,'link')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')]
  tree_sig: a(h2,svg(path))
  content: [HREF=1 TEXT=1]

--- Chunk 11: article.grid.large ---
  type=card freq=3 excl=0.24
  pattern_xpath: ///article[contains(@class,'grid')][contains(@class,'large')][contains(@class,'table')][contains(@class,'top')][contains(@class,'list')]
  tree_sig: div(div(div(article(figure(a(img)),div(div(h2))))))
  content: [ATTR=1 HREF=2 IMG=5 TEXT=1]

--- Chunk 12: article.grid.large ---
  type=card freq=3 excl=0.24
  pattern_xpath: ///article[contains(@class,'grid')][contains(@class,'large')][contains(@class,'table')][contains(@class,'top')][contains(@class,'list')]
  tree_sig: div(div(div(article(figure(a(img,div)),div(div(h2))))))
  content: [ATTR=1 HREF=2 IMG=5 TEXT=2]

--- Chunk 13: div.footer.group ---
  type=card freq=3 excl=0.50
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'group')][contains(@class,'links')]
  tree_sig: div(h2,ul(li(a(span)),li(a(span)),li(a(span))))
  content: [HREF=3 TEXT=7]

--- Chunk 14: ul.chain.header ---
  type=card freq=3 excl=0.24
  pattern_xpath: ///ul[contains(@class,'menu')][contains(@id,'header')][contains(@id,'section')][contains(@id,'sub')][contains(@class,'chain')]
  tree_sig: ul(li(a),li(a),li(a),li(a,a,a,a))
  content: [HREF=7 TEXT=7]

--- Chunk 15: ul.chain.header ---
  type=structural freq=2 excl=0.35
  pattern_xpath: ///ul[contains(@id,'canada')][contains(@id,'world')][contains(@class,'menu')][contains(@id,'header')][contains(@id,'section')]
  tree_sig: ul(li(a),li(a,a))
  content: [HREF=3 TEXT=3]

--- Chunk 16: ul.chain.header ---
  type=structural freq=2 excl=0.35
  pattern_xpath: ///ul[contains(@id,'business')][contains(@id,'ottawa')][contains(@class,'menu')][contains(@id,'header')][contains(@id,'section')]
  tree_sig: ul(li(a),li(a),li(a,a,a))
  content: [HREF=5 TEXT=5]

--- Chunk 17: div.anchor.center ---
  type=card freq=15 excl=0.62
  pattern_xpath: ///div[contains(@data-style-alignment,'center')][contains(@data-style-direction,'horizontal')][contains(@class,'anchor')][contains(@data-testid,'section')][contains(@data-testid,'subsection')]
  tree_sig: div(a,button(span(svg(path))))
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 18: div.custom.header ---
  type=card freq=13 excl=0.06
  pattern_xpath: ///div[contains(@class,'child')][contains(@class,'triple')]//div[contains(@class,'header')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')]
  tree_sig: div(a(h2,svg(path)))
  content: [HREF=1 TEXT=1]

--- Chunk 19: div.custom.image ---
  type=card freq=13 excl=0.17
  pattern_xpath: ///div[contains(@class,'wrapper')][contains(@class,'image')][contains(@class,'item')][contains(@class,'standard')][contains(@class,'custom')]
  tree_sig: div(a(img))
  content: [HREF=1 IMG=4]

--- Chunk 20: div.false.large ---
  type=card freq=6 excl=0.38
  pattern_xpath: ///div[contains(@class,'grid')][contains(@class,'container')][contains(@class,'false')]//div[contains(@class,'text')][contains(@class,'large')][contains(@data-style-alignment,'unset')][contains(@data-style-direction,'vertical')][contains(@class,'stack')]
  tree_sig: div(div(h2(a)))
  content: [HREF=1 TEXT=1]

--- Chunk 21: li.footer.group ---
  type=menu_item freq=9 excl=0.32
  pattern_xpath: ///li[contains(@class,'footer')][contains(@class,'group')][contains(@class,'links')][contains(@class,'item')][contains(@class,'list')]
  tree_sig: li(a(span))
  content: [HREF=1 TEXT=2]

--- Chunk 22: [search_inputs] ---
  type=search_input freq=2 excl=1.00
  pattern_xpath: ///input[contains(@autocapitalize,'none')][contains(@autocomplete,'off')][contains(@autocorrect,'off')][contains(@id,'queryly')][contains(@spellcheck,'false')]
  content: [ATTR=2]

--- Chunk 23: [pagination_buttons] ---
  type=pagination freq=31 excl=0.14
  pattern_xpath: ///a[contains(@class,'link')]
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:a×113] ---
  type=menu_item freq=113 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 28: [nav_content:a×21] ---
  type=menu_item freq=21 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 29: [nav_content:a×17] ---
  type=menu_item freq=17 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 30: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 28: [nav_content:a×21] ---
  type=menu_item freq=21 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 29: [nav_content:a×17] ---
  type=menu_item freq=17 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 30: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 31: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h2[contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h2[contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///div[contains(@class,'double')][contains(@class,'child')]/h2[contains(@class,'medium')][contains(@class,'header')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 38: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 39: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 40: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 41: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 42: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 43: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 44: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 46: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 47: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 48: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 49: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 50: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///div[contains(@class,'picks')][contains(@class,'story')][contains(@class,'feed')]//h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 51: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///div[contains(@class,'trends')][contains(@class,'shopping')][contains(@class,'feed')]//h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 52: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03 LEAKS=12
  pattern_xpath: ///div[contains(@class,'grid')][contains(@class,'quad')][contains(@class,'children')]//h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=30 TEXT=30]
  LEAKS (high):
    [HREF] /canada/article/in-exclusive-analysis-former-canadian-defence-chief-says-we-can-no-longer- (href not in rendered output)
    [HREF] /opinion/article/tfsa-might-be-the-better-tax-choice-this-rrsp-season-dale-jackson/ (href not in rendered output)
    [HREF] /business/article/quiet-quitting-vs-quitting-which-one-actually-hurts-your-finances-more/ (href not in rendered output)
    [HREF] /world/article/the-daughters-left-holding-the-damage-what-the-epstein-files-mean-for-beatr (href not in rendered output)
    [HREF] https://www.ctvnews.ca/shopping/gifts/best-advent-calendars-2025-canada.html (href not in rendered output)
  LEAKS (medium):
    [TEXT] In exclusive analysis, former Canadian defence chief says we can no lo
    [TEXT] TFSA might be the better tax choice this RRSP season: Dale Jackson
    [TEXT] Quiet quitting vs. quitting: Which one actually hurts your finances mo

--- Chunk 53: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h2[contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 54: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.45
  pattern_xpath: ///div[contains(@class,'double')][contains(@class,'child')]//h2[contains(@class,'manual')][contains(@class,'promo')][contains(@class,'medium')][contains(@class,'title')][contains(@class,'custom')]
  content: [HREF=1 TEXT=1]

--- Chunk 55: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 56: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 57: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 58: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 59: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 60: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 61: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 62: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 63: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 64: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03 LEAKS=2
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [HREF=20 TEXT=20]
  LEAKS (high):
    [HREF] /montreal/article/auto-thefts-down-18-year-over-year-while-recovery-remains-low-report/ (href not in rendered output)
    [HREF] /climate-and-environment/article/tropical-cyclone-gezani-hits-madagascar-and-kills-at-leas (href not in rendered output)
  LEAKS (medium):
    [TEXT] Canadian ice dancers Gilles, Poirier earn long-awaited Olympic bronze 
    [TEXT] Auto thefts down 18% year-over-year while recovery remains low: report
    [TEXT] Tropical Cyclone Gezani hits Madagascar and kills at least 31

--- Chunk 65: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 66: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 67: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 68: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 69: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 70: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 71: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 72: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 73: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 74: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 75: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 76: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 77: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'title')][contains(@class,'standard')][contains(@class,'custom')][contains(@class,'list')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 78: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h2[contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 79: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h2[contains(@class,'heading')]
  content: [HREF=1 TEXT=1]

--- Chunk 80: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'bmw')][contains(@class,'is')][contains(@class,'only')][contains(@class,'reader')][contains(@class,'screen')]
  content: [TEXT=1]

--- Chunk 81: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 82: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 83: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 84: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 85: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 86: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 87: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 88: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 89: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 90: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 91: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 92: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@style,'heading')][contains(@style,'truncation')][contains(@class,'heading')]
  content: [TEXT=1]

```

## Your Task

1. Read `source.html` — identify all repeating patterns, count atoms,
   note which content signals (headline, link, image) each atom carries
2. Read `quality_report.txt` and `distilled.html` — find segmentation gaps
   using the taxonomy: NESTED_ATOM, OVER_SEGMENTATION, MISSING_IMAGE,
   MISSING_LINK, MISSING_CHUNK, CROSS_CHUNK_DUPE, SELF_DUPE_TEXT
3. Generate a Python test file covering ALL applicable categories from
   the system prompt (cards, menus, text, search, pagination, images,
   cross-chunk duplication, coverage)
4. Use filename `ctvnews_ca.html` in all `_distill()` calls
5. Name the module `test_ctvnews_ca_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
