# Toshakhana e-Auction (toshakhanaauction.mea.gov.in) — full catalog extraction

MEA's portal auctioning gifts received by Indian dignitaries. Vue SPA, hash routes, served by NIC/GePNIC. **All product data is AES-encrypted in transit and decrypted client-side** — bare `http_get`/`fetch` returns empty/garbage. The DOM is the decrypted source of truth; the API is reachable too once you know the scheme.

## Connect (dialog-free)
Public site, no login needed to browse. Use the universal dedicated-profile session so Chrome's un-clickable "Allow remote debugging" modal never appears (see `interaction-skills/connection.md`):
```bash
eval "$(browser-harness/automation_session.sh)"   # or --no-auth for a clean profile
```

## URL / route map
- Home: `/#/`
- Live listing: `/#/category?auctionType=bGl2ZQ%3D%3D`  (`bGl2ZQ==` = base64 "live"; also `upcoming`, `closed`, etc.)
- Product detail: `/#/EAuctionProductDetailsBeforeLogin?setAuctionId=<base64(id)>` (needs Buyer login for full spec/bidding)
- Nav links ("Search", "Categories") are Angular click-handlers with **no href** — click by coordinates or `el.click()`. "Search" (top nav) routes straight to the live category listing.

## API endpoints (all under `/toshakhana_rs/`)
- `preLogin/getToken`, `preLogin/homePageContent`
- `OpenAuctionLogin/getCategoriesAndSubCategoriesForMenu`
- `OpenAuctionLogin/getProductsDetails?type=<enc>` — home carousel sections
- `OpenAuctionLogin/getAuctionsByProductCategory` — **the catalog**. POST, body = encrypted `searchParams`, **15 items per call** (server-side pagination via `offset`/`limit`).

## The crypto (from app.<hash>.js, CryptoJS, confirmed 2026-06-26)
AES-CBC + PBKDF2(SHA1), key size 4 words (128-bit), 100 iterations. **Fixed** salt/IV for the `commonEncrypt`/`decrypt` pair the catalog uses:
- salt (hex): `92bd2f379f0846f83b8de8d767b2bf3d`
- IV (hex):   `2f99055bcd81c869a3fa86453365c5b3`
- response body wire format = `base64( base64( ciphertext ) )` → `atob(bodyText)` then `Base64.parse`.
- decrypt output (utf8) **is the JSON string** directly (app does `JSON.parse(atob(btoa(plaintext)))`).

**Passphrase = the per-session, single-use `headerToken`** (NOT a static string like "eAuction"). It signs the request (`Authorization: i`), encrypts the request body (`commonEncrypt(i, JSON.stringify(searchParams))`), decrypts the response (`decrypt(i, atob(bodyText))`), and the response's `Authorization` header is the NEXT token. Forging a request with a token already consumed by the page → HTTP 400. So **don't forge — capture the app's own calls.**

## Extraction recipe (works, ~30s for all ~300 live lots)
1. Fresh-load home, then install an XHR hook **before** navigating (SPA nav keeps the hook; a reload kills it), and inject CryptoJS (CDN is not CSP-blocked here):
```js
window.__cap=[];
var S=XMLHttpRequest.prototype.send,O=XMLHttpRequest.prototype.open,H=XMLHttpRequest.prototype.setRequestHeader;
XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return O.apply(this,arguments);};
XMLHttpRequest.prototype.setRequestHeader=function(k,v){if(/authorization/i.test(k))this.__a=v;return H.apply(this,arguments);};
XMLHttpRequest.prototype.send=function(b){var s=this;this.addEventListener('load',function(){if(/getAuctionsByProductCategory/.test(s.__u))window.__cap.push({a:s.__a,b:s.responseText});});return S.apply(this,arguments);};
// + append <script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/3.1.9-1/crypto-js.min.js">
```
2. Click "Search" → page 1 loads. Then click the **"Next"** `<a>` 19× (20 pages, 15/lot), ~1.6s between — each fires one captured XHR. Stop when no "Next" anchor.
3. Decrypt every capture in-page and dedupe by `id`:
```js
var SALT=CryptoJS.enc.Hex.parse("92bd2f379f0846f83b8de8d767b2bf3d"),IV=CryptoJS.enc.Hex.parse("2f99055bcd81c869a3fa86453365c5b3");
function k(p){return CryptoJS.PBKDF2(p,SALT,{keySize:4,iterations:100});}
function dec(p,t){var c=CryptoJS.lib.CipherParams.create({ciphertext:CryptoJS.enc.Base64.parse(t)});return CryptoJS.AES.decrypt(c,k(p),{iv:IV}).toString(CryptoJS.enc.Utf8);}
var byId={}; window.__cap.forEach(c=>{JSON.parse(dec(c.a,atob(c.b))).forEach(it=>byId[it.id]=it);});
```
4. **Return projected fields only** (drop the huge base64 `image`) — pushing 150KB INTO the daemon over the socket breaks the pipe; ~45KB back is fine.

