# Monetization Roadmap

## Prerequisite: Traffic

**Current traffic: Zero**

Monetization is irrelevant without traffic. This document assumes the [Launch Plan](LAUNCH_PLAN.md) has succeeded and there's meaningful traffic (1,000+ monthly visitors minimum).

See also: [Competitive Analysis](COMPETITIVE_ANALYSIS.md)

---

## Conversion Reality: Monetize Moments, Not Users

Most visitors will never pay. That is expected. Focus on the 2-5% moments where the output matters, gets shared, or carries decision risk.

Key principles:
- Show full results first, then gate artifact actions (export, download, save, batch)
- Avoid signup before value; keep payment transactional, not SaaS
- Prefer one-time purchases early; subscriptions only after trust and repeat use
- Ads are acceptable only when quarantined (sidebar/footer, non-engineering pages)
- Engineers pay to avoid re-doing work: saved configs, history, reproducibility

## Monetization Options (Ordered by Feasibility)

### Tier 1: Zero-Effort Options (Enable Now)

These can be set up immediately with no downside:

| Option | Setup Effort | Expected Revenue | When It Makes Sense |
|--------|--------------|------------------|---------------------|
| GitHub Sponsors | 30 min | $0-50/mo | Any time (0% fees) |
| Ko-fi donations | 15 min | $0-20/mo | Any time |
| Buy Me a Coffee | 15 min | $0-20/mo | Any time |

**Action:** Set up GitHub Sponsors and Ko-fi now. No downside, tiny potential upside, signals project is "real."

---

### Tier 2: Traffic-Dependent Options

Only viable after consistent traffic exists.

#### Artifact Monetization (Pay After Result)

**Flow that converts:**
1. User runs tool
2. Sees full result
3. Clicks export/save/share/batch
4. Soft gate: "One-time $3 export or sign in"

**Why it works:** No trust required upfront, feels transactional, and matches the engineer's need for a verifiable artifact.

**Pricing ideas (early):**
- $2-5 per export (PDF/CSV/XLSX)
- $9 lifetime access to one tool
- $19 category pack

**Access model:** Stripe checkout, no account required. Email receipt can unlock a temporary access link.

#### Display Ads

| Threshold | Platform | Est. RPM |
|-----------|----------|----------|
| Any | Google AdSense | $1-5 |
| 10K pageviews/mo | Ezoic | $8-15 |
| 50K sessions/mo | Mediavine | $15-25 |

**Pros:** Passive, scales with traffic
**Cons:** Hurts UX, competitors are ad-heavy (differentiator to be ad-free?)

**Consideration:** Being ad-free could be a differentiator vs. Engineering Toolbox and Engineers Edge which are cluttered with ads.

#### Affiliate Links

| Program | Relevance | Effort |
|---------|-----------|--------|
| Amazon Associates | Medium (books, tools) | Low |
| Engineering courses | Medium | Low |
| Software trials | Low | Medium |

**Realistic revenue:** $10-100/mo at 10K visitors, highly variable

---

### Tier 3: Premium/Freemium

Subscriptions only make sense after artifact monetization proves demand and trust. Mechanicalc's model ($15/mo or $99/year) is a useful benchmark, but defer until repeat usage is clear.

**Free tier:**
- All tools, ad-free
- Basic functionality

**Premium tier ($8-15/mo or $80-120/year):**
- Export to PDF/Excel
- Save calculations to account
- API access
- Batch calculations
- Priority support
- Early access to new tools

**Implementation complexity:** High (needs auth, payment, feature gating)

**When to pursue:** Only after:
- 5,000+ monthly visitors
- Evidence users want premium features
- Clear feature set that's worth paying for
- Artifact monetization shows repeat purchase behavior

**Payment platform:** Lemon Squeezy (handles global taxes) or Stripe

---

### Tier 4: B2B / Licensing

