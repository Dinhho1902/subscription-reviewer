# Subscription Reviewer: the product case

**One line:** an AI review layer that tells a fund admin, within minutes, whether an offline subscription
booklet is in good order, shows the evidence for every field, and leaves only the exceptions for a human.

Sources are listed at the end. Figures marked *(vendor)* come from vendor marketing and are weaker evidence.

---

## 1. Why should this product exist?

**More investors, smaller tickets, same manual review.**
- Private-markets AUM grew from $6.1T (2016) to $16.7T (Dec 2025) [1].
- Growth is shifting to individual investors:
  - US evergreen funds are close to $500B [2].
  - Interval and tender-offer funds took in more than $40B net inflows by Sep 2025, against $35B for all of 2024 [2].
  - Individuals hold only 16% of alternatives AUM, but that share is forecast to grow at a 12% CAGR [3].
- Each new investor is one more booklet to check, so review work grows with investor count, not with capital raised.

**Fundraising is harder, so every LP counts.**
- Global fundraising is on track to fall for a fifth straight year [1].
- A slow or messy onboarding now costs real money. In one survey, 63% of GPs said they lost investors or
  reinvestments because of AML/KYC shortcomings, and 61% named documentation gaps as the cause [4].

**Anduin has digitized online subscriptions. Offline booklets and the final good-order check are still manual.**
- Anduin's adaptive forms already validate online subscriptions [5].
- Offline investors still send PDFs. Instant Extraction (Apr 2026) gets their data out, but its own page
  promises "80%+ accuracy out of the box" and flags low-confidence fields for a human [6].
- Anduin's CEO wants to compress "manual review from days to minutes" [7]. "Review Agent" is on the
  2026 timeline [8], and investor-ops panels at GP Con 2026 favoured exception-based review [9].

**Why now:** models can now read messy documents reliably enough to be measured against a ship gate,
which was not true two years ago.

## 2. What pain does it solve?

**Job to be done:** *"When a subscription arrives, I want to know quickly whether it is in good order and
exactly what is missing, so we close on time without ever accepting a defective subscription."*

| Who | Pain today |
|---|---|
| Fund admin / GP ops reviewer | Checks every booklet page by page: signature, amount in words vs figures, minimum, accreditation, tax form. Anduin itself describes subscriptions processed "one clause at a time and late into the night" [7]. Offline PDFs are re-keyed by hand [6]. |
| LP and their adviser | Finds out late that something is wrong, then goes back and forth by email. |
| GP / investor relations | The close date slips, and some investors drop out [4]. |
| Compliance | The worst case is not a slow review but a wrong acceptance: an investor with no accreditation basis, or the wrong tax form. |

## 3. Is the pain big?

**Yes on time and lost investors; the error rate itself is less certain.**

| Evidence | Strength |
|---|---|
| 74% of GPs say KYC adds 6 to 30 days to fund closings; 48% still run it on spreadsheets and email [10] | Survey, 2026 |
| 63% of GPs lost investors over AML/KYC; documentation gaps were the main cause (61%) [4] | Survey, n=400, 2025 |
| About 50,000 new subscriptions on one platform in 2025 [11]; Anduin serves 76K+ unique investors [5] | Vendor volume counts |
| Even on a digital platform, 20% of subscription documents still need revisions (80% need none) [12] | Vendor |
| 30-60% of investment documents arrive not in good order; fixing one costs 3-4x a clean one [13] | Vendor estimate, 2020 |

**What I could not find:** no independent benchmark for subscription NIGO rates, and no published review
minutes per booklet. Competitors market a first-time-right number [12][14]; Anduin's current pages do not.
That is the first thing I would measure with customers.

**Counter-signal:** in iCapital's 2026 survey, financial advisers ranked automated subscription processing
lower than before (41% to 26%) [15]. The pain sits with GP ops and fund admins, not advisers, so they are
the buyer and the user.

## 4. Is it worth doing?