Item schema: `{id, productName, productnamehindi, currentPrice, highestBid, timeLeft (end datetime), productRefNo, productDeptCode, isFeatured, image (base64 jpeg)}`. `highestBid:0` = no bids → `currentPrice` is the base/starting price.

## Per-lot detail page (base price, live bids, description)
Deep link: `/#/EAuctionProductDetailsBeforeLogin?setAuctionId=<urlencode(base64(id))>` (e.g. id 13479 → `setAuctionId=MTM0Nzk%3D`). The page renders full data **without login**: product name, `Product ID` (= ref/`productRefNo`), Category, **No of Bids Quoted**, Auction Ends On, **Highest Quoted Price**, Minimum Increment, **Base / Starting Price**, and a description paragraph (before the "Product ID" label).

Key value distinction the listing hides: the listing's `currentPrice` ≈ **current high bid** (rises as bids come in), NOT the floor. The true floor is **Base / Starting Price**, only on the detail page, and it's materially lower (e.g. a lot showing listing `currentPrice` ₹9,950 had base ₹4,950 + bids). Always pull base from the detail page if "how cheap is the floor" matters.

**Trap — the detail SPA does NOT refetch on hash/param change.** Navigating `setAuctionId` to a new id (even via `Page.navigate`) shows the *previously loaded* product's data — every id looks identical. Fix: force a clean bootstrap by navigating to `about:blank` first, then to the detail URL:
```python
cdp("Page.navigate", url="about:blank"); time.sleep(1.2)
cdp("Page.navigate", url=detail_url)
# poll innerText until  re.search(r"Product ID\s*:?\s*"+ref)  AND  "Base / Starting Price: <digit>"  (verify ref to confirm it's THIS lot, not stale)
```
~3-5s/item (full bootstrap + XHR). Occasionally a lot's detail XHR hangs on "Loading ..." / "Product ID: " (empty) — retry, or fall back to the listing value for that one.

## Faster alt (DOM only, no crypto)
The live listing renders 15 `.single-products` cards/page, each with the base64 `<img>`, base price, lot code (`productRefNo | productDeptCode`), and end date — but **not the product name** (name shows only on home carousel + detail page). Use the crypto path if you need names+bids for all lots; use DOM if you just need images for visible cards.

## Lot-code prefixes encode category
`WEARWRWT`=wrist watch, `WEARWOTR`=other watch, `ACCJEW`=jewellery, `CROCOTR`=crockery, `CLOTER`=textile, `PLTSLV`/`CUPSSL`=silver, `ELI*`=electronics, `SWD*`=sword/dagger, `IDSS*`=idol/statue, `PNT*`=painting, `STAPNE`=pen. Useful for bucketing by value class.

## Traps
- Same-URL `goto` does NOT refetch (SPA). Use `Page.reload` or SPA nav, but reload wipes injected hooks.
- The daemon's `network_requests()` buffer races against SPA XHR timing — the XHR hook above is more reliable than CDP `Network.getResponseBody` for these.
- `getProductsDetails`/`getAuctionsByProductCategory` returns HTTP 200 with empty body to bare fetches lacking the `Authorization` token.
