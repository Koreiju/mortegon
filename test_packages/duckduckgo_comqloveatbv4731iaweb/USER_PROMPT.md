# Test Generation Task: duckduckgo_comqloveatbv4731iaweb.html

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

- **Total chunks:** 56
- **Structural chunks:** 9
- **Text/Nav chunks:** 45
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `span.clamp.cm` (freq=2, pq_sig=`div(div(div(span(span,span(b)))))`)
  - Chunk 1: `span` (freq=3, pq_sig=`div(div(div(span(span(b,b)))))`)
  - Chunk 2: `div.ke.ogdw` (freq=3, pq_sig=`div(div(span(span(b,b)),p,a(div(p(span,span)))),sp`)
  - Chunk 3: `div.ke.ogdw` (freq=2, pq_sig=`div(div(span(span,span(b)),p,a(div(p(span,span))))`)
  - Chunk 4: `a.ah.atb` (freq=3, pq_sig=`a`)
  - Chunk 5: `div.axz.bn` (freq=20, pq_sig=`div(div(p,span(i)),img)`)
  - Chunk 6: `div.ad.cd` (freq=20, pq_sig=`div(h2(a(span)))`)
  - Chunk 7: `span.dkz.dp` (freq=10, pq_sig=`span(a(div(img)))`)
  - Chunk 8: `button.acqyoh.aur` (freq=18, pq_sig=`button(svg(path))`)