| Test | Answer |
|---|---|
| Desirable | Survey evidence above; Anduin's own users describe the manual review. |
| Feasible | This prototype: Claude reads the booklet, code checks every quote against the page, rules decide, a human approves. Eval results: see section 6. |
| Strategic fit | Matches Anduin's stated direction (Review Agent, AI-assisted and exception-based review) [8][9]. Reuses what exists: Instant Extraction's confidence flags [6] and the validation rules already encoded in each fund's adaptive form [5]. One rule set for online and offline subscriptions. |
| Competitive | Others are moving: Juniper Square extracts offline subscriptions with AI [16], Carta uses AI on subscription documents [17], Allvue launched Document IQ and agents [18]. Extraction alone is becoming table stakes; a review layer that decides "in good order, with evidence" is not. |
| Risk | Accepting a bad subscription. Controlled by design: code makes every pass/fail decision, Approve is blocked while a critical issue remains, and the ship gate below. |

**Kill criterion, set before testing:** if the pipeline misses any planted critical defect (critical-flag
recall below 100%) or field accuracy is below 95%, it does not ship as an auto-clear feature. It stays an
assistant that pre-fills fields for a human.

## 5. What is the business impact?

**Main success measure:** days from receiving a booklet to a decision (accept or return). This is what
the review layer changes directly.

The share of booklets in good order at first submission (first-time-right rate) becomes the main measure
only in the next phase, when the same checks run as the investor submits (section 7). A review layer
alone finds errors faster; it does not stop investors from making them.

| Level | Metric | Why |
|---|---|---|
| Customer outcome | Days from first submission to acceptance; LP drop-off | What GPs feel at closing |
| Ops efficiency | Reviewer minutes per booklet; share of booklets auto-cleared | The cost the product removes |
| Safety | Critical defects missed in production spot audits (target 0) | The trust that allows auto-clear |
| Anduin | Attach rate to Fund Subscription and Data Extraction; win rate vs competitors; offline investors moved online | Revenue and defensibility |

**Impact model (to fill with customer data in discovery):**
`reviewer hours = booklets x (flagged share x minutes per flagged booklet
                 + (1 - flagged share) x minutes per spot check) / 60`

*Illustrative only.* A big close can mean "over 1000 subscription agreements" to review in a few days [19].
If manual review took 30 minutes, 1,000 booklets cost 500 hours. If 35% are flagged and take 10 minutes
each, and the rest get a 2-minute spot check, review drops to about 80 hours. The 30 minutes, 35%,
10 minutes and 2 minutes are assumptions to measure, not findings. The demo has a calculator for this.

## 6. What I built, and what the evals say

- 20 synthetic offline booklets (invented fund and investors), 11 with planted defects, with ground truth.
- Claude Opus 5.5 extraction with page-and-quote evidence, a grounding check, and a rules engine.
- Review screen: page view, flags, editable fields, approve or return, and a decision log that becomes
  the next eval set.
- Eval harness with the ship gate above, plus cost and latency per booklet.

**Results** (20 booklets, Claude Opus 5.5 at medium effort, run through Claude Code):

| Metric | v1 | v2 |
|---|---|---|
| Critical-flag recall (ship gate 100%) | 12/12 | 12/12 |
| Field accuracy (ship gate 95%) | 100% | 100% |
| Flag precision | 100% | 100% |
| Fields backed by a quote found on the page | 100% | 100% |
| Clean booklets auto-cleared | 7/9 | 9/9 |
| Latency per booklet | 11.3s | 11.5s |
| Cost per booklet (list-price estimate) | $0.09 | $0.09 |

**What changed from v1 to v2:** the model marked fields that do not apply (a signatory title for an
individual) as "uncertain", which sent 2 clean booklets to a human. One sentence in the prompt fixed it.

