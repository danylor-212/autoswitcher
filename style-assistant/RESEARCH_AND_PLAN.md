# Personal Style Assistant: Research & Build Plan

> Working name: **"Stylist"**. A private web app for one person (my wife, London, UK), and maybe more people later. Prices below are in USD where providers quote USD.
> Research date: **2026-10-14**. Prices and API availability change often. Anything marked ⚠️ needs checking before you rely on it.
> How to use this file: copy it into a new empty repo as `docs/PLAN.md`, open Claude Code in that repo, and paste the **Kickoff prompt** from section 11.

---

## 1. What we're building (one paragraph)

She uploads a few photos of herself and enters her body measurements. The app works out her **colour palette** (seasonal colour analysis) and her **body shape and proportions**. It learns her **style preferences** through a short quiz and swipe session. From these it builds a **"Style Passport"**: her colours, her silhouettes, what to avoid, and her style keywords. Then it plans a **functional, modern capsule wardrobe**, searches real shops for matching items, and shows product cards that link to the retailer. On any item she can press **"Try it on me"** to see an AI-generated image of herself wearing it.

## 2. Core user flow

```
Onboarding ─► Photos + measurements + lifestyle/budget/sizes
     │
     ▼
Colour analysis  (automatic estimate + interactive "drape test" she confirms)
Body analysis    (from measurements → shape + proportion rules)
Style discovery  (swipe outfits she likes or dislikes → style keywords)
     │
     ▼
STYLE PASSPORT  (palette swatches, flattering cuts, avoid-list, keywords)
     │
     ▼
Capsule plan    (Claude: "you need 2 trousers, 1 blazer, 3 tops…" + why)
     │
     ▼
Product search  (real shops) ─► filter by colour/size/budget ─► ranked cards
     │
     ▼
Virtual try-on  (on demand, cached) ─► like / dislike / buy link
     │
     ▼
Feedback loop   (likes and dislikes refine the next recommendations)
```

## 3. Research findings

### 3.1 Getting products: "ASOS and other shops by API"

**Key finding: ASOS does not appear to have a public product API today.** (Confidence: medium-high.) Retail Week reported years ago that ASOS planned a developer portal, but I found nothing showing it exists now. ASOS runs an **affiliate programme** through networks, which gives tracked links and possibly product feeds. Unofficial "ASOS APIs" on RapidAPI and Apify are **scrapers**. They break often, ASOS blocks them (Akamai bot protection), and they probably break ASOS's terms. **Recommendation: don't build on scrapers.**

The options, ranked for this project:

| Option | What it gives | Pros | Cons | Use when |
|---|---|---|---|---|
| **Google Shopping via a SERP API** (e.g. SerpApi `google_shopping`, or alternatives such as Bright Data/Apify) | Search "camel wool coat women" and get title, price, shop, image, link across *many* shops, ASOS included | Fastest to build, one integration covers many retailers, good for a private app | Paid (⚠️ roughly $50–75/mo per a third-party comparison; check this), sizes and stock not always shown, images are small thumbnails | **MVP (Stage 2)** |
| **Awin Publisher Product Feeds** | Full product feeds (JSON Lines via the Publisher Product API) with size and colour attributes, deep links, and affiliate commission | Official, rich data, large catalogue of UK/EU fashion retailers, legal | Needs a publisher account approved by each retailer; feeds are big (you store them locally and search them yourself); not every advertiser is on the new feed system | **Later (Stage 5)**, if you want better data or commission |
| **Affiliate aggregators** (e.g. Affiliate.com product search, Rakuten, CJ, Impact) | Normalised product search across networks | One API, many networks | ⚠️ Vendor claims are unverified; approval needed | Alternative to Awin |
| **Retailer scrapers** (ASOS on Apify/RapidAPI) | ASOS catalogue | Direct ASOS data | Fragile, blocked, against ToS | **Avoid** |

**Design decision:** hide all of these behind a single `ProductSource` interface (`search(query, filters) → Product[]`). Start with a SERP API and add Awin feeds later without changing the rest of the app.

### 3.2 Virtual try-on ("show how the clothes look on her")