| Model | Prospects | Revenue Potential |
|-------|-----------|-------------------|
| White-label licensing | Engineering firms | $500-5000/year |
| Educational licensing | Universities | $100-500/year |
| API access | Developers | $50-500/mo |
| Sponsored tools | Manufacturers | $500-2000 one-time |

**When to pursue:** Only after proven consumer traction and demonstrated quality.

---

## What the Competition Does

| Competitor | Primary Revenue | Secondary |
|------------|-----------------|-----------|
| Engineering Toolbox | Display ads | - |
| Engineers Edge | Display ads | Premium membership ($50/yr) |
| Omnicalculator | Display ads | B2B licensing, API |
| Mechanicalc | Freemium ($99/yr) | - |

**Observation:** The market supports both ad-based and freemium models. Mechanicalc proves engineers will pay for quality.

---

## Recommended Path

### Phase 1: Foundation (Now - Month 2)
- Set up GitHub Sponsors and Ko-fi (no downside)
- Focus on launch plan, not monetization
- Don't add ads yet (keep UX clean as differentiator)
- No login gates; build trust in accuracy and speed

### Phase 2: Validate (Month 2-4)
- Track which tools get traffic
- Survey users on what they'd pay for
- Monitor competitor premium features
- Build email list for future premium launch
- Identify the specific paid actions (export/save/share/batch) and instrument demand

### Phase 3: Experiment (Month 4-6, if 5K+ visitors)
- Launch pay-after-result exports with one-time payments, no account required
- Test quarantined ads on non-critical pages (or stay ad-free)
- Soft-launch premium waitlist only if repeat usage is clear
- Explore sponsorship conversations

### Phase 4: Scale (Month 6+, if 10K+ visitors)
- Launch premium tier if demand exists
- Optimize conversion
- Explore B2B

---

## Financial Projections (Conservative)

| Monthly Visitors | Ads Only | Freemium (2% convert @ $10/mo) | Donations |
|------------------|----------|--------------------------------|-----------|
| 1,000 | $3-5 | $20 | $0-10 |
| 5,000 | $15-25 | $100 | $10-30 |
| 10,000 | $30-50 | $200 | $20-50 |
| 50,000 | $150-250 | $1,000 | $50-100 |

**Reality check:** Most side projects never reach 10K monthly visitors. Plan for slow, sustainable growth.

---

## Legal/Business Setup (When Needed)

Only needed once revenue exceeds ~$400/year:

| Task | Cost | When |
|------|------|------|
| LLC formation | $100-500 | When revenue > $600/year |
| EIN | Free | After LLC |
| Business bank account | Free | After EIN |
| Terms of Service | Free (template) | Before launch |
| Privacy Policy | Free (template) | Before launch |

---

## Payment Platforms Comparison

### For Donations
| Platform | Fees | Notes |
|----------|------|-------|
| GitHub Sponsors | 0% | Best for open source |
| Ko-fi | 0-5% | Simple, popular |
| Buy Me a Coffee | 5% | Simple, popular |

### For Subscriptions
| Platform | Fees | Notes |
|----------|------|-------|
| Stripe | 2.9% + $0.30 | Full control, more work |
| Lemon Squeezy | 5% + $0.50 | Handles taxes globally |
| Paddle | 5% + $0.50 | Handles taxes, reseller model |

**Recommendation:** Start with GitHub Sponsors. Move to Lemon Squeezy if/when premium tier launches.

---

## Key Decisions to Make

1. **Ads or ad-free?** Being ad-free is a differentiator but leaves money on the table.
2. **Paid moments?** Which artifacts are worth paying for (export/save/share/batch)?
3. **One-time vs subscription?** Start transactional, add recurring only after trust.
4. **Open source vs. proprietary premium?** Keep core open, premium closed?

---

## Anti-Goals

- Don't optimize for revenue before traffic exists
- Don't add ads until UX/trust is established
- Don't build premium features without user demand signals
- Don't form LLC until revenue justifies it
- Don't require signup before showing results

---

*Last updated: 2026-01-11*