**What I learned**
- The hardest planted defect passed: figures of 1,500,000 against "One Million Fifty Thousand" in words.
- In v2, every booklet the model marked as uncertain really had a defect. Its doubt is a usable signal.
- In v1 the model doubted the signature on a joint account signed by one holder. My rules do not check
  that every joint holder signs. The v2 prompt change silenced that doubt, so this becomes a rule, not
  something left to the model.

**Why 100% is not the headline.** Twenty clean, digitally generated booklets make an easy test. Real
booklets are scanned, handwritten, longer and come with side letters. The next eval set has to come from
real NIGO cases (step 1 below). Cost was measured through Claude Code, which adds its own context; a direct
API call should cost less, and that needs measuring too.

## 7. What I would do next

1. **Discovery (weeks 1-2):** sit with 3 fund admins during a close. Measure minutes per booklet, NIGO
   rate and the top five defect types. Replace every assumption in section 5.
2. **Pilot (weeks 3-8):** run on offline booklets after Instant Extraction, review-assist mode only.
   Track critical misses, reviewer minutes and how often reviewers override the model.
3. **Move upstream:** run the same checks when the LP submits, so issues are fixed before they reach
   the admin. That is where NIGO loops actually disappear.
4. **Next rule:** every holder of a joint account must sign (found by the model in v1).
5. **Cut for now:** scanned or handwritten pages, side letters, e-signature validation, a UI for editing
   fund terms.

---

## Sources
1. PitchBook, Q2 2026 Global Private Market Fundraising Report - pitchbook.brightspotcdn.com/74/45/4f36da844589a606c5cea79f2aeb/q2-2026-global-private-market-fundraising-report.pdf
2. PitchBook, Q4 2025 US Evergreen Fund Landscape - pitchbook.brightspotcdn.com/d1/af/a887e3b24b59b3a51fe411f1c8dc/q4-2025-us-evergreen-fund-landscape.pdf
3. Georgetown Psaros Center (citing Bain), Jun 2025 - finpolicy.georgetown.edu/wp-content/uploads/2025/06/Alternative-Investments-by-Individual-Investors_-The-Next-Frontier-for-Private-Equity.pdf
4. CSC survey via City A.M., 17 Nov 2025 - cityam.com/?p=2379053
5. Anduin, Fund Subscription and homepage - anduintransact.com/solutions/anduin-fund-subscription ; anduintransact.com
6. Anduin, Instant Extraction for offline investors - anduintransact.com/blog/offline-investors-data-extraction
7. Anduin CEO, "Building what private markets run on" - anduintransact.com/blog/building-what-private-markets-run-on
8. Anduin, About (2026 timeline) - anduintransact.com/about
9. Anduin, GP Con 2026 recap - anduintransact.com/blog/gp-con-2026-investor-operations
10. IQ-EQ fund managers' KYC survey, 30 Apr 2026 - iqeq.com/insights/from-back-office-formality-to-front-line-differentiator-five-key-findings-from-our-fund-managers-kyc-survey
11. Juniper Square, 21 Jan 2026 *(vendor)* - junipersquare.com/news/2025-top-fundraisers-announced
12. Passthrough *(vendor)* - passthrough.com/products/electronic-subscription-documents
13. WealthForge e-guide, May 2020 *(vendor estimate)* - irei.com/real-assets-adviser/white-papers/straight-processing-technology/
14. Atominvest *(vendor)* - atominvest.co/onboarding
15. iCapital advisor survey, 12 Aug 2026 - finance.yahoo.com/markets/stocks/articles/icapital-advisor-demand-alts-stays-180232202.html
16. Juniper Square, investor onboarding *(vendor)* - junipersquare.com/platform/investor-onboarding
17. Carta, Premium Closings *(vendor; page not opened, seen in search results only)* - carta.com/sg/en/blog/premium-closings/
18. Allvue, Oct 2026 - itbrief.com.au/story/allvue-adds-agentic-ai-tools-for-private-markets-platform
19. Cadwalader, Fund Finance Friday, 26 Jul 2024 - fundfinancefriday.com/index.php?nid=305