| Option | Notes | Cost (⚠️ check) | Licence |
|---|---|---|---|
| **FASHN API** (fashn.ai) | Purpose-built try-on API. `tryon-v1.6` is the standard model; `tryon-max` gives higher quality but takes about 50 s. Inputs are a model photo plus a garment image (a product flat-lay or on-model photo works) | Official help page: **$0.075/image on demand**, cheaper on monthly tiers. Try-On Max reportedly costs 4 credits per image | Commercial use OK |
| **Google Vertex AI Virtual Try-On** (`virtual-try-on-001`) | Good quality | ~$0.06/image (aggregator figure) | ⚠️ A deprecation notice has been reported, with the Gemini 3.x image models suggested as the replacement. **Don't build on it.** |
| **Gemini image models / other general image-edit models** | Prompt: "dress person in image A in garment B" | ~$0.04–0.10 | Identity and garment fidelity is less reliable than with dedicated try-on models. Use as a fallback only |
| **fal.ai hosted models** (FASHN, Leffa, Kling Kolors, FLUX try-on) | One API key gives access to several try-on models you can A/B test | ~$0.04–0.10/generation | Varies by model |
| **Open-source** (CatVTON, IDM-VTON) running on your own GPU | Free to run, private | GPU needed | **CC BY-NC-SA 4.0 (non-commercial)**. Fine for a private family app, **not** for a product you sell |

**Recommendation: FASHN API** behind a `TryOnProvider` interface, with fal.ai as the second provider for comparison. Budget estimate: 100 try-ons/month ≈ $7.50 (confidence: medium; based on the published on-demand price).

**Quality tips (build these into the upload UI):** use a full-body, front-facing photo in good even light with a plain background, fitted clothes, and arms slightly away from the body. Use a separate photo for tops and bottoms if needed. Store 2–3 "try-on base photos" and let her pick the best one.

### 3.3 Colour analysis (which colours suit her)

The established method is **seasonal colour analysis** with **12 seasons**. There are 4 seasons (Spring, Summer, Autumn, Winter), each split into 3 sub-types. The three dimensions are **undertone** (warm/cool), **value** (light/deep), and **chroma** (bright/soft), plus the **contrast** between skin, hair and eyes.

**Biggest risk: lighting.** Phone photos shift skin tone a lot, so a fully automatic answer is unreliable. A hybrid approach works best:

1. **Measured estimate.** Detect face landmarks (MediaPipe Face Landmarker, in the browser or with Python). Sample cheek/forehead skin, hair, and iris pixels and convert them to the **CIELAB** colour space. Compute undertone (ratio of b* to a*), lightness L*, chroma, and skin/hair/eye contrast. Ask for a photo in daylight, without makeup, and ideally holding a **white sheet of paper** so the app can correct white balance.
2. **Vision interpretation.** Send the photos and the measured numbers to Claude (vision). It returns a top-3 list of seasons with confidence scores and its reasoning, as structured JSON.
3. **Interactive drape test (key feature).** Show her face cropped above coloured "drapes" (a coloured bib under the chin), two at a time: warm vs cool, bright vs muted, light vs deep. She (or you) picks which looks better. This is how human colour analysts work, it's cheap to build (canvas overlay, no AI), and it fixes the AI's mistakes.
4. Result: **season + palette** (about 30–40 hex colours), **neutrals** (base colours for the capsule), **accent colours**, and **colours to avoid near the face**.

### 3.4 Body shape (which cuts suit her)

**Use measurements, not photo inference.** It's more accurate, more private, and less awkward. Inputs: height, shoulders, bust, waist, high hip, hip, and optionally inseam and torso length.

- Classify shape from the ratios: hourglass, pear/triangle, inverted triangle, rectangle, apple/round. Use standard formulas (for example the published "FFIT" body-shape rules). Show the result gently, as "your proportions", not as a label.
- Proportions: petite/tall, short-waisted/long-waisted, leg-to-torso ratio.
- Map these to **silhouette rules**: necklines, rises, lengths, where to add or reduce volume, and fabrics with structure vs drape.
- Optional later: **Kibbe** body types. They're popular but subjective; let Claude suggest one with a confidence score and let her disagree.

### 3.5 Style preference and "functional but modern"

- **Lifestyle intake:** work dress code, days per week at the office, kids or active life, climate, how often she goes to events, budget per item, sizes per brand, fabrics she hates (e.g. no wool on the skin), ethical preferences.
- **Swipe session:** 30–50 outfit images (inspiration set) → derive style keywords (e.g. "minimal, smart-casual, Scandinavian, soft tailoring").
- **Capsule wardrobe logic** for "functional": every new item must combine with at least N others. Claude plans a capsule (e.g. 25–35 pieces) from her lifestyle, palette and shape. Later, when she uploads her *existing* clothes, it plans only the **gaps**.

### 3.6 Ranking products against her profile

