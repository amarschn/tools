# Launch Plan

## Current Reality

- **Traffic:** Zero (site exists but not discoverable)
- **Domain:** transparent.tools (hosted on Netlify) ✓
- **Donation link:** Ko-fi set up on all tool pages ✓
- **Tools:** 39 total, 0 formally verified
- **Discoverability:** None (no SEO, no marketing, no domain authority)

This plan addresses what needs to happen before any monetization makes sense.

---

## Phase 0: Pre-Launch Requirements

### 0.1 Establish Core Verified Tools (5 minimum)

Before launch, need 5 tools that are:
- Fully tested against known solutions
- Equations verified against standards/textbooks
- Edge cases handled gracefully
- Mobile-responsive
- Clear "Verified" badge displayed

**Candidate tools for verification (based on current state):**

| Tool | Category | Verification Effort | Notes |
|------|----------|--------------------| ------|
| Bolt Torque Calculator (VDI 2230) | Mechanical | Medium | VDI 2230 standard, well-documented, high value |
| Beam Bending Calculator | Mechanical | Medium | Standard formulas |
| Unit Converter | Reference | Low | Straightforward validation |
| Battery Runtime Estimator | Electrical | Low | Simple math |
| Wire Sizing Calculator | Electrical | Low | NEC tables exist |
| Heat Transfer Calculator | Thermal | Medium | Standard correlations |
| Reynolds Number Explorer | Fluids | Low | Simple formula |

**Priority order for first 5 verified tools:**
1. Unit Converter (low effort, high utility)
2. Reynolds Number Explorer (low effort, simple formula)
3. Battery Runtime Estimator (low effort)
4. Bolt Torque Calculator (VDI 2230) (medium effort, high value for engineers)
5. Beam Bending Calculator (medium effort, common use case)

**Verification process for each tool:**
- [ ] Document expected outputs for 5+ test cases
- [ ] Compare against hand calculations or known software
- [ ] Test edge cases (zero, negative, extreme values)
- [ ] Peer review if possible
- [ ] Add "Verified" badge with verification date

### 0.2 Experimental Badge System ✓ DONE

The catalog (`index.html`) automatically handles badge display:
- Tools WITHOUT `human-verified` tag → "Experimental" badge (orange)
- Tools WITH `human-verified` tag → "Verified" badge (green)
- Priority tools also get "Up Next" badge
- Status dropdown filter (All / Verified only / Experimental only)

**To mark a tool as verified:** Add `"human-verified"` to its `tags` array in `catalog.json`.

### 0.3 Domain & Basic Infrastructure

| Task | Priority | Status |
|------|----------|--------|
| Register domain (transparent.tools) | High | ✓ Done |
| Set up Netlify hosting | High | ✓ Done |
| Configure custom domain | High | ✓ Done |
| Set up Ko-fi donation links | Low | ✓ Done |
| Set up basic analytics (GA4) | Medium | ✓ Done |
| Create robots.txt and sitemap | Medium | ✓ Done |
| Create About page | Medium | ✓ Done |
| Create Terms/Privacy page | Medium | ✓ Done |

---

## Phase 1: Soft Launch

### 1.1 Minimum Viable Launch Checklist

- [ ] 5 verified tools with badges
- [x] All other tools marked "Experimental"
- [x] Custom domain configured
- [x] Analytics installed (GA4)
- [x] Terms of Service page
- [x] Privacy Policy page
- [x] About page (who made this, why, transparency about AI)
- [x] Contact method (Ko-fi linked from About page)
- [ ] Mobile responsive confirmed
- [x] Basic SEO (titles, descriptions, sitemap)

### 1.2 Initial Traffic Sources (Free)

| Source | Effort | Expected Impact |
|--------|--------|-----------------|
| Reddit (r/engineering, r/mechanicalengineering, r/AskEngineers) | Low | Medium - if genuinely useful, not spammy |
| Hacker News | Low | High if it catches on, unpredictable |
| LinkedIn personal network | Low | Low-Medium |
| GitHub trending | Low | Low |
| Engineering Discord servers | Low | Low-Medium |
| University subreddits | Low | Low |

**Key principle:** Don't spam. Share when genuinely relevant to discussions. "I made this" posts work once.

### 1.3 Content Marketing (Slow but Sustainable)

| Content Type | SEO Value | Effort |
|--------------|-----------|--------|
| Blog posts explaining calculations | High | Medium |
| Tutorial videos (YouTube) | Medium | High |
| Worked examples in tool pages | High | Low |
| Comparison articles (vs. competitors) | Medium | Medium |

