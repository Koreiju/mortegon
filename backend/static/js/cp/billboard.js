/**
 * cp/billboard.js — Floating info panels: primary billboard, pinned
 * draggable knowledge panels, and the SVG connector arrow.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global.
 */

export const BillboardMixin = {

    showBillboard(data, isLocked) {
        const billboard = document.getElementById('billboard');
        if (!billboard || !data) return;
        // Per Mortegon §4.1 the hover billboard ALSO works for doc-hubs
        // — the previous early-return meant doc-hubs had no hover
        // panel, which broke the "hover → click freezes panel in
        // place" contract for hub spheres. We synthesize a doc-hub
        // body (url, chunk count, detected search-field xpath) in
        // the same DOM elements the chunk path uses; html and
        // rendered_text sections are hidden because doc-hubs have
        // none of their own.

        const entry = this.nodeInstanceMap.get(data.id);
        let cssColor  = '#b8c0c8';
        let textColor = '#ffffff';
        if (entry) {
            const color = entry.originalColor;
            cssColor  = `#${color.getHexString()}`;
            textColor = this.getContrastYIQ(color);
            billboard.style.borderLeft = `4px solid ${cssColor}`;
        }

        const title = document.getElementById('billboard-title');
        if (title) { title.textContent = this.shortenUrl(data.url || ''); title.style.color = textColor; }

        const header = billboard.querySelector('.billboard-header');
        if (header) { header.style.backgroundColor = cssColor; header.style.color = textColor; }

        const closeBtn = document.getElementById('billboard-close');
        if (closeBtn) {
            closeBtn.style.color = textColor;
            closeBtn.onclick = () => {
                this.hideBillboard();
                this.selectedId = null;
                this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
            };
        }

        const pinBtn = document.getElementById('billboard-pin');
        if (pinBtn) {
            pinBtn.style.color = textColor;
            pinBtn.onclick = (ev) => { ev.stopPropagation(); this.pinBillboard(data, cssColor, textColor); };
        }

        const link = document.getElementById('billboard-link');
        if (link) { link.href = data.url || '#'; link.textContent = data.url || ''; }
        // §O — register the billboard's source URL so the workspace/url-set can
        // correlate the pinned panel to its origin (peer tabs + REPL viewer).
        if (data.url && typeof this._mirrorUi === 'function')
            this._mirrorUi('/api/ui/register_billboard_url', { billboard_id: String(data.id), url: data.url });

        this.renderBillboardMedia(data);

        const htmlPre  = document.getElementById('billboard-html');
        const textPre  = document.getElementById('billboard-rendered-text');
        const fieldsPre = document.getElementById('billboard-fields');
        const xpathEl  = document.getElementById('billboard-xpath');

        if (data.is_document) {
            // Doc-hub variant of the unified panel. Hide html /
            // rendered-text sections (no per-hub html), repurpose
            // the fields section as a {url, chunks, search_field}
            // summary block, set xpath to "URL root".
            const url        = data.url || (data.id || '').replace(/^doc_/, '');
            const chunkCount = this._chunksPerDoc
                ? (this._chunksPerDoc.get(data.id) || 0)
                : 0;
            const search     = (typeof this._findUrlSearchChunk === 'function')
                ? this._findUrlSearchChunk(data)
                : null;
            const lines = [
                `url: ${url}`,
                `chunks: ${chunkCount}`,
            ];
            if (search && search.absolute_xpath) {
                lines.push(`search_field_xpath: ${search.absolute_xpath}`);
            }
            if (htmlPre)  { htmlPre.textContent  = ''; htmlPre.style.display  = 'none'; }
            if (textPre)  { textPre.textContent  = ''; textPre.style.display  = 'none'; }
            // Also hide the labels above the html/text panels so the
            // hidden <pre> doesn't leave an orphan label visible.
            const hideLabelAdjacent = (preId) => {
                const pre = document.getElementById(preId);
                if (!pre) return;
                const lbl = pre.previousElementSibling;
                if (lbl && lbl.classList.contains('billboard-section-label')) {
                    lbl.dataset.docHidden = '1';
                    lbl.style.display = 'none';
                }
            };
            hideLabelAdjacent('billboard-html');
            hideLabelAdjacent('billboard-rendered-text');
            if (fieldsPre) { fieldsPre.textContent = lines.join('\n'); fieldsPre.style.display = ''; }
            if (xpathEl)  xpathEl.textContent = `URL root: ${url}`;
        } else {
            // Chunk variant — original behavior. Restore any sections
            // we may have hidden during a previous doc-hub hover.
            if (htmlPre) {
                htmlPre.style.display = '';
                if (data.html_raw !== undefined)
                    htmlPre.textContent = (data.html_raw || '').trim() || '(no HTML)';
                else
                    htmlPre.innerHTML = '<span style="color:#6b7280;font-style:italic;">Click node to load HTML...</span>';
            }
            if (textPre) {
                textPre.style.display = '';
                if (data.rendered_text !== undefined)
                    textPre.textContent = (data.rendered_text || '').trim() || '(no text)';
                else
                    textPre.innerHTML = '<span style="color:#6b7280;font-style:italic;">Click node to load text...</span>';
            }
            if (fieldsPre) {
                fieldsPre.style.display = '';
                if (data.fields === undefined) {
                    fieldsPre.innerHTML = '<span style="color:#6b7280;font-style:italic;">Click node to load summary...</span>';
                } else {
                    const fields = data.fields || {};
                    const keys   = Object.keys(fields);
                    fieldsPre.textContent = keys.length
                        ? keys.map(k => `${k}: ${JSON.stringify(fields[k])}`).join('\n')
                        : '(no summary)';
                }
            }
            if (xpathEl) xpathEl.textContent = data.absolute_xpath || 'Click node to load XPath...';
            // Un-hide section labels that the doc-hub branch may have
            // hidden previously.
            document.querySelectorAll('.billboard-section-label[data-doc-hidden="1"]').forEach(lbl => {
                lbl.removeAttribute('data-doc-hidden');
                lbl.style.display = '';
            });
        }

        const scoreEl = document.getElementById('billboard-score');
        if (scoreEl) {
            if (this.searchResults && this.searchResults.has(data.id)) {
                scoreEl.textContent = `${(this.searchResults.get(data.id) * 100).toFixed(1)}% match`;
                scoreEl.style.display = 'inline-block';
            } else {
                scoreEl.style.display = 'none';
            }
        }

        billboard.style.display = 'block';
        const pos = this._getNodePosition(data.id);
        if (pos) this.updateBillboardPosition({ position: pos });
    },

    hideBillboard() {
        const b = document.getElementById('billboard');
        if (b) b.style.display = 'none';
        this.hideBillboardArrow();
    },

    // ── Pinned knowledge panels ───────────────────────────────────────────────

    _escapeHtml(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },

    /**
     * Forward-truncate a long xpath to its last `keep` segments. The
     * user's reference output for the click-and-stick HTML summary
     * collapses long shadow-DOM paths like
     *
     *   /tile-dispatcher/#shadow-root/div/a/item-tile/#shadow-root/div/div/div/div/h3/text()
     *
     * down to the meaningful tail
     *
     *   .../h3/text()
     *
     * so the summary stays readable at a glance while preserving the
     * leaf attribute that identifies which field this value belongs
     * to. Mirrors backend/mapper/pattern_trie.forward_truncate (which
     * the scan.py interactive query loop uses for the same purpose).
     */
    _forwardTruncateXpath(xp, keep) {
        if (!xp) return '';
        if (typeof keep !== 'number' || keep < 1) keep = 3;
        const parts = String(xp).split('/').filter(p => p.length > 0);
        if (parts.length <= keep) return '/' + parts.join('/');
        return '…/' + parts.slice(-keep).join('/');
    },

    /**
     * Derive a short panel name from a chunk's absolute xpath: the
     * last two segments, joined by `/`. The user spec: knowledge
     * panel name == "last two steps of the absolute xpath of the
     * chunk root node". This is what gets shown as the title in
     * the concept card and also stamped as the slug for graph
     * references.
     */
    _chunkPanelName(xp) {
        if (!xp) return 'chunk';
        const parts = String(xp).split('/').filter(p => p.length > 0);
        if (parts.length === 0) return 'chunk';
        if (parts.length === 1) return parts[0];
        return parts.slice(-2).join('/');
    },

    /**
     * Build the string that becomes a click-and-stick concept card's
     * VALUE for a chunk. The output is JSON-shaped on purpose so the
     * card's Compile button can decompose it into sub-cards (one per
     * top-level key) and recompose back to the same JSON.
     *
     * Output schema, matching the user's HTML-summary contract:
     *
     *   {
     *     "url":           "<full URL of the source page>",
     *     "xpath":         "<absolute xpath of this chunk>",
     *     "html_raw":      "<full content-distilled HTML — NO truncation>",
     *     "rendered_text": "<full markdown-lite flatten — NO truncation>",
     *     "fields":        { "<forward-truncated xpath>": "<value or [values]>", ... }
     *   }
     *
     * Field-formatting requirements (per the user's example showing
     * an archive.org item-tile shadow-DOM card):
     *
     *   • **No truncation of html_raw or rendered_text** — the user
     *     explicitly asked that ALL content is shown. Long values
     *     are perfectly fine in the value textarea; the user can
     *     scroll.
     *   • **Group-dedup of fields by VALUE**: when many xpaths in
     *     the same chunk share a value (the title repeated as
     *     `@aria-label`, `@title`, and `h3/text()`, all "Nice Games
     *     Vol.7 (Game Magazine)(Scan)(JP)"), we collapse them to
     *     ONE entry whose key is an `[xp1, xp2, …]` array of all
     *     contributing xpaths. The grouping makes the visual scan
     *     dramatically cleaner while still preserving every xpath
     *     so the user / compile-decompose pipeline can drill into
     *     any specific structural path.
     *   • **Forward-truncated xpath keys**: every xpath in the
     *     `fields` map is replaced by its `.../<last 3 segments>`
     *     compression. Full xpaths are unwieldy on shadow-DOM
     *     hosts; the tail is the only structural part the user
     *     usually cares about for triage.
     *   • **Sorted output**: fields ordered by their canonical
     *     forward-truncated key so the JSON-decompose / Compile
     *     round-trip is deterministic.
     */
    _buildChunkSummaryString(data) {
        if (!data) return '';
        const rawFields = data.fields || data.content_fields_full || {};

        // ── Group entries by their value, then forward-truncate keys ──
        // valueGroup: `<typeTag>|<canonical_value>` → { xpaths: [...], value: any }
        const valueGroup = new Map();
        for (const k of Object.keys(rawFields)) {
            const v = rawFields[k];
            if (v === null || v === undefined) continue;
            let canonical;
            if (typeof v === 'string') {
                const t = v.trim();
                if (!t) continue;
                canonical = `s|${t}`;
            } else if (typeof v === 'number' || typeof v === 'boolean') {
                canonical = `${typeof v}|${v}`;
            } else {
                // arrays / objects — group by JSON shape so structurally
                // identical sub-objects collapse too.
                try { canonical = `j|${JSON.stringify(v)}`; }
                catch (_) { canonical = `o|${k}`; }  // fall back to per-key
            }
            const shortKey = this._forwardTruncateXpath(k, 3);
            let grp = valueGroup.get(canonical);
            if (!grp) {
                grp = { xpaths: [], value: typeof v === 'string' ? v.trim() : v };
                valueGroup.set(canonical, grp);
            }
            grp.xpaths.push(shortKey);
        }

        // Build cleanFields: each entry's key is the SHORTEST forward-
        // truncated xpath in the group; the value is either the bare
        // value (single contributor) or an object
        //   { value, xpaths: [<every short xpath that produced it>] }
        // when multiple xpaths share a value. JSON-decompose still
        // recurses into the `{value, xpaths}` shape correctly, and
        // the JSON itself reads naturally.
        const cleanFields = {};
        for (const grp of valueGroup.values()) {
            grp.xpaths.sort();  // shortest-first → use as canonical key
            const canonicalKey = grp.xpaths[0];
            if (grp.xpaths.length === 1) {
                cleanFields[canonicalKey] = grp.value;
            } else {
                cleanFields[canonicalKey] = {
                    value:  grp.value,
                    xpaths: grp.xpaths,
                };
            }
        }
        // Sort entries by canonical key for deterministic output.
        const sortedFields = {};
        Object.keys(cleanFields).sort().forEach(k => { sortedFields[k] = cleanFields[k]; });

        const obj = {
            url:           data.url || '',
            xpath:         data.absolute_xpath || '',
            // No truncation — user explicitly asked that ALL content
            // is shown (matches scan.py's interactive query loop).
            html_raw:      (data.html_raw      || '').trim(),
            rendered_text: (data.rendered_text || '').trim(),
            fields:        sortedFields,
        };

        // ── Pretty-print without JSON syntax ──
        // The user wants the data field to read like a tree, not like
        // JSON: key/value pairs indented with tabs/newlines, no
        // braces / brackets / quotes around plain string values. The
        // compile-decompose pipeline still works because it parses the
        // value as JSON ONLY if it starts with `{` or `[`; for the
        // tree format below, the compile button leaves the data
        // alone and the `rendering` shows the substituted output of
        // `{ref}` placeholders.
        try { return this._prettyTree(obj); }
        catch (_) {
            // Defensive fall-through to JSON if the tree printer
            // chokes on a circular ref or exotic type.
            try { return JSON.stringify(obj, null, 2); }
            catch (_e) { return String(obj.rendered_text || obj.html_raw || ''); }
        }
    },

    /**
     * Render a JS value as an indented tree string. Indentation uses
     * two spaces per level. The format mirrors the JSON structure but
     * elides every delimiter:
     *
     *     url
     *       https://archive.org/details/foo
     *     fields
     *       …/h3/text()
     *         value
     *           Nice Games Vol.7 (Game Magazine)(Scan)(JP)
     *         xpaths
     *           - …/h3/text()
     *           - …/@aria-label
     *
     * For very long string values (multi-line html_raw / rendered_text)
     * the value is emitted on the next line, each line of the value
     * indented one extra step so it reads as a sub-block.
     */
    _prettyTree(value, depth) {
        if (typeof depth !== 'number') depth = 0;
        const pad = '  '.repeat(depth);
        const lines = [];
        if (value === null || value === undefined) {
            lines.push(pad + '(none)');
            return lines.join('\n');
        }
        if (Array.isArray(value)) {
            if (value.length === 0) { lines.push(pad + '(empty)'); return lines.join('\n'); }
            value.forEach(item => {
                if (item !== null && typeof item === 'object') {
                    lines.push(pad + '-');
                    lines.push(this._prettyTree(item, depth + 1));
                } else {
                    lines.push(pad + '- ' + this._prettyScalar(item));
                }
            });
            return lines.join('\n');
        }
        if (typeof value === 'object') {
            const keys = Object.keys(value);
            if (keys.length === 0) { lines.push(pad + '(empty)'); return lines.join('\n'); }
            for (const k of keys) {
                const v = value[k];
                if (v !== null && typeof v === 'object') {
                    lines.push(pad + k);
                    lines.push(this._prettyTree(v, depth + 1));
                } else {
                    const scalar = this._prettyScalar(v);
                    if (scalar.indexOf('\n') >= 0 || scalar.length > 100) {
                        // Multi-line / long values get their own block
                        // so the key/value pair stays on a clean line.
                        lines.push(pad + k);
                        const inner = '  '.repeat(depth + 1);
                        scalar.split('\n').forEach(line => lines.push(inner + line));
                    } else {
                        lines.push(pad + k + ': ' + scalar);
                    }
                }
            }
            return lines.join('\n');
        }
        // Scalar root.
        lines.push(pad + this._prettyScalar(value));
        return lines.join('\n');
    },

    _prettyScalar(v) {
        if (v === null || v === undefined) return '';
        if (typeof v === 'string') return v;          // raw text, no quotes
        if (typeof v === 'number')  return String(v);
        if (typeof v === 'boolean') return v ? 'true' : 'false';
        try { return JSON.stringify(v); }
        catch (_) { return String(v); }
    },

    /**
     * §8B.5 — extract the static-data link chips from a chunk's
     * extracted fields. Returns ``{internal, external, media, json}``
     * arrays of ``{label, href, raw}`` records. Internal/external is
     * decided by URL hostname comparison against the chunk's own
     * source url; URLs that parse but lack a hostname (relative
     * paths) are bucketed as internal. Media uses both the chunk's
     * pre-extracted ``image_urls`` map and any ``@src``/``@srcset``/
     * ``@data-src`` fields that weren't already image-classified.
     * JSON chips fire only for ``@data-*`` attributes whose value
     * trims to ``{...}`` or ``[...]`` shape (string form, not parsed
     * yet — the click handler parses on demand).
     */
    _extractLinkChips(data) {
        const out = { internal: [], external: [], media: [], json: [] };
        if (!data || typeof data !== 'object') return out;
        // Source-url host for internal/external classification.
        let srcHost = '';
        try {
            srcHost = (new URL(data.url || '', 'http://_.local')).hostname;
        } catch (_) { srcHost = ''; }
        const sameHost = (u) => {
            if (!u) return true;  // relative paths
            try {
                const h = (new URL(u, 'http://_.local')).hostname;
                if (!h || h === '_.local') return true;
                return !srcHost || h === srcHost;
            } catch (_) { return true; }
        };
        const seenUrl = new Set();
        const seenMedia = new Set();
        const pushUrl = (u) => {
            if (!u) return;
            const t = String(u).trim();
            if (!t || seenUrl.has(t)) return;
            seenUrl.add(t);
            const bucket = sameHost(t) ? out.internal : out.external;
            bucket.push({ label: this.shortenUrl(t), href: t, raw: t });
        };
        const pushMedia = (u) => {
            if (!u) return;
            const t = String(u).trim();
            if (!t || seenMedia.has(t)) return;
            seenMedia.add(t);
            out.media.push({ label: this.shortenUrl(t), href: t, raw: t });
        };
        // Pre-extracted media URLs (chunk_builder filled these on the
        // backend; image_urls is keyed by member_xpath → url).
        const imageUrls = data.image_urls || {};
        if (imageUrls && typeof imageUrls === 'object') {
            for (const u of Object.values(imageUrls)) pushMedia(u);
        }
        // Walk the field dict for attribute leaves we care about.
        const fields = data.fields || data.content_fields_full || {};
        if (fields && typeof fields === 'object') {
            for (const [k, v] of Object.entries(fields)) {
                if (!k || v === undefined || v === null) continue;
                const key = String(k);
                // Field values are sometimes scalars, sometimes arrays
                // (chunk_query returns ``{path: [values]}``). Normalise.
                const vals = Array.isArray(v) ? v : [v];
                for (const raw of vals) {
                    if (raw === null || raw === undefined) continue;
                    if (/@href$/.test(key) ||
                        /@data-link$/.test(key) ||
                        /@data-url$/.test(key)) {
                        pushUrl(raw);
                    } else if (/@src$/.test(key) ||
                               /@srcset$/.test(key) ||
                               /@data-src$/.test(key)) {
                        // srcset may carry "url 1x, url2 2x" pairs; take
                        // first URL token from each comma-separated entry.
                        const tokens = String(raw).split(',').map(t => t.trim().split(/\s+/)[0]);
                        for (const tok of tokens) pushMedia(tok);
                    } else if (/@data-/.test(key) && typeof raw === 'string') {
                        const t = raw.trim();
                        if ((t.startsWith('{') && t.endsWith('}')) ||
                            (t.startsWith('[') && t.endsWith(']'))) {
                            // Use the attribute name as label; keep the
                            // raw JSON string in ``raw`` for on-click
                            // parse-and-expand.
                            const attr = key.replace(/^.*@/, '@');
                            out.json.push({
                                label: attr,
                                href: '',
                                raw: t,
                            });
                        }
                    }
                }
            }
        }
        return out;
    },

    /**
     * §8B.5 — render the chip strip. Returns the HTML fragment for a
     * ks-panel-section; caller decides where to inject it. Empty when
     * the chunk carries no extractable attributes (in which case we
     * skip the section entirely to avoid a "no chips" label cluttering
     * panels with pure text content).
     */
    _renderLinkChips(data) {
        const chips = this._extractLinkChips(data);
        const total =
            chips.internal.length + chips.external.length +
            chips.media.length    + chips.json.length;
        if (!total) return '';
        // Inline styles match the rest of the panel (which avoids a
        // separate stylesheet edit). Colour is per-type so the four
        // chip categories are scannable at a glance.
        const chipColors = {
            internal: { bg: '#1e3a8a', fg: '#bfdbfe', border: '#b8c0c8' },
            external: { bg: '#374151', fg: '#d1d5db', border: '#6b7280' },
            media:    { bg: '#3b0764', fg: '#e9d5ff', border: '#b8c0c8' },
            json:     { bg: '#064e3b', fg: '#a7f3d0', border: '#9aa3ab' },
        };
        const chipBtn = (cls, icon, tooltip, attrs, label) => {
            const col = chipColors[cls] || chipColors.internal;
            const style =
                'display:inline-flex;align-items:center;gap:4px;' +
                'padding:2px 6px;font-size:10px;font-family:inherit;' +
                'background:' + col.bg + ';color:' + col.fg + ';' +
                'border:1px solid ' + col.border + ';border-radius:10px;' +
                'cursor:pointer;max-width:180px;overflow:hidden;' +
                'text-overflow:ellipsis;white-space:nowrap;';
            return `<button class="ks-link-chip ks-chip-${cls}" ` +
                `style="${style}" title="${this._escapeHtml(tooltip)}" ${attrs}>` +
                `<i class="fas fa-${icon}"></i><span style="overflow:hidden;text-overflow:ellipsis;">` +
                `${this._escapeHtml(label)}</span></button>`;
        };
        const parts = [];
        for (const c of chips.internal) {
            parts.push(chipBtn(
                'internal', 'link',
                'Internal link — click opens in new tab; Ctrl+click creates an OntologyNode',
                `data-chip-type="internal" data-chip-href="${this._escapeHtml(c.href)}"`,
                c.label,
            ));
        }
        for (const c of chips.external) {
            parts.push(chipBtn(
                'external', 'external-link-alt',
                'External link — click opens in new tab; Ctrl+click scans target URL',
                `data-chip-type="external" data-chip-href="${this._escapeHtml(c.href)}"`,
                c.label,
            ));
        }
        for (const c of chips.media) {
            parts.push(chipBtn(
                'media', 'image',
                'Media — click opens in new tab; Ctrl+click pins as PinnedComponent',
                `data-chip-type="media" data-chip-href="${this._escapeHtml(c.href)}"`,
                c.label,
            ));
        }
        for (const c of chips.json) {
            parts.push(chipBtn(
                'json', 'code',
                'Embedded JSON — click toggles inline tree; Ctrl+click creates a UserNote',
                `data-chip-type="json" data-chip-payload="${this._escapeHtml(c.raw)}"`,
                c.label,
            ));
        }
        return `
            <div class="ks-panel-section" data-section="links">
                <div class="ks-section-label"><i class="fas fa-tags"></i> Static data links</div>
                <div class="ks-link-chip-row" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;">
                    ${parts.join('')}
                </div>
                <pre class="ks-pre ks-pre-json" style="display:none;margin-top:6px;"></pre>
            </div>`;
    },

    /**
     * §8B.5 — wire up chip click handlers on a freshly-rendered
     * pinned panel. Click opens the URL / toggles JSON preview;
     * Ctrl-click creates the appropriate concept node via the
     * existing POST /api/concepts endpoint (no special-case routes
     * needed — the type_hint differentiates ontology / pin / note).
     */
    _bindLinkChipHandlers(panel, data) {
        const chips = panel.querySelectorAll('.ks-link-chip');
        if (!chips || !chips.length) return;
        const jsonPre = panel.querySelector('.ks-pre-json');
        const focalId = data && data.id ? String(data.id) : '';
        const focalUrl = data && data.url ? String(data.url) : '';
        chips.forEach(btn => {
            btn.addEventListener('click', async (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                const type = btn.getAttribute('data-chip-type');
                const href = btn.getAttribute('data-chip-href') || '';
                const payload = btn.getAttribute('data-chip-payload') || '';
                // Ctrl/Cmd+click — create a concept node referencing
                // this chip. Same endpoint, different type_hint.
                if (ev.ctrlKey || ev.metaKey) {
                    const hint = ({
                        internal: 'ontology_node',
                        external: 'ontology_node',
                        media:    'pinned_component',
                        json:     'user_note',
                    })[type] || 'ontology_node';
                    const body = {
                        name: btn.querySelector('span')?.textContent || type,
                        description: `From chip on chunk ${focalId || '?'}`,
                        data: type === 'json' ? payload : JSON.stringify({
                            chip_type: type, href, source_id: focalId,
                            source_url: focalUrl,
                        }, null, 2),
                        type_hint: hint,
                        provenance: 'user-authored',
                        workspace_id: this._conceptWorkspaceId || '',
                    };
                    try {
                        await fetch('/api/concepts', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(body),
                        });
                    } catch (_) { /* silently swallow; user can retry */ }
                    return;
                }
                // Plain click — type-specific default action.
                if (type === 'json') {
                    if (!jsonPre) return;
                    if (jsonPre.style.display === 'none') {
                        let pretty = payload;
                        try { pretty = JSON.stringify(JSON.parse(payload), null, 2); }
                        catch (_) { /* keep raw */ }
                        jsonPre.textContent = pretty;
                        jsonPre.style.display = 'block';
                    } else {
                        jsonPre.style.display = 'none';
                    }
                } else if (href) {
                    window.open(href, '_blank', 'noopener');
                }
            });
        });
    },

    /**
     * Render the body of the click-and-stick knowledge panel —
     * exactly the same sectioned layout the OLD hover billboard
     * (#billboard in index.html) uses, so the click-and-stick
     * widget mirrors what the user sees on hover. Sections:
     *
     *   • xpath               — monospace, slate-grey
     *   • Content-distilled HTML   — preformatted, scrollable
     *   • Rendered text        — preformatted, scrollable
     *   • Content-structure summary (fields)
     *                           — key: value lines, deduped + forward-truncated
     *   • §8B.5 static-data link chips (if any)
     *   • Visit source link
     *
     * Each section's content goes through `_escapeHtml` so user
     * data can't inject HTML.  `{var}` placeholders inside the
     * editable fields are detected at compile time (see the panel's
     * Compile button wired in `pinBillboard` below).
     */
    _renderPanelBody(data, opts) {
        // §8D.1.2 — when ``opts.latched`` is true (the default at first
        // pin), the body renders name + description + rendering only;
        // the html / rendered_text / fields sections live in the
        // slide-out side panel produced by ``_renderPanelDataSlide`` and
        // are revealed by the latch button. ``latched=false`` renders
        // the whole anatomy inline (legacy behaviour).
        const latched = !!(opts && opts.latched);
        // Doc-hub variant (Mortegon §4.1): URL, chunk count, detected
        // search-field chunk if any. Doc-hubs don't have html_raw /
        // rendered_text / fields of their own — they're the spatial
        // root for their chunks. The synthesised body still uses the
        // unified ks-panel-section anatomy so the Compile button and
        // {var} reference parsing work the same way.
        if (data && data.is_document) {
            const url       = data.url || (data.id || '').replace(/^doc_/, '');
            const chunkCount = this._chunksPerDoc
                ? (this._chunksPerDoc.get(data.id) || 0)
                : 0;
            const search    = (typeof this._findUrlSearchChunk === 'function')
                ? this._findUrlSearchChunk(data)
                : null;
            const summaryLines = [
                `url: ${url}`,
                `chunks: ${chunkCount}`,
            ];
            if (search && search.absolute_xpath) {
                summaryLines.push(`search_field_xpath: ${search.absolute_xpath}`);
            }
            const summary = summaryLines.join('\n');
            const linkHref = url;
            return `
                <div class="ks-panel-section" data-section="xpath">
                    <div class="ks-section-label"><i class="fas fa-globe"></i> URL root</div>
                    <div class="ks-xpath">${this._escapeHtml(url || '(no url)')}</div>
                </div>
                <div class="ks-panel-section" data-section="fields">
                    <div class="ks-section-label"><i class="fas fa-list"></i> Page-level summary</div>
                    <pre class="ks-pre ks-pre-fields" contenteditable="true">${this._escapeHtml(summary)}</pre>
                </div>
                <div class="ks-panel-section" data-section="compiled" style="display:none;">
                    <div class="ks-section-label"><i class="fas fa-bolt"></i> Compiled rendering</div>
                    <pre class="ks-pre ks-pre-compiled"></pre>
                </div>
                <div class="ks-panel-actions">
                    <button class="ks-compile-btn" title="Resolve {var} references against the 2D concept graph">Compile</button>
                    <a href="${this._escapeHtml(linkHref)}" target="_blank" class="ks-source-link">Visit source ↗</a>
                </div>`;
        }
        const html    = (data.html_raw      || '').trim();
        const txt     = (data.rendered_text || '').trim();
        const xp      = data.absolute_xpath || '';
        const linkHref = data.url || '#';
        const rawFields = data.fields || data.content_fields_full || {};
        const fieldLines = this._renderFieldsLines(rawFields);
        // §8D.1.2 — latched body: xpath + rendered-text (the "rendering"
        // surface) only. The html block and the fields summary live in
        // the side-slide data panel because they ARE the data block.
        if (latched) {
            return `
            <div class="ks-panel-section" data-section="xpath">
                <div class="ks-section-label"><i class="fas fa-sitemap"></i> xpath</div>
                <div class="ks-xpath">${this._escapeHtml(xp || '(no xpath)')}</div>
            </div>
            <div class="ks-panel-section" data-section="text">
                <div class="ks-section-label"><i class="fas fa-align-left"></i> Rendered text</div>
                <pre class="ks-pre ks-pre-text" contenteditable="true">${this._escapeHtml(txt || '(no text)')}</pre>
            </div>
            ${this._renderLinkChips(data)}
            <div class="ks-panel-section" data-section="compiled" style="display:none;">
                <div class="ks-section-label"><i class="fas fa-bolt"></i> Compiled rendering</div>
                <pre class="ks-pre ks-pre-compiled"></pre>
            </div>`;
        }
        return `
            <div class="ks-panel-section" data-section="xpath">
                <div class="ks-section-label"><i class="fas fa-sitemap"></i> xpath</div>
                <div class="ks-xpath">${this._escapeHtml(xp || '(no xpath)')}</div>
            </div>
            <div class="ks-panel-section" data-section="html">
                <div class="ks-section-label"><i class="fas fa-code"></i> Content-distilled HTML</div>
                <pre class="ks-pre ks-pre-html" contenteditable="true">${this._escapeHtml(html || '(no HTML)')}</pre>
            </div>
            <div class="ks-panel-section" data-section="text">
                <div class="ks-section-label"><i class="fas fa-align-left"></i> Rendered text</div>
                <pre class="ks-pre ks-pre-text" contenteditable="true">${this._escapeHtml(txt || '(no text)')}</pre>
            </div>
            <div class="ks-panel-section" data-section="fields">
                <div class="ks-section-label"><i class="fas fa-list"></i> Content-structure summary</div>
                <pre class="ks-pre ks-pre-fields" contenteditable="true">${this._escapeHtml(fieldLines || '(no fields)')}</pre>
            </div>
            ${this._renderLinkChips(data)}
            <div class="ks-panel-section" data-section="compiled" style="display:none;">
                <div class="ks-section-label"><i class="fas fa-bolt"></i> Compiled rendering</div>
                <pre class="ks-pre ks-pre-compiled"></pre>
            </div>
            <div class="ks-panel-actions">
                <button class="ks-compile-btn" title="Resolve {var} references against the 2D concept graph">Compile</button>
                <a href="${this._escapeHtml(linkHref)}" target="_blank" class="ks-source-link">Visit source ↗</a>
            </div>`;
    },

    /**
     * Render a content_fields_full dict as deduplicated, forward-
     * truncated key:value lines. The key column is the user's
     * "forward-truncated xpath" — keep last 3 segments, prefix
     * `…/`. Values that repeat across multiple xpaths collapse to
     * one line whose tail lists all contributing xpaths.
     */
    _renderFieldsLines(rawFields) {
        if (!rawFields || typeof rawFields !== 'object') return '';
        const fwd = (xp) => {
            if (!xp) return '';
            const parts = String(xp).split('/').filter(p => p.length > 0);
            if (parts.length <= 3) return '/' + parts.join('/');
            return '…/' + parts.slice(-3).join('/');
        };
        const seen = new Map();  // value → [shortKey, ...]
        const keyOrder = Object.keys(rawFields).sort();
        for (const k of keyOrder) {
            const v = rawFields[k];
            if (v === null || v === undefined) continue;
            let canonical;
            if (typeof v === 'string') {
                const t = v.trim();
                if (!t) continue;
                canonical = 's|' + t;
            } else {
                try { canonical = 'j|' + JSON.stringify(v); }
                catch (_) { canonical = 'o|' + k; }
            }
            const short = fwd(k);
            const group = seen.get(canonical);
            if (group) group.keys.push(short);
            else seen.set(canonical, { keys: [short], value: v });
        }
        const lines = [];
        seen.forEach(({ keys, value }) => {
            const canonical = keys[0];
            const display = typeof value === 'string' ? value : JSON.stringify(value);
            lines.push(`${canonical}: ${display}`);
            // Append the rest of the xpaths that produced the same
            // value on subsequent indented lines so the user can see
            // every structural alias.
            for (let i = 1; i < keys.length; i++) {
                lines.push(`  ↳ ${keys[i]}`);
            }
        });
        return lines.join('\n');
    },

    _nextPanelZ() {
        let z = 10010;
        this._pinnedPanels.forEach(({ panel }) => {
            const cur = parseInt(panel.style.zIndex || '0', 10);
            if (cur > z) z = cur;
        });
        return z + 1;
    },

    pinBillboard(data, cssColor, textColor) {
        if (!data || !data.id) return;
        // ── Click-and-stick: spawn a clone of the OLD hover-billboard
        //     layout (xpath / html / rendered_text / fields sections),
        //     pinned, draggable, multi-pin. Per Mortegon Integration
        //     Scheme §1.2, the hover billboard and the click-pinned
        //     panel MUST look identical and appear at the SAME screen
        //     rect — hovering and clicking should feel like the same
        //     panel "sticking" in place. To achieve this we capture
        //     the hover billboard's current getBoundingClientRect()
        //     at click time and use it as the new pinned panel's
        //     (top, left, width); then we hide the hover billboard
        //     so it is free to preview a different node next time
        //     the user mouses over one.
        const existing = this._pinnedPanels.get(data.id);
        if (existing) {
            if (existing.minimized) this._togglePanelMinimize(data.id);
            existing.panel.style.zIndex = String(this._nextPanelZ());
            return;
        }
        const host  = document.getElementById('projector-panel') || document.body;
        const panel = document.createElement('div');
        panel.className      = 'pinned-panel';
        panel.dataset.panelId = data.id;
        // Stamp the 3D node id so the animate-loop arrow drawer
        // (concept_graph.js _drawConcept3DLinks, called every
        // frame from animation.js) can pull this panel's matching
        // sphere position and draw a solid line between them.
        panel.dataset['3dNodeId'] = data.id;
        panel.setAttribute('data-3d-node-id', data.id);
        // The 3D-link drawer scans `.concept-card[data-3d-node-id]`
        // by class — give the panel the same class so it gets picked
        // up alongside concept cards. (`.pinned-panel` keeps all its
        // existing styling.)
        panel.classList.add('concept-card');

        // ── Position freeze: capture the hover billboard's current
        //    on-screen rect (if visible) and reuse it for this new
        //    pinned panel. Falls back to a stagger offset for code
        //    paths that pin without a prior hover (search-row click,
        //    keyboard shortcuts).
        const n          = this._pinnedPanels.size;
        const hover      = document.getElementById('billboard');
        const hoverVis   = hover && hover.style.display !== 'none' &&
                           hover.offsetParent !== null;
        let pinTop  = 80 + n * 24;
        let pinLeft = 80 + n * 24;
        let pinWidth = 380;
        if (hoverVis) {
            const r = hover.getBoundingClientRect();
            // host (projector-panel) is the offsetParent of pinned
            // panels — translate the viewport rect into host-local
            // coordinates so absolute positioning lines up.
            const hostRect = host.getBoundingClientRect();
            pinTop  = r.top  - hostRect.top;
            pinLeft = r.left - hostRect.left;
            if (r.width  > 80) pinWidth = r.width;
        }
        // Note: we set an explicit `height` (instead of max-height) so
        // `resize:both` works in both directions. max-height would
        // silently cap the user's downward drag at 70vh, which feels
        // broken. min-width / min-height give a sensible floor.
        // §S.4 BLACK SLATE — thin silver border, completely black infill, serif
        // white text. No coloured header, no left stripe, no chrome buttons.
        panel.style.cssText =
            'position:absolute; z-index:' + this._nextPanelZ() + ';' +
            'top:' + pinTop + 'px; left:' + pinLeft + 'px;' +
            'width:' + pinWidth + 'px; height:70vh; overflow:hidden;' +
            'background:#000; color:#ffffff;' +
            "font-family:Georgia,'Times New Roman',serif;" +
            'border:1px solid var(--slate-border,#c0c0c0); border-radius:6px;' +
            'box-shadow:0 12px 32px rgba(0,0,0,0.55);' +
            'display:flex; flex-direction:column; resize:both;' +
            'min-width:280px; min-height:160px;';

        const title     = (data.url || data.absolute_xpath || 'Pinned chunk').toString();
        // §S.4 — no coloured header; the strip is transparent (still a drag
        // handle), glyphs are silver-on-black, serif white text.
        const headerBg  = 'transparent';
        const headerFg  = 'var(--slate-border,#c0c0c0)';
        // §8D.1.2 — latch + form-fit + slide-out data panel.
        // The panel opens *latched*: name + description + rendering only.
        // The "▶" latch button (right edge of the chrome) slides the data
        // block out into a side panel at equal height to the latched body.
        // Read-only panels (§8D.4.2 python-native) hide the latch button
        // entirely — there is no editable data block to slide out.
        const isReadOnly = this._isReadOnlyData(data);
        const latchBtn = isReadOnly ? '' : (
            `<button class="pinned-panel-latch" title="Slide data block out" ` +
            `style="background:none;border:none;color:${headerFg};cursor:pointer;font-size:12px;">` +
            `<i class="fas fa-angle-right"></i></button>`
        );
        const lockIndicator = isReadOnly
            ? `<span class="pinned-panel-lock" title="Read-only (Python-native)" ` +
              `style="margin-right:4px;font-size:11px;opacity:0.85;">🔒</span>`
            : '';
        panel.innerHTML = `
            <div class="pinned-panel-header" style="display:flex;align-items:center;justify-content:space-between;padding:4px 8px;background:${headerBg};color:${headerFg};cursor:move;user-select:none;">
                <span class="pinned-panel-title" style="font-family:Georgia,serif;font-size:11px;opacity:0.7;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:260px;">${lockIndicator}${this._escapeHtml(this.shortenUrl(title))}</span>
                <span style="display:flex;gap:6px;">
                    ${latchBtn}
                    <button class="pinned-panel-min" title="Minimize" style="display:none;background:none;border:none;color:${headerFg};cursor:pointer;font-size:12px;"><i class="fas fa-window-minimize"></i></button>
                    <button class="pinned-panel-close" title="Unpin" style="display:none;background:none;border:none;color:${headerFg};cursor:pointer;font-size:12px;"><i class="fas fa-times"></i></button>
                </span>
            </div>
            <div class="pinned-panel-content" style="display:flex;flex-direction:row;flex:1;overflow:hidden;">
                <div class="pinned-panel-body" style="padding:8px 10px;overflow:auto;flex:1;min-width:260px;max-width:600px;font-size:11px;">
                    ${this._renderPanelBody(data, { latched: true })}
                </div>
                <div class="pinned-panel-data-slide" style="display:none;padding:8px 10px;overflow:auto;border-left:1px solid rgba(0,0,0,0.18);min-width:280px;max-width:800px;font-size:11px;background:rgba(0,0,0,0.02);">
                    ${this._renderPanelDataSlide(data)}
                </div>
            </div>`;
        host.appendChild(panel);

        const entry = { panel, data, minimized: false, engaged: false, hovered: false };
        this._pinnedPanels.set(data.id, entry);

        // §8B.5 — wire chip click handlers (no-op when the chunk had
        // nothing extractable; _renderLinkChips returned '' in that
        // case so there are no buttons to bind).
        this._bindLinkChipHandlers(panel, data);

        // §8B halo wiring — the pinned billboard panel is the click-
        // and-stick representation of a 3D node, symmetric with a
        // concept card (§8D.1). On hover, fire the same §8D apparition
        // halo machinery that editor concept cards use; the halo
        // renders in 2D screen-space anchored to this panel's bounding
        // rect via ``_renderApparitionHalo``. This is the realization
        // of §8B's "halo arrows around the clicked node" — they're
        // not floating 3D billboards; they're 2D phantom cards
        // surrounding the billboarded knowledge panel. Debounced so
        // a quick mouse-over doesn't fire an unnecessary fetch.
        let _haloTimer = null;
        panel.addEventListener('mouseenter', () => {
            entry.hovered = true;
            if (!entry.engaged) this._panelHoverCount++;
            if (typeof this._fetchApparitionsForFocal !== 'function') return;
            if (typeof this._renderApparitionHalo !== 'function') return;
            if (_haloTimer) clearTimeout(_haloTimer);
            _haloTimer = setTimeout(async () => {
                try {
                    const cands = await this._fetchApparitionsForFocal(data.id, 6);
                    if (cands && cands.length) {
                        this._renderApparitionHalo(panel, cands);
                    }
                } catch (_) { /* halo is best-effort */ }
            }, 250);
        });
        panel.addEventListener('mouseleave', (ev) => {
            entry.hovered = false;
            if (!entry.engaged) this._panelHoverCount = Math.max(0, this._panelHoverCount - 1);
            if (_haloTimer) { clearTimeout(_haloTimer); _haloTimer = null; }
            // Mirror the editor concept-card behaviour: only clear the
            // halo if the user isn't drifting onto a phantom candidate
            // (phantoms are pointer-events:auto and clickable).
            const next = ev && ev.relatedTarget;
            // Phantom cards rendered by ``_renderApparitionHalo`` use
            // the ``concept-apparition-phantom`` class — keep the halo
            // alive while the user drifts onto one to click it.
            const onPhantom = next && next.closest && next.closest('.concept-apparition-phantom');
            if (!onPhantom && typeof this._clearApparitionHalo === 'function') {
                this._clearApparitionHalo();
            }
        });
        panel.addEventListener('click',     (ev) => ev.stopPropagation());
        panel.addEventListener('mousedown', (ev) => ev.stopPropagation());

        const bodyEl = panel.querySelector('.pinned-panel-body');
        if (bodyEl) {
            bodyEl.addEventListener('click', () => {
                if (!entry.engaged) {
                    entry.engaged = true;
                    if (entry.hovered) this._panelHoverCount = Math.max(0, this._panelHoverCount - 1);
                    panel.style.boxShadow = '0 12px 32px rgba(184,192,200,0.55)';
                }
            });
        }

        panel.querySelector('.pinned-panel-close').addEventListener('click', (ev) => {
            ev.stopPropagation(); this.unpinPanel(data.id);
        });
        panel.querySelector('.pinned-panel-min').addEventListener('click', (ev) => {
            ev.stopPropagation(); this._togglePanelMinimize(data.id);
        });
        // §8D.1.2 — latch toggle: slide the data block out as a side
        // panel at equal height to the latched body. Hidden entirely
        // for read-only python-native panels (latchBtn was '').
        const latchEl = panel.querySelector('.pinned-panel-latch');
        if (latchEl) {
            latchEl.addEventListener('click', (ev) => {
                ev.stopPropagation();
                this._togglePanelLatch(data.id);
            });
        }
        // §8D.2.2 — right-click central panel body toggles the
        // compile expansion. First right-click expands the panel
        // into a simplified subgraph on the editor canvas; second
        // right-click (on the same central or on its children)
        // collapses back. The UI state mirror at /api/ui/compile_*
        // records the toggle so peer tabs + REPL viewers see it.
        panel.addEventListener('contextmenu', (ev) => {
            // Browser-native menu on textareas (so copy/paste still works).
            const t = ev.target;
            if (t && (t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
            ev.preventDefault();
            ev.stopPropagation();
            this._togglePanelCompileExpand(data.id, data);
        });
        // §7.3.4 — DOUBLE-LEFT-CLICK is the symmetric panel↔graph toggle
        // (the new-design gesture). Right-click above stays as an additive
        // alias (§8D.2.2). Ignore dbl-clicks on editable fields / controls so
        // text selection and buttons keep working.
        panel.addEventListener('dblclick', (ev) => {
            const t = ev.target;
            if (t && (t.tagName === 'TEXTAREA' || t.tagName === 'INPUT' || t.tagName === 'BUTTON'
                      || t.isContentEditable
                      || (t.closest && t.closest('button, .ks-compile-btn, .pinned-panel-close, .pinned-panel-min, .rs-latch, .ft-latch, a')))) return;
            ev.preventDefault();
            ev.stopPropagation();
            this._togglePanelCompileExpand(data.id, data);
        });
        // ── Compile button ──
        // Resolves `{some_concept}` references inside any of the
        // editable sections (html / rendered_text / fields) against
        // the live concept graph. Substitutes each placeholder with
        // the referenced node's value (recursive — the concept
        // graph's _compileConceptNode handles cycle detection). The
        // result is dumped into the panel's "Compiled rendering"
        // section, which is hidden until the first compile press.
        const compileBtn = panel.querySelector('.ks-compile-btn');
        if (compileBtn) {
            compileBtn.addEventListener('click', (ev) => {
                ev.stopPropagation();
                this._compilePanelReferences(panel);
            });
        }
        this._makePanelDraggable(panel);

        // Hand off the hover-billboard's role to the new pinned panel.
        // We just spawned a draggable clone at the hover billboard's
        // exact screen rect, so the hover billboard's job is done for
        // this node — hide it so the next mouse-over can show a fresh
        // preview for a different chunk.
        if (hoverVis) this.hideBillboard();
    },

    /**
     * Per Mortegon §7, Compile does a single recursive descent:
     *   1. Substitute every `{slug-shaped-ref}` with the referenced
     *      concept node's compiled value (cycle-safe).
     *   2. After substitution, attempt to parse each section's text
     *      as a structured payload (JSON, bracketed list, indented
     *      tree). If structured, decompose the top level into child
     *      concept cards keyed `<panel_id>__<key>` and rewrite the
     *      section as `{child_key}` placeholders — so the next
     *      Compile press substitutes through the children.
     *   3. Print the final substituted+decomposed text into the
     *      panel's "Compiled rendering" section.
     */
    _compilePanelReferences(panel) {
        if (!panel) return;
        const panelId = panel.dataset.panelId || 'pp';
        const sections = ['html', 'text', 'fields'];

        const parts = [];
        for (const tag of sections) {
            const sec = panel.querySelector(`.ks-panel-section[data-section="${tag}"] .ks-pre`);
            if (!sec) continue;
            const raw = sec.innerText || sec.textContent || '';
            // (1) {ref} expansion against the live concept graph.
            let text = this._compileExpandRefs(raw);
            // (2) Structural decomposition. _tryParseStructure returns
            //     a normalised tree {kind, children:[{key,value}|leaf]}
            //     or null when the section is plain text.
            const struct = this._tryParseStructure(text);
            if (struct) {
                // Spawn / refresh child concept cards keyed
                // `<panel_id>__<sec>__<safekey>` so the next Compile
                // press hits them through {ref} expansion.
                const rewritten = this._decomposeIntoChildren(panelId, tag, struct);
                parts.push(`# ${tag}\n${rewritten}`);
            } else {
                parts.push(`# ${tag}\n${text}`);
            }
        }

        const outSection = panel.querySelector('.ks-panel-section[data-section="compiled"]');
        const outPre     = panel.querySelector('.ks-pre-compiled');
        if (outSection && outPre) {
            outSection.style.display = parts.length ? '' : 'none';
            outPre.textContent = parts.length
                ? parts.join('\n\n')
                : '(no content to compile)';
        }
    },

    /** Slugify per the concept-graph rules — same as _conceptSlugify. */
    _compileSlugify(s) {
        return String(s || '')
            .trim().toLowerCase()
            .replace(/[^a-z0-9_]+/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
    },

    /**
     * Substitute `{slug-shaped-ref}` against the concept graph.
     * Unresolved refs are left as the literal `{ref}`.
     */
    _compileExpandRefs(text) {
        const REF_RE = /\{([\w][\w \-]*)\}/g;
        return String(text || '').replace(REF_RE, (_m, ref) => {
            const slug = this._compileSlugify(ref);
            if (!this._conceptNodes || !this._conceptNodes.has(slug)) return `{${ref}}`;
            if (typeof this._compileConceptNode === 'function') {
                const v = this._compileConceptNode(slug);
                return v !== null && v !== undefined ? v : `{${ref}}`;
            }
            return this._conceptNodes.get(slug).value || `{${ref}}`;
        });
    },

    /**
     * Try to interpret `text` as a structured payload. Returns
     *   { kind: 'json' | 'list' | 'tree' | 'html', children: [...] }
     * or null when the text doesn't parse as any known structure.
     *
     * The decomposer is syntax-agnostic per Mortegon §7.2 — the
     * same compile button handles JSON, bracketed lists, indented
     * key-value trees, and HTML element trees. Recognition order
     * is "most specific first": JSON parses cleanly with delimiters,
     * HTML has angle brackets, trees fall out from indentation.
     */
    _tryParseStructure(text) {
        const t = String(text || '').trim();
        if (!t) return null;
        // (1) JSON object / array — strict parse on balanced delimiters.
        if ((t.startsWith('{') && t.endsWith('}')) ||
            (t.startsWith('[') && t.endsWith(']'))) {
            try {
                const v = JSON.parse(t);
                if (v !== null && typeof v === 'object') {
                    if (Array.isArray(v)) {
                        return {
                            kind: 'list',
                            children: v.map((item, i) => ({ key: String(i), value: item })),
                        };
                    }
                    return {
                        kind: 'json',
                        children: Object.keys(v).map((k) => ({ key: k, value: v[k] })),
                    };
                }
            } catch (_) { /* fall through */ }
        }
        // (2) HTML element tree — sniff a top-level tag and a closing tag.
        if (/^<\s*[a-zA-Z][\w-]*[\s>]/.test(t) && /<\/\s*[a-zA-Z][\w-]*\s*>\s*$/.test(t)) {
            try {
                const tpl = document.createElement('template');
                tpl.innerHTML = t;
                const root = tpl.content.firstElementChild;
                if (root) {
                    const kids = [];
                    // Attributes fold in as `@attr` children — matches
                    // Mortegon §7.2: "attributes folded as `@attr` children."
                    for (const attr of Array.from(root.attributes)) {
                        kids.push({ key: '@' + attr.name, value: attr.value });
                    }
                    // Element children: one per child element. Text
                    // siblings get a synthetic `#text-<i>` key.
                    let textIdx = 0, elIdx = 0;
                    for (const node of Array.from(root.childNodes)) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            kids.push({ key: `${node.tagName.toLowerCase()}_${elIdx++}`, value: node.outerHTML });
                        } else if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                            kids.push({ key: `#text_${textIdx++}`, value: node.textContent.trim() });
                        }
                    }
                    if (kids.length >= 1) return { kind: 'html', children: kids, _root: root.tagName.toLowerCase() };
                }
            } catch (_) { /* fall through */ }
        }
        // (3) Indented tree — at least one indented line plus one flat.
        const lines = t.split(/\r?\n/);
        const hasIndent = lines.some(L => /^\s+\S/.test(L));
        const hasFlat   = lines.some(L => /^\S/.test(L));
        if (hasIndent && hasFlat && lines.length >= 2) {
            // Group by top-level (flat) keys; descendants (indented
            // lines that follow) become the value text.
            const children = [];
            let cur = null;
            for (const line of lines) {
                if (!line.trim()) {
                    if (cur) cur.value += '\n';
                    continue;
                }
                if (/^\s+/.test(line)) {
                    // Continuation under the previous flat key.
                    if (cur) cur.value += (cur.value ? '\n' : '') + line;
                    continue;
                }
                // Flat line: start a new top-level child.
                const m = line.match(/^([^:]+):\s*(.*)$/);
                if (m) cur = { key: m[1].trim(), value: m[2] };
                else   cur = { key: line.trim(),  value: '' };
                children.push(cur);
            }
            if (children.length >= 1) return { kind: 'tree', children };
        }
        // (4) Lines of "key: value" with no indentation — still
        //     useful for the chunk fields summary. ≥ 2 lines AND
        //     ≥ 2 distinct keys.
        if (lines.length >= 2) {
            const flatKVs = [];
            for (const line of lines) {
                if (!line.trim()) continue;
                const m = line.match(/^([^:]+):\s*(.*)$/);
                if (m) flatKVs.push({ key: m[1].trim(), value: m[2] });
            }
            if (flatKVs.length >= 2) return { kind: 'tree', children: flatKVs };
        }
        return null;
    },

    /**
     * For each child of a parsed structure, create / refresh a
     * concept-graph card keyed `<panelId>__<section>__<safeKey>`
     * (deterministic — re-pressing Compile is idempotent; the
     * `_upsertConceptCard` helper handles "already exists" by
     * refreshing the value rather than spawning a duplicate).
     * Returns the rewritten section text as `{child_key}`
     * placeholders that the NEXT Compile press will resolve.
     */
    _decomposeIntoChildren(panelId, sectionTag, struct) {
        if (!struct || !struct.children || !struct.children.length) return '';
        const cKey = `${panelId}__${sectionTag}`;
        const refs = [];
        const slugSeen = new Map();
        for (const child of struct.children) {
            // Disambiguate duplicate keys within ONE Compile press
            // (e.g. two children named `@class` or `child_0`) with a
            // suffix on subsequent occurrences. Across presses the
            // mapping is deterministic because we walk children in
            // the same order.
            let baseSlug = this._compileSlugify(`${cKey}__${child.key}`);
            const count = (slugSeen.get(baseSlug) || 0) + 1;
            slugSeen.set(baseSlug, count);
            const slug = count === 1 ? baseSlug : `${baseSlug}_${count}`;
            const valueStr = (typeof child.value === 'object' && child.value !== null)
                ? JSON.stringify(child.value, null, 2)
                : String(child.value);
            if (typeof this._upsertConceptCard === 'function') {
                this._upsertConceptCard(slug, child.key, valueStr);
            }
            refs.push({ key: child.key, slug });
        }
        // Re-emit in the same flavour we parsed, so the next Compile
        // press sees the same structure shape and decomposes the
        // children's values in turn.
        switch (struct.kind) {
            case 'list':
                return '[\n' + refs.map(r => `  {${r.slug}}`).join(',\n') + '\n]';
            case 'json':
                return '{\n' + refs.map(r => `  "${r.key}": {${r.slug}}`).join(',\n') + '\n}';
            case 'html': {
                const tag = struct._root || 'div';
                const attrs = refs.filter(r => r.key.startsWith('@'))
                                   .map(r => `${r.key.slice(1)}="{${r.slug}}"`).join(' ');
                const inner = refs.filter(r => !r.key.startsWith('@'))
                                   .map(r => `{${r.slug}}`).join('');
                return `<${tag}${attrs ? ' ' + attrs : ''}>${inner}</${tag}>`;
            }
            case 'tree':
            default:
                return refs.map(r => `${r.key}: {${r.slug}}`).join('\n');
        }
    },

    /**
     * Upsert a concept-graph node by slug. Idempotent — if a node
     * with this slug already exists, only the `value` is refreshed
     * (so re-compile doesn't proliferate duplicates). Wraps the
     * concept-graph mixin's primitives so the compile path doesn't
     * have to know about Map internals.
     */
    _upsertConceptCard(slug, name, value) {
        if (!this._conceptNodes) return;
        if (this._conceptNodes.has(slug)) {
            // Refresh value on an existing card; re-paint the
            // <textarea>/<pre> so the user sees the update.
            const node = this._conceptNodes.get(slug);
            node.value = value;
            const card = document.querySelector(`.concept-card[data-id="${slug}"]`);
            if (card) {
                const ta = card.querySelector('.concept-value, textarea[data-field="value"]');
                if (ta) ta.value = value;
            }
            return;
        }
        // Lay out new children offset from the parent panel so they
        // don't pile up at (0,0). A simple grid keeps them legible
        // even on N>10 child cards.
        const n  = this._conceptNodes.size;
        const x  = 360 + (n % 4) * 280;
        const y  = 200 + Math.floor(n / 4) * 220;
        // addConceptNode takes (name, x, y) only — we patch the value
        // on the resulting node so the value flows through {ref}
        // resolution on the next Compile press.
        if (typeof this.addConceptNode === 'function') {
            const created = this.addConceptNode(name || slug, x, y);
            // addConceptNode may slugify `name` to a different id;
            // align the stored slug with what we asked for so the
            // refs we just emitted resolve.
            if (created) {
                const oldId = created.id;
                if (oldId !== slug) {
                    // Re-key the DOM first (before mutating created.id)
                    // so the selector still matches the old data-id.
                    const oldCard = document.querySelector(`.concept-card[data-id="${oldId}"]`);
                    if (oldCard) oldCard.setAttribute('data-id', slug);
                    this._conceptNodes.delete(oldId);
                    created.id = slug;
                    this._conceptNodes.set(slug, created);
                }
                created.value = value;
                const card = document.querySelector(`.concept-card[data-id="${slug}"]`);
                if (card) {
                    const ta = card.querySelector('.concept-value, textarea[data-field="value"]');
                    if (ta) ta.value = value;
                }
            }
        }
    },

    unpinPanel(id) {
        const entry = this._pinnedPanels.get(id);
        if (!entry) return;
        if (entry.hovered && !entry.engaged)
            this._panelHoverCount = Math.max(0, this._panelHoverCount - 1);
        if (entry.panel && entry.panel.parentNode) entry.panel.parentNode.removeChild(entry.panel);
        this._pinnedPanels.delete(id);
        // billboard.md §6 — mirror the unpin so pinned_billboards stays in sync
        // across the REPL viewer, peer tabs, and agent perception.
        if (typeof this._mirrorUi === 'function') this._mirrorUi('/api/ui/unpin', { node_id: id });
    },

    _togglePanelMinimize(id) {
        const entry = this._pinnedPanels.get(id);
        if (!entry) return;
        const body = entry.panel.querySelector('.pinned-panel-body');
        if (!body) return;
        entry.minimized = !entry.minimized;
        body.style.display      = entry.minimized ? 'none' : '';
        entry.panel.style.resize = entry.minimized ? 'none' : 'both';
        entry.panel.style.height = entry.minimized ? 'auto' : '';
        // Also hide the slide-out data panel when minimised.
        const slide = entry.panel.querySelector('.pinned-panel-data-slide');
        if (slide && entry.minimized) slide.style.display = 'none';
        // §17.12 — mirror pin chrome (minimised state) so peer tabs + REPL see it.
        if (typeof this._mirrorUi === 'function')
            this._mirrorUi('/api/ui/pin_chrome', { panel_id: id, minimised: entry.minimized });
    },

    // §8D.1.2 — latch toggle: slide-out side panel for the data block.
    _togglePanelLatch(id) {
        const entry = this._pinnedPanels.get(id);
        if (!entry) return;
        const slide = entry.panel.querySelector('.pinned-panel-data-slide');
        const latch = entry.panel.querySelector('.pinned-panel-latch i');
        if (!slide) return;
        const isOpen = slide.style.display !== 'none';
        slide.style.display = isOpen ? 'none' : 'block';
        if (latch) {
            latch.className = isOpen
                ? 'fas fa-angle-right'    // collapsed (latched) — slide closed
                : 'fas fa-angle-left';    // expanded — slide open
        }
        // §8D.1.2 — mirror the latch (data-slide) state so peer tabs + REPL see
        // whether the side data panel is revealed (latched = slide closed).
        if (typeof this._mirrorUi === 'function')
            this._mirrorUi('/api/ui/latch', { card_id: id, latched: (slide.style.display === 'none') });
    },

    // §8D.4.2 — heuristic for "this is a read-only python-native node".
    // Looks at the data block for the no_datablock sentinel; falls back
    // to type_hint if present in the data envelope.
    _isReadOnlyData(data) {
        if (!data) return false;
        if (data.type_hint && /^python_/.test(String(data.type_hint))) return true;
        const raw = data.data || data.data_block;
        if (typeof raw === 'string' && raw) {
            try {
                const j = JSON.parse(raw);
                if (j && (j.read_only === true || j.no_datablock === true)) return true;
            } catch (_) { /* not JSON — not read-only by this heuristic */ }
        }
        return false;
    },

    // §8D.1.2 — slide-out side panel renders just the data block.
    _renderPanelDataSlide(data) {
        const raw = data?.data || data?.data_block || '';
        const safe = this._escapeHtml(typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2));
        return `<pre class="pinned-panel-data-block" style="margin:0;font-family:monospace;font-size:11px;white-space:pre-wrap;word-break:break-word;">${safe}</pre>`;
    },

    // §8D.2.2 — right-click toggles a panel between collapsed (panel)
    // and expanded (simplified subgraph centred on its concept). We
    // mirror the toggle through /api/ui/compile_* so peer surfaces
    // (REPL watch-activity, peer tabs, agent perception) see it.
    _togglePanelCompileExpand(id, data) {
        const entry = this._pinnedPanels.get(id);
        if (!entry) return;
        const expanded = !!entry.compileExpanded;
        entry.compileExpanded = !expanded;
        const url = expanded ? '/api/ui/compile_collapse' : '/api/ui/compile_expand';
        const body = {
            workspace_id: (typeof window !== 'undefined' && window._activeWorkspaceId) || '',
            central_id:   id,
        };
        const _post = () => {
            try {
                fetch(url, {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify(body),
                }).catch(() => { /* best-effort mirror; UI still toggles locally */ });
            } catch (_) { /* fetch may not be available in test envs */ }
        };
        if (!expanded) {
            // §R.1/§R.5 — derive children from the backend's CANONICAL
            // syntax-agnostic decomposition (`decompose_top_level`: JSON,
            // markdown-gesture outline, indent tree) so the mirror carries
            // the same children every surface derives — one decomposition,
            // never a JSON-only fork (§18.11). Local JSON parse remains the
            // offline fallback.
            const raw = data?.data || data?.data_block || '';
            const _fallbackChildren = () => {
                let kids = [];
                if (typeof raw === 'string' && raw) {
                    try {
                        const j = JSON.parse(raw);
                        if (j && typeof j === 'object' && !Array.isArray(j)) {
                            kids = Object.keys(j).map(k => `${id}__${k}`);
                        }
                    } catch (_) { /* not JSON; leave children empty */ }
                }
                return kids;
            };
            if (typeof raw === 'string' && raw && typeof fetch === 'function') {
                fetch('/api/compile_pipeline', {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify({ text: raw, workspace_id: body.workspace_id }),
                }).then(r => r.json()).then(out => {
                    const entries = (out && out.entries) || [];
                    body.children = entries.length
                        ? entries.map(e => `${id}__${e.key}`)
                        : _fallbackChildren();
                    _post();
                }).catch(() => {
                    body.children = _fallbackChildren();
                    _post();
                });
            } else {
                body.children = _fallbackChildren();
                _post();
            }
        } else {
            _post();
        }
        // Visual cue on the panel itself so the user sees the toggle.
        entry.panel.style.outline = expanded
            ? ''
            : '2px solid #eef0f2';  /* specular silver = expanded-to-graph state (§4 active outline) */
    },

    _makePanelDraggable(panel) {
        const header = panel.querySelector('.pinned-panel-header');
        if (!header) return;
        let startX = 0, startY = 0, origLeft = 0, origTop = 0, dragging = false;
        const onMove = (ev) => {
            if (!dragging) return;
            panel.style.left = (origLeft + ev.clientX - startX) + 'px';
            panel.style.top  = (origTop  + ev.clientY - startY) + 'px';
        };
        const onUp = () => {
            dragging = false;
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup',   onUp);
            // §17.12 — mirror pin chrome (drag-end position) so a moved panel's
            // rect persists across peer tabs + REPL. Reverse-look-up the id.
            if (typeof this._mirrorUi === 'function') {
                let pid = null;
                this._pinnedPanels.forEach((e, k) => { if (e.panel === panel) pid = k; });
                if (pid) {
                    const r = panel.getBoundingClientRect();
                    this._mirrorUi('/api/ui/pin_chrome', { panel_id: pid, top: r.top, left: r.left, width: r.width, height: r.height });
                }
            }
        };
        header.addEventListener('mousedown', (ev) => {
            if (ev.target.closest('button')) return;
            dragging = true;
            startX = ev.clientX; startY = ev.clientY;
            const rect     = panel.getBoundingClientRect();
            const hostRect = (panel.parentNode || document.body).getBoundingClientRect();
            origLeft = rect.left - hostRect.left;
            origTop  = rect.top  - hostRect.top;
            panel.style.zIndex = String(this._nextPanelZ());
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup',   onUp);
            ev.preventDefault();
        });
    },

    updateBillboardPosition(meshOrObj) {
        const billboard = document.getElementById('billboard');
        const pos = meshOrObj?.position;
        if (!pos || !billboard) return;

        const panel     = document.getElementById('projector-panel');
        const panelRect = panel
            ? panel.getBoundingClientRect()
            : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };

        const vector = pos.clone();
        vector.project(this.camera);
        const x = (vector.x * 0.5 + 0.5) * panelRect.width  + panelRect.left;
        const y = -(vector.y * 0.5 - 0.5) * panelRect.height + panelRect.top;
        const behindCamera = vector.z > 1 || vector.z < -1;
        const rect = billboard.getBoundingClientRect();
        const NODE_CLEARANCE_PX = 110;
        billboard.style.left = `${Math.min(panelRect.right - rect.width - 20, Math.max(panelRect.left + 20, x + NODE_CLEARANCE_PX))}px`;
        billboard.style.top  = `${Math.min(panelRect.bottom - rect.height - 20, Math.max(panelRect.top + 20, y - rect.height / 2))}px`;

        const svg  = document.getElementById('billboard-arrow-svg');
        const line = document.getElementById('billboard-arrow-line');
        if (svg && line) {
            const bbRect    = billboard.getBoundingClientRect();
            const cx        = (bbRect.left + bbRect.right)  / 2;
            const cy        = (bbRect.top  + bbRect.bottom) / 2;
            let anchorX = cx, anchorY = cy;
            const dx = x - cx, dy = y - cy;
            if (dx !== 0 || dy !== 0) {
                const tX = dx > 0 ? (bbRect.right  - cx) / dx : dx < 0 ? (bbRect.left - cx) / dx : Infinity;
                const tY = dy > 0 ? (bbRect.bottom - cy) / dy : dy < 0 ? (bbRect.top  - cy) / dy : Infinity;
                const t  = Math.max(0, Math.min(tX, tY));
                anchorX = cx + dx * t; anchorY = cy + dy * t;
            }
            const insideBillboard = x >= bbRect.left && x <= bbRect.right && y >= bbRect.top && y <= bbRect.bottom;
            if (behindCamera || insideBillboard) {
                svg.style.display = 'none';
            } else {
                svg.style.display = '';
                line.setAttribute('x1', anchorX); line.setAttribute('y1', anchorY);
                line.setAttribute('x2', x);       line.setAttribute('y2', y);
                let cssColor = '#c0c0c0';
                const entry = this.nodeInstanceMap.get(this.selectedId || this.hoveredId);
                if (entry) cssColor = `#${entry.originalColor.getHexString()}`;
                line.setAttribute('stroke', cssColor);
                const markerPolygon = svg.querySelector('marker polygon');
                if (markerPolygon) markerPolygon.setAttribute('fill', cssColor);
            }
        }
    },
};