1. Claude turns each "capsule slot" into search queries, e.g. `{"slot":"tailored trousers","query":"high waisted wide leg tailored trousers women","colors":["camel","chocolate","olive"],"avoid":["skinny","low rise"]}`.
2. Search the product source(s).
3. **Colour check:** extract the garment's dominant colour from the product image (k-means in LAB, ignoring background and skin) and compute **ΔE (CIEDE2000)** to her palette. Drop anything far from it.
4. **Fit check:** Claude vision reviews the product image and title against her silhouette rules and returns a score from 0–1 plus a one-line reason ("A-line midi balances hips; works with your Soft Autumn camel").
5. Filter by price and size, deduplicate, and show the top N.

### 3.7 Privacy and safety (these are photos of your wife)

- Run the app **locally / self-hosted**. Store photos on disk or in a private bucket and never make them public. Single-user auth (even a simple password).
- Photos go to third parties: Claude API (analysis) and FASHN (try-on). ⚠️ Read both providers' data retention terms and use any zero-retention or delete options they offer. Strip EXIF/GPS from every upload.
- Add a "delete all my data" button.
- Keep swimwear/underwear out of try-on at first. Some providers block it anyway (one developer reported this for the Gemini image models).

## 4. Recommended tech stack

| Layer | Choice | Why |
|---|---|---|
| App | **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui** | One codebase for UI and API routes; Claude Code knows it well; works well on mobile (she'll use her phone) |
| DB | **SQLite + Drizzle ORM** (switch to Postgres if it ever goes multi-user) | Zero setup, local |
| File storage | Local `./data/uploads` folder at first; later S3/R2 | Simple |
| AI reasoning and vision | **Claude API** (Anthropic SDK) with **structured outputs / tool use** for JSON results | Colour/season reasoning, capsule planning, fit scoring, stylist chat |
| Face landmarks | **MediaPipe Face Landmarker** (in the browser, `@mediapipe/tasks-vision`) | Free, runs on her device, no upload needed for the measurements |
| Colour maths | `culori` (LAB, ΔE2000) | Small and well tested |
| Product search | SerpApi (or similar) Google Shopping → Awin later | See 3.1 |
| Try-on | FASHN API (fal.ai as an alternative) | See 3.2 |
| Jobs | Simple DB-backed job table + polling (try-on takes 10–50 s) | No Redis needed |
| Mobile | Make it a **PWA** so she can "Add to Home Screen" | Feels like an app |

Hosting: run it on your machine first. To reach it from her phone, use the home network or a Tailscale/Cloudflare Tunnel. Deploy (e.g. Vercel + Turso + R2) later if needed.

## 5. Data model (first draft)

```
User(id, name, heightCm, sizes JSON, budget JSON, lifestyle JSON)
Photo(id, userId, kind[face|full_body|tryon_base], path, createdAt, whiteBalanceRef?)
ColorAnalysis(id, userId, measurements JSON(L,a,b per region, contrast), aiTop3 JSON,
              drapeResults JSON, finalSeason, palette JSON{core,neutrals,accents,avoid}, confidence)
BodyProfile(id, userId, measurements JSON, shape, proportions JSON, silhouetteRules JSON)
StyleProfile(id, userId, keywords[], swipeLikes[], swipeDislikes[], notes)
StylePassport(id, userId, version, summary MD, createdAt)   -- snapshot of all three above
CapsulePlan(id, userId, slots JSON[{slot, qty, colors, mustHave, avoid, reason}])
Product(id, source, externalId, title, brand, price, currency, url, affiliateUrl?, imageUrl,
        dominantColorLab, colorDeltaE, fitScore, fitReason, fetchedAt)
Recommendation(id, userId, capsuleSlot, productId, rank, status[new|liked|disliked|bought])
TryOn(id, userId, productId, basePhotoId, provider, status, resultPath, cost, createdAt)
WardrobeItem(id, userId, photoPath, category, colorLab, notes)   -- Stage 4
```

## 6. Build stages

Each stage ends with something she can actually use. **Don't start the next stage until she has used the current one.**

### Stage 0: De-risk spike (½–1 day, mostly no code)
- [ ] Take 3 good photos of her (face in daylight, full body). Run 5 ASOS products through the **FASHN web playground** by hand. **Is the try-on quality good enough for her?** This decides whether try-on is the centrepiece or a side feature.
- [ ] Try one SERP API free tier: search 5 typical queries in your country, check that ASOS/Zara/M&S/etc. results come back with images and prices.
- [ ] Give Claude (claude.ai) her face photos and ask for a seasonal colour analysis, to get a feel for its quality.

### Stage 1: Profile and Style Passport (MVP 1)
- [ ] Next.js skeleton, SQLite, simple password auth, upload with EXIF stripping
- [ ] Onboarding wizard: measurements, sizes, budget, lifestyle
- [ ] Colour: MediaPipe sampling → LAB metrics → Claude top-3 seasons → **drape test UI** → final palette
- [ ] Body: shape and proportion calculator → Claude silhouette rules
- [ ] Style: swipe session over a curated inspiration set (start with ~40 images you collect yourself)
- [ ] **Style Passport** page (nice to look at, shareable PDF or image)
- ✅ Done when: she reads her Style Passport and agrees with it (or corrects it through the drape test)

### Stage 2: Capsule plan and real product recommendations (MVP 2)
- [ ] Claude capsule planner → slots with reasons
- [ ] `ProductSource` interface + SERP API implementation, with response caching (save money)
- [ ] Dominant-colour extraction + ΔE filter + Claude fit scoring
- [ ] Recommendation feed per slot: cards with image, price, shop, "why it suits you", buy link
- [ ] Like / dislike / hide-brand feedback that goes back into the next run
- ✅ Done when: she finds ≥3 items she actually wants to buy

### Stage 3: Virtual try-on
- [ ] `TryOnProvider` interface + FASHN implementation (async job + polling, result cached per product × base photo)
- [ ] Download the garment image from the product URL; pick the best base photo (top vs bottom vs dress)
- [ ] Try-on gallery, side-by-side comparison of 2–4 items, monthly spend counter with a hard limit
- ✅ Done when: try-on images help her decide (yes/no) on real purchases

### Stage 4: Her existing wardrobe and outfits
- [ ] Upload photos of her current clothes → auto-categorise + colour
- [ ] Gap analysis: the capsule plan only recommends what's missing
- [ ] Outfit generator ("3 outfits for Monday office + dinner") using owned and wishlist items
- [ ] "Stylist chat": ask anything, with her passport as context

### Stage 5: Nice-to-haves
- [ ] Awin product feeds (affiliate links, size and stock data), price-drop alerts
- [ ] Seasonal refresh ("autumn 2026 trends in your palette")
- [ ] Multi-user (friends/family) → Postgres, proper auth, provider zero-retention settings

## 7. Rough running costs (personal use)

Confidence: **low-medium**. These are estimates from published or third-party prices. Check each one.

| Item | Assumption | ~Monthly |
|---|---|---|
| Claude API | Analyses once, then ~200 fit-scoring/planning calls/month | ~$5–20 |
| Try-on (FASHN) | 100 images at $0.075 | ~$7.50 |
| Product search (SERP API) | Smallest paid plan, aggressive caching | ~$0–75 (some have free tiers) |
| Hosting | Local / home | $0 |

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Colour analysis wrong because of lighting | White-balance reference + drape test with her confirmation + manual override |
| Try-on looks fake or changes her face or body | Stage 0 spike; offer 2 providers; frame try-on as "rough preview", not exact |
| Product APIs change, block, or cost too much | `ProductSource` abstraction + caching; no scraping |
| Recommendations feel generic | Swipe feedback loop; "why" explanations she can disagree with; ban lists |
| Body-shape labels feel hurtful | Present as "proportions and what flatters", never as a judgement; she can hide labels |
| Privacy | Local storage, EXIF strip, provider retention settings, delete-all button |
| Scope creep | Strict stages; each stage must be used before moving on |

## 9. Open questions (answer before or during Stage 0)

1. ~~Country / currency / shops~~ **Answered: London, UK.** Use GBP, UK sizes (UK 6–20 / EU equivalents stored too), SERP region `gl=uk`/`google.co.uk`, and UK delivery. Shop shortlist to check during Stage 0: ASOS, M&S, Next, John Lewis, Zara, Mango, COS, Arket, & Other Stories, Uniqlo, H&M, Reiss, Whistles, Me+Em, Boden. Awin is a strong fit for the later affiliate stage because many UK fashion retailers use it (confidence: medium; check which of these brands are on Awin, Rakuten or Partnerize).
2. **Budget:** per item and per month, and API spend you're comfortable with (e.g. $20/month cap)?
3. **Device:** will she mostly use her phone? (Assumed **yes**, so the app is mobile-first and a PWA.)
4. **Existing wardrobe:** does she want to include clothes she already owns (Stage 4), or only shop new ones?
5. **Language** of the UI: English or another language?
6. **Her involvement:** will she do the drape test and swipe session (≈15 min)? It improves results a lot.
7. **Try-on importance:** must-have, or nice-to-have? (Stage 0 answers this.)
8. **Local only**, or should it be reachable from her phone outside home?
9. **Clothing scope:** everyday + work only, or also occasion wear, shoes and accessories?

## 10. Suggested `CLAUDE.md` for the new repo

```md
# Stylist – personal style assistant
Private, single-user web app. See docs/PLAN.md for full research and staged plan.

## Rules
- Build ONLY the current stage (see "Current stage" below). Ask before starting the next one.
- Stack: Next.js App Router + TS + Tailwind + shadcn/ui, SQLite + Drizzle, local file storage.
- All external services behind interfaces: ProductSource, TryOnProvider, StylistLLM.
- All LLM outputs that drive logic must be structured JSON validated with zod.
- Secrets only in .env.local (ANTHROPIC_API_KEY, SERPAPI_KEY, FASHN_API_KEY). Never commit them.
- Photos are sensitive: strip EXIF, never log image data, never expose /data publicly.
- Cache every paid API response; enforce a monthly spend cap in config.
- Mobile-first UI. Test at 390px width.
- Write small tests for pure logic (colour maths, body-shape classification, ranking).

## Current stage
Stage 1 – Profile & Style Passport
```

## 11. Kickoff prompt for local Claude Code

> Paste this into Claude Code in a new empty folder after copying this file to `docs/PLAN.md`.

```
Read docs/PLAN.md fully. We're building the app described there, step by step.

First, before writing code:
1. Ask me the open questions from section 9 that are still unanswered (location is answered: London, UK — GBP, UK shops).
2. Create CLAUDE.md from section 10.
3. Propose a concrete task breakdown for Stage 1 only (files, components, DB tables,
   API routes, prompts), with an order of work. Wait for my approval.

Then implement Stage 1 in small, working increments:
- scaffold Next.js + TS + Tailwind + shadcn/ui + Drizzle/SQLite + simple password auth
- onboarding wizard (measurements, sizes, budget, lifestyle)
- photo upload with EXIF stripping, stored under ./data (gitignored)
- colour analysis: MediaPipe face landmarks in the browser -> sample skin/hair/eyes ->
  CIELAB metrics (use culori) -> Claude vision call returning top-3 seasons as zod-validated
  JSON -> interactive drape test (face crop above coloured bib, A/B choices) -> final palette
- body profile: shape/proportion classifier from measurements (pure function + unit tests)
  -> Claude call producing silhouette rules JSON
- swipe session over images in ./data/inspiration -> style keywords
- Style Passport page combining everything, mobile-first

After each increment: run lint/typecheck/tests, show me how to try it, and commit.
Use the latest Claude model via the Anthropic SDK; put the model id in config.
Don't start Stage 2 until I say so.
```

## 12. Sources

- ASOS developer data (old Retail Week article): https://retail-week.com/tech/asos-to-open-data-to-external-web-developers/5032186.article
- ASOS affiliate overview (third-party, figures unverified): https://www.creator-hero.com/fr/blog/asos-affiliate-program-in-depth-review-pros-and-cons
- ASOS unofficial scrapers (why to avoid them): https://apify.com/lentic_clockss/asos-scraper.md
- Awin Publisher Product API: https://developer.awin.com/apidocs/retail-publisher-productapidocumentation-1
- Awin product feed docs: https://help.awin.com/docs/product-feed.md
- Affiliate.com product feed API (vendor claim): https://blog.affiliate.com/ai-product-feed-api-for-shopping-feeds/
- SerpApi Google Shopping posts: https://serpapi.com/blog/tag/google-shopping-api
- FASHN API pricing: https://help.fashn.ai/plans-and-pricing/api-pricing
- FASHN Try-On Max: https://fashn.ai/changelog/api-try-on-max-endpoint-now-available
- FASHN developer guide (open-source licence caveats): https://fashn.ai/blog/so-you-want-to-build-a-virtual-try-on-app-a-developers-guide-to-not-getting
- Try-on API comparison (fal.ai): https://fal.ai/learn/tools/best-virtual-try-on-apis-2026
- Google Virtual Try-On price listing: https://cloudprice.net/models/google-virtual-try-on-1
- Vertex AI release notes (deprecations): https://docs.cloud.google.com/vertex-ai/generative-ai/docs/release-notes
- Forum report on VTO deprecation and swimwear filter: https://discuss.ai.google.dev/t/urgent-escalation-request-project-allowlist-for-vertex-ai-imagen-gemini-image-safety-filters-virtual-try-on-continuity/183510
- CatVTON licence (CC BY-NC-SA 4.0): https://gitee.com/analyzesystem/CatVTON
- IDM-VTON licence: https://huggingface.co/Elabd/IDM-VTON
