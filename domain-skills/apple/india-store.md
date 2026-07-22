# apple.com/in — Apple India online store

Buying / configuring Macs and reading price + delivery estimates.

## URLs

- Buy landing: `https://www.apple.com/in/shop/buy-mac/mac-mini`
- **Config pages are directly navigable by slug** — no need to click through the chip picker:
  `…/buy-mac/mac-mini/m4-pro-chip-12-core-cpu-16-core-gpu-48gb-memory-512gb-storage`
  Slug = `<chip>-chip-<cpu>-core-cpu-<gpu>-core-gpu-<mem>gb-memory-<storage>gb-storage`.
  An **invalid slug silently redirects to the buy landing page** (`/buy-mac/mac-mini`) — verify `page_info().url` after goto; if it dropped the slug, your option combo doesn't exist.

## Configurator

- Options are `<input type=radio>` with names like `memory-dimensionMemory`,
  `m4pro-processor-dimensionChip-cpuCoreCount-gpuCoreCount`, `storage-dimensionCapacity`.
- Clicking a radio rewrites the URL to the new config slug — confirm the change by reading the slug.
- Live total is the `MRP ₹… (inclusive of all taxes)` string (grep page text); the big "From ₹…/mo … or ₹…" near the chip cards is the *static* base price, not the running total.

## Delivery estimate (the useful part)

- The page shows `Delivers to: <pin> (Get Delivery Dates) <date range> (Free)` and a store-pickup line.
  Apple pre-fills `<pin>` from IP / prior visit.
- To change pincode: click **"(Get Delivery Dates)"** → a **"Delivery Options" modal** opens with a PIN input
  pre-filled like `Current Location - 560009`.
- **Plain typing / Cmd-A+Backspace does NOT clear it** (typeahead field). Use the React-safe native setter:
  ```js
  const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
  set.call(inp,''); inp.dispatchEvent(new Event('input',{bubbles:true}));
  set.call(inp,'560038'); inp.dispatchEvent(new Event('input',{bubbles:true}));
  inp.dispatchEvent(new Event('change',{bubbles:true}));
  ```
  then click **"View Options"**. The page-level "Delivers to:" text may lag (stale background DOM) — trust the modal.
- **Delivery dates are regional, not per-pincode**: 560038 and 560009 (both central Bengaluru, Apple Hebbal store) return the identical range. Don't burn calls chasing an exact pincode when a nearby one already resolved.

## Mac mini facts (verified Jun 2026)

- **M4 Pro Mac mini maxes at 48GB RAM** — only 24GB / 48GB offered, on *both* 12-core and 14-core CPU. No 64GB (that's Mac Studio / M4 Max). 48GB = +₹40000 over 24GB base.
- Base M4 Pro (12-core/16-core/24GB/512GB) = **₹1,49,900**; +48GB → ₹1,89,900.
- **14-core CPU upgrade (+₹20000) is supply-constrained: "Ships 10–12 weeks."** The 12-core + 48GB BTO is faster (~10–11 weeks, e.g. order mid-Jun → 28 Aug–4 Sept). If lead time matters, avoid the 14-core.
- Storage ladder: 512GB incl / 1TB +₹20000 / 2TB +₹60000 / 4TB +₹120000 / 8TB +₹240000. 10GbE +₹10000.

## Connection note

Chrome 149 returns **HTTP 404 on `/json/version` and `/json`** even when remote debugging is on; the browser
WS URL comes from the `DevToolsActivePort` file instead — browser-harness handles this. A wedged CDP endpoint
(port LISTENs but HTTP never responds) is fixed by a graceful `quit` + relaunch of Chrome.