---

## Phase 2: Growth

### 2.1 SEO Strategy

**Target keywords (long-tail first):**
- "bolt torque calculator vdi 2230"
- "beam bending calculator with diagram"
- "battery runtime calculator mah"
- "free engineering calculator online"
- Specific standards: "ISO 898-1 bolt calculator"

**Content approach:**
- Each tool page is a landing page
- Background/theory section helps SEO
- Worked examples target specific searches
- Blog posts for broader topics

#### SEO-First Tools That Convert

People pay when the tool answers a decision-blocking question: "Is this safe?" "Is this allowed?" "Can I send this to a client?"

Best-converting categories:
- **Acceptable/pass-fail checks:** deflection limits, bolt safety factor, breaker sizing, noise exposure, vibration limits, thermal rise vs insulation class
- **Sizing tools:** wire gauge, motor sizing, heat sink size, fan CFM, pipe diameter, battery capacity
- **Diagnostics/inverse tools:** "why did this fail" explainers, trip curve visualizers, spectrum/OASPL explainers
- **Comparison tools:** AC vs DC, aluminum vs steel, series vs parallel, single-phase vs three-phase
- **Utilities as on-ramps:** unit conversion, dB/log helpers, Hz/RPM/EO, percent/ppm (ads acceptable here, link to higher-value tools)

#### Design for SEO Conversion

- Answer the query above the fold: tool + result + one-line explanation
- Show full results before any gate; pay only to export/save/share/batch
- Use engineer-centric copy: "verify", "check", "estimate", "compare", "validate"
- Make assumptions explicit; add sensitivity and scenario comparisons
- Make paid artifacts inevitable: compliance reports, audit trails, presentation-ready exports

#### Low-Conversion Tool Types (Avoid Early)

- Random generators, timers, basic math widgets, novelty visualizers
- Education-only tools with no exportable artifact or decision outcome

#### Initial SEO-First Tool Ideas

1. Deflection + stress checker with pass/fail
2. Motor current vs breaker + wire size
3. Noise exposure + regulatory check
4. Thermal rise vs insulation class
5. EO frequency explainer with spectrum input

### 2.2 Backlink Opportunities

| Source | How |
|--------|-----|
| Engineering blogs | Guest posts, mentions |
| University course pages | Reach out to professors |
| GitHub awesome-lists | Submit to relevant lists |
| Stack Exchange | Answer questions, link when relevant |
| Wikipedia (careful) | Add as external reference if appropriate |

### 2.3 Community Building

- GitHub Discussions for feature requests
- Discord server (optional, high maintenance)
- Email newsletter (low effort, high value)
- Twitter/X for updates

---

## Success Metrics by Phase

### Pre-Launch (Phase 0)
- [ ] 5 tools verified (add `human-verified` tag in catalog.json)
- [x] Experimental badges on all others (automatic via index.html)
- [x] Domain registered and configured
- [x] Ko-fi donation links added
- [x] Basic analytics working (GA4 on all pages)
- [x] robots.txt and sitemap created
- [x] About page
- [x] Terms of Service / Privacy Policy

### Soft Launch (Phase 1)
- [ ] 100 unique visitors in first month
- [ ] At least 1 external mention/link
- [ ] No critical bugs reported

### Growth (Phase 2)
- [ ] 1,000 monthly visitors
- [ ] Appearing in search results for target keywords
- [ ] 10+ GitHub stars
- [ ] First donation or sign of monetization viability

---

## Timeline (Realistic)

| Milestone | Target |
|-----------|--------|
| 5 verified tools complete | Week 2-3 |
| Domain + Netlify configured | Week 1 |
| Soft launch (share on Reddit/HN) | Week 3-4 |
| First 100 visitors | Week 4-6 |
| First 1,000 visitors | Month 2-3 |
| Monetization experiments | Month 3+ (only if traffic exists) |

---

## Anti-Goals

Things we're NOT doing yet:
- Paid advertising (no point without proven product-market fit)
- Complex monetization (ads, subscriptions)
- Building features no one asked for
- Scaling before validating

---

## Open Questions

1. ~~What domain name?~~ → **transparent.tools** ✓
2. ~~Which 5 tools to verify first?~~ → Unit Converter, Reynolds Number, Battery Runtime, Bolt Torque, Beam Bending
3. ~~How to display experimental vs. verified in the UI?~~ → Automatic badges in catalog + filter dropdown ✓
4. Who can help verify tools? (peer review)
5. What's the "about" story? (transparency about AI, personal project, etc.)

---

*Last updated: 2026-01-12*