**Text/Nav chunks:**
  - Chunk 11: `[text_content:li×12]` (freq=12)
  - Chunk 12: `[text_content:li×3]` (freq=3)
  - Chunk 13: `[text_content:li×6]` (freq=6)
  - Chunk 14: `[text_content:li×3]` (freq=3)
  - Chunk 15: `[nav_content:li×5]` (freq=5)
  - Chunk 16: `[nav_content:li×6]` (freq=6)
  - Chunk 17: `[nav_content:li×4]` (freq=4)
  - Chunk 18: `[nav_content:li×7]` (freq=7)
  - Chunk 19: `[nav_content:a×31]` (freq=31)
  - Chunk 20: `[nav_content:li×4]` (freq=4)
  - Chunk 21: `[nav_content:li×10]` (freq=10)
  - Chunk 22: `[nav_content:li×20]` (freq=20)
  - Chunk 23: `[nav_content:a×10]` (freq=10)
  - Chunk 24: `[text_content:h3×1]` (freq=1)
  - Chunk 25: `[text_content:h3×1]` (freq=1)
  - Chunk 26: `[text_content:h3×1]` (freq=1)
  - Chunk 27: `[text_content:h2×1]` (freq=1)
  - Chunk 28: `[text_content:h3×1]` (freq=1)
  - Chunk 29: `[text_content:h3×1]` (freq=1)
  - Chunk 30: `[text_content:h3×1]` (freq=1)
  - Chunk 31: `[text_content:h3×1]` (freq=1)
  - Chunk 32: `[text_content:h3×1]` (freq=1)
  - Chunk 33: `[text_content:h3×1]` (freq=1)
  - Chunk 34: `[text_content:h3×1]` (freq=1)
  - Chunk 35: `[text_content:h3×1]` (freq=1)
  - Chunk 36: `[text_content:h3×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h3×1]` (freq=1)
  - Chunk 39: `[text_content:h3×1]` (freq=1)
  - Chunk 40: `[text_content:h3×1]` (freq=1)
  - Chunk 41: `[text_content:h3×1]` (freq=1)
  - Chunk 42: `[text_content:h3×1]` (freq=1)
  - Chunk 43: `[text_content:li×1]` (freq=1)
  - Chunk 44: `[text_content:li×1]` (freq=1)
  - Chunk 45: `[text_content:li×1]` (freq=1)
  - Chunk 46: `[text_content:li×1]` (freq=1)
  - Chunk 47: `[text_content:li×1]` (freq=1)
  - Chunk 48: `[text_content:li×1]` (freq=1)
  - Chunk 49: `[text_content:li×1]` (freq=1)
  - Chunk 50: `[text_content:li×1]` (freq=1)
  - Chunk 51: `[text_content:li×1]` (freq=1)
  - Chunk 52: `[text_content:li×1]` (freq=1)
  - Chunk 53: `[text_content:li×1]` (freq=1)
  - Chunk 54: `[text_content:li×1]` (freq=1)
  - Chunk 55: `[text_content:figcaption×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: duckduckgo_comqloveatbv4731iaweb.html ===
Chunks: 56 (structural=9, functional=11, text=36)
Categories: {'structural': 1, 'card': 7, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 36, 'menu_item': 9}
Content: 1718 tagged, 1004 preserved (58%)
Leaks: 714 total, 208 high-importance

--- Chunk 0: span.clamp.cm ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///span[contains(@class,'cm')][contains(@class,'erah')][contains(@class,'gjhar')][contains(@class,'igmn')][contains(@style,'clamp')]
  tree_sig: div(div(div(span(span,span(b)))))
  content: [TEXT=4]

--- Chunk 1: span ---
  type=card freq=3 excl=0.00
  pattern_xpath: ///span
  tree_sig: div(div(div(span(span(b,b)))))
  content: [TEXT=4]

--- Chunk 2: div.ke.ogdw ---
  type=card freq=3 excl=0.50
  pattern_xpath: ///div[contains(@class,'ke')][contains(@class,'ogdw')][contains(@class,'qthn')][contains(@class,'xqwfc')][contains(@class,'yg')]
  tree_sig: div(div(span(span(b,b)),p,a(div(p(span,span)))),span(a(div(img))))
  content: [ATTR=1 HREF=2 IMG=1 TEXT=7]

--- Chunk 3: div.ke.ogdw ---
  type=card freq=2 excl=0.50
  pattern_xpath: ///div[contains(@class,'ke')][contains(@class,'ogdw')][contains(@class,'qthn')][contains(@class,'xqwfc')][contains(@class,'yg')]
  tree_sig: div(div(span(span,span(b)),p,a(div(p(span,span)))),span(a(div(img))))
  content: [ATTR=1 HREF=2 IMG=1 TEXT=7]

--- Chunk 4: a.ah.atb ---
  type=card freq=3 excl=0.72
  pattern_xpath: ///a[contains(@class,'hb')][contains(@class,'opq')][contains(@class,'wu')][contains(@class,'ff')][contains(@class,'co')]
  tree_sig: a
  content: [HREF=1 TEXT=1]

--- Chunk 5: div.axz.bn ---
  type=card freq=20 excl=1.00
  pattern_xpath: ///div[contains(@class,'axz')][contains(@class,'bn')][contains(@class,'ky')][contains(@class,'sf')][contains(@class,'twl')]
  tree_sig: div(div(p,span(i)),img)
  content: [IMG=1 TEXT=1]

--- Chunk 6: div.ad.cd ---
  type=card freq=20 excl=0.90
  pattern_xpath: ///div[contains(@class,'ad')][contains(@class,'ikg')][contains(@class,'xi')][contains(@class,'zo')][contains(@class,'cd')]
  tree_sig: div(h2(a(span)))
  content: [HREF=1 TEXT=1]

--- Chunk 7: span.dkz.dp ---
  type=card freq=10 excl=1.00
  pattern_xpath: ///span[contains(@class,'dkz')][contains(@class,'dp')][contains(@class,'pk')][contains(@class,'vr')][contains(@class,'zae')]
  tree_sig: span(a(div(img)))
  content: [ATTR=1 HREF=1 IMG=1]

--- Chunk 8: button.acqyoh.aur ---
  type=button freq=18 excl=1.00
  pattern_xpath: ///button[contains(@class,'aur')][contains(@class,'byk')][contains(@class,'cy')][contains(@class,'esp')][contains(@class,'fidpg')]
  tree_sig: button(svg(path))
  content: [ATTR=1]

--- Chunk 9: [search_inputs] ---
  type=search_input freq=12 excl=0.00
  pattern_xpath: ///input
  content: [ATTR=2]

--- Chunk 10: [pagination_buttons] ---
  type=pagination freq=95 excl=0.00
  pattern_xpath: ///div
  content: [TEXT=1]

--- Chunk 11: [text_content:li×12] ---
  type=text_singleton freq=12 excl=1.00
  pattern_xpath: ///li[contains(@class,'ll')][contains(@class,'xnd')][contains(@class,'zpzpf')][contains(@data-layout,'organic')]
  content: [ATTR=3 HREF=1 TEXT=21]

--- Chunk 12: [text_content:li×3] ---
  type=text_singleton freq=3 excl=0.28
  pattern_xpath: ///li[contains(@class,'definition')][contains(@class,'definitions')][contains(@class,'module')]
  content: [TEXT=1]

--- Chunk 13: [text_content:li×6] ---
  type=text_singleton freq=6 excl=0.28
  pattern_xpath: ///li[contains(@class,'definition')][contains(@class,'definitions')][contains(@class,'module')]
  content: [TEXT=1]

--- Chunk 14: [text_content:li×3] ---
  type=text_singleton freq=3 excl=0.28
  pattern_xpath: ///div[contains(@class,'title')]//li[contains(@class,'definition')][contains(@class,'definitions')][contains(@class,'module')]
  content: [TEXT=1]

--- Chunk 15: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.20
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 16: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.20
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 17: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.20
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 18: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.20
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 19: [nav_content:a×31] ---
  type=menu_item freq=31 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 20: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 21: [nav_content:li×10] ---
  type=menu_item freq=10 excl=0.50
  pattern_xpath: ///li[contains(@class,'ar')][contains(@class,'be')][contains(@class,'bnt')][contains(@class,'gi')][contains(@class,'hrx')]
  content: [ATTR=2 HREF=1 IMG=2 TEXT=5]

--- Chunk 22: [nav_content:li×20] ---
  type=menu_item freq=20 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=2 HREF=1 IMG=2 TEXT=5]

--- Chunk 23: [nav_content:a×10] ---
  type=menu_item freq=10 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=6 HREF=1 IMG=2 TEXT=9]

--- Chunk 24: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h3[contains(@class,'co')][contains(@class,'geqs')][contains(@class,'ra')][contains(@class,'us')][contains(@class,'ah')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h3[contains(@class,'co')][contains(@class,'geqs')][contains(@class,'ra')][contains(@class,'us')][contains(@class,'ah')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.70
  pattern_xpath: ///h3[contains(@class,'of')][contains(@class,'part')][contains(@class,'speech')][contains(@class,'definitions')][contains(@class,'module')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'ee')][contains(@class,'ez')][contains(@class,'gdy')][contains(@class,'ws')][contains(@class,'xq')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'al')][contains(@class,'bnu')][contains(@class,'cl')][contains(@class,'de')][contains(@class,'ei')]
  content: [ATTR=1 TEXT=1]

--- Chunk 29: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'al')][contains(@class,'bnu')][contains(@class,'cl')][contains(@class,'de')][contains(@class,'ei')]
  content: [ATTR=1 TEXT=1]

--- Chunk 30: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'al')][contains(@class,'bnu')][contains(@class,'cl')][contains(@class,'de')][contains(@class,'ei')]
  content: [ATTR=1 TEXT=1]

--- Chunk 31: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'al')][contains(@class,'bnu')][contains(@class,'cl')][contains(@class,'de')][contains(@class,'ei')]
  content: [ATTR=1 TEXT=1]

--- Chunk 32: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'al')][contains(@class,'bnu')][contains(@class,'cl')][contains(@class,'de')][contains(@class,'ei')]
  content: [ATTR=1 TEXT=1]

--- Chunk 33: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 34: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 35: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 36: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 38: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 39: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 40: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 41: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 42: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'ac')][contains(@class,'dt')][contains(@class,'euosa')][contains(@class,'fro')][contains(@class,'ggh')]
  content: [ATTR=1 TEXT=1]

--- Chunk 43: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.40 LEAKS=9
  pattern_xpath: ///li[contains(@data-layout,'videos')][contains(@class,'ca')][contains(@class,'fj')][contains(@class,'jl')][contains(@class,'mf')]
  content: [ATTR=23 HREF=12 IMG=20 TEXT=55]
  LEAKS (high):
    [HREF] https://www.youtube.com/watch?v=9kaZ79MQWrM (href not in rendered output)
    [HREF] https://www.youtube.com/watch?v=THPU7RDt-rc (href not in rendered output)
    [HREF] https://www.youtube.com/watch?v=PU2HANE4iPE (href not in rendered output)
    [HREF] https://www.youtube.com/watch?v=eDMwpVUhxAo (href not in rendered output)
    [HREF] https://www.youtube.com/watch?v=wHlloPiWwHE (href not in rendered output)
  LEAKS (medium):
    [TEXT] What is Love? The Science Behind Lust, Attraction, and Attachment
    [TEXT] What Is Love? | The Science, Emotion, and Meaning Behind It All
    [TEXT] Céline Dion - The Power Of Love (Lyrics)

--- Chunk 44: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.40 LEAKS=13
  pattern_xpath: ///li[contains(@data-layout,'images')][contains(@class,'ca')][contains(@class,'fj')][contains(@class,'jl')][contains(@class,'mf')]
  content: [ATTR=33 HREF=13 IMG=10 TEXT=39]
  LEAKS (high):
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fstorage.googleapis.com%2Fmv-pro (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fpsychology.tips%2Fwp-content%2F (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fi.pinimg.com%2Foriginals%2Fe1%2 (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fi1.wp.com%2Filoverelationship.c (href not in rendered output)
    [HREF] http://parmaks.com/Resources/key-differences-signs-psychology-explained/ (href not in rendered output)
  LEAKS (medium):
    [TEXT] Key Differences, Signs & Psychology Explained - Self Help Resources
    [TEXT] Signs a Man Loves You but Is Afraid: Unraveling His Hidden Emotions | 
    [TEXT] Psychologists have identified ten factors that explain why and how we 

--- Chunk 45: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.55 LEAKS=140
  pattern_xpath: ///li[contains(@data-layout,'related')][contains(@data-layout,'searches')][contains(@class,'ca')][contains(@class,'fj')][contains(@class,'jl')]
  content: [ATTR=150 HREF=165 IMG=96 TEXT=539]
  LEAKS (high):
    [HREF] https://www.verywellmind.com/what-is-love-2795343 (href not in rendered output)
    [HREF] https://en.wikipedia.org/wiki/Love (href not in rendered output)
    [HREF] https://www.merriam-webster.com/dictionary/love (href not in rendered output)
    [HREF] https://www.britannica.com/topic/love-emotion (href not in rendered output)
    [HREF] https://psychcentral.com/relationships/the-psychology-of-love (href not in rendered output)
  LEAKS (medium):
    [TEXT] The American Heritage® Dictionary of the English Language, 5th Edition
    [TEXT] What Love Is and How to Cultivate It - Verywell Mind
    [TEXT] What Love Is and How to Cultivate It - Verywell Mind

--- Chunk 46: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.33 LEAKS=5
  pattern_xpath: ///li[contains(@class,'bu')][contains(@class,'bui')][contains(@class,'ju')][contains(@class,'mj')][contains(@class,'oz')]
  content: [ATTR=18 HREF=6 IMG=6 TEXT=18]
  LEAKS (high):
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fpsychology.tips%2Fwp-content%2F (href not in rendered output)
    [HREF] https://psychology.tips/signs-a-man-loves-you-but-is-afraid/ (href not in rendered output)
    [IMG] //external-content.duckduckgo.com/ip3/www.calmsage.com.ico (img URL not in rendered)
    [IMG] //external-content.duckduckgo.com/ip3/parmaks.com.ico (img URL not in rendered)
    [IMG] //external-content.duckduckgo.com/ip3/psychology.tips.ico (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Signs a Man Loves You but Is Afraid: Unraveling His Hidden Emotions | 
    [TEXT] Block this site from all results
    [TEXT] Block this site from all results

--- Chunk 47: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.33 LEAKS=2
  pattern_xpath: ///li[contains(@class,'bu')][contains(@class,'bui')][contains(@class,'ju')][contains(@class,'mj')][contains(@class,'oz')]
  content: [ATTR=12 HREF=4 IMG=4 TEXT=12]
  LEAKS (high):
    [IMG] //external-content.duckduckgo.com/ip3/www.pinterest.com.ico (img URL not in rendered)
    [IMG] //external-content.duckduckgo.com/ip3/iloverelationship.com.ico (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Block this site from all results
    [TEXT] Block this site from all results

--- Chunk 48: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.33 LEAKS=17
  pattern_xpath: ///li[contains(@class,'bu')][contains(@class,'bui')][contains(@class,'ju')][contains(@class,'mj')][contains(@class,'oz')]
  content: [ATTR=46 HREF=12 IMG=17 TEXT=51]
  LEAKS (high):
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fwww.calmsage.com%2Fwp-content%2 (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fstorage.googleapis.com%2Fmv-pro (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fpsychology.tips%2Fwp-content%2F (href not in rendered output)
    [HREF] https://www.calmsage.com/8-types-of-love-learn-their-impact-on-your-relationships/ (href not in rendered output)
    [HREF] http://parmaks.com/Resources/key-differences-signs-psychology-explained/ (href not in rendered output)
  LEAKS (medium):
    [TEXT] 8 Different Types of Love According to Greek | Perfect Combination for
    [TEXT] Key Differences, Signs & Psychology Explained - Self Help Resources
    [TEXT] Signs a Man Loves You but Is Afraid: Unraveling His Hidden Emotions | 

--- Chunk 49: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.16 LEAKS=1
  pattern_xpath: ///li[contains(@class,'jg')][contains(@class,'lxm')][contains(@class,'pg')][contains(@class,'pmq')][contains(@class,'ya')]
  content: [ATTR=6 HREF=2 IMG=2 TEXT=6]
  LEAKS (high):
    [IMG] //external-content.duckduckgo.com/ip3/www.calmsage.com.ico (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Block this site from all results

--- Chunk 50: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.16 LEAKS=1
  pattern_xpath: ///li[contains(@class,'jg')][contains(@class,'lxm')][contains(@class,'pg')][contains(@class,'pmq')][contains(@class,'ya')]
  content: [ATTR=6 HREF=2 IMG=2 TEXT=6]
  LEAKS (high):
    [IMG] //external-content.duckduckgo.com/ip3/parmaks.com.ico (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Block this site from all results

--- Chunk 51: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.16 LEAKS=1
  pattern_xpath: ///li[contains(@class,'jg')][contains(@class,'lxm')][contains(@class,'pg')][contains(@class,'pmq')][contains(@class,'ya')]
  content: [ATTR=6 HREF=2 IMG=2 TEXT=6]
  LEAKS (high):
    [IMG] //external-content.duckduckgo.com/ip3/psychology.tips.ico (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Block this site from all results

--- Chunk 52: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.16 LEAKS=1
  pattern_xpath: ///li[contains(@class,'jg')][contains(@class,'lxm')][contains(@class,'pg')][contains(@class,'pmq')][contains(@class,'ya')]
  content: [ATTR=6 HREF=2 IMG=2 TEXT=6]
  LEAKS (high):
    [IMG] //external-content.duckduckgo.com/ip3/www.pinterest.com.ico (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Block this site from all results

--- Chunk 53: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.16 LEAKS=1
  pattern_xpath: ///li[contains(@class,'jg')][contains(@class,'lxm')][contains(@class,'pg')][contains(@class,'pmq')][contains(@class,'ya')]
  content: [ATTR=6 HREF=2 IMG=2 TEXT=6]
  LEAKS (high):
    [IMG] //external-content.duckduckgo.com/ip3/iloverelationship.com.ico (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Block this site from all results

--- Chunk 54: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.16 LEAKS=17
  pattern_xpath: ///li[contains(@class,'jg')][contains(@class,'lxm')][contains(@class,'pg')][contains(@class,'pmq')][contains(@class,'ya')]
  content: [ATTR=40 HREF=10 IMG=15 TEXT=45]
  LEAKS (high):
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fwww.calmsage.com%2Fwp-content%2 (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fstorage.googleapis.com%2Fmv-pro (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fpsychology.tips%2Fwp-content%2F (href not in rendered output)
    [HREF] /?q=love&atb=v473-1&ia=images&iax=images&iai=https%3A%2F%2Fi.pinimg.com%2Foriginals%2Fe1%2 (href not in rendered output)
    [HREF] http://parmaks.com/Resources/key-differences-signs-psychology-explained/ (href not in rendered output)
  LEAKS (medium):
    [TEXT] Key Differences, Signs & Psychology Explained - Self Help Resources
    [TEXT] Signs a Man Loves You but Is Afraid: Unraveling His Hidden Emotions | 
    [TEXT] Psychologists have identified ten factors that explain why and how we 

--- Chunk 55: [text_content:figcaption×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///figcaption
  content: [ATTR=4 HREF=1 IMG=1 TEXT=6]
  LEAKS (medium):
    [TEXT] Block this site from all results

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
4. Use filename `duckduckgo_comqloveatbv4731iaweb.html` in all `_distill()` calls
5. Name the module `test_duckduckgo_comqloveatbv4731iaweb_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
