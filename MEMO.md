# Subscription Reviewer: the product case

**One line:** an AI pre-check that tells a fund administrator, in seconds, whether a subscription booklet
sent as a PDF is in good order, shows the evidence behind every problem, and sends only the booklets
with a problem to a reviewer.

**Live demo:** https://subscription-reviewer.streamlit.app (start with "Try the product", or follow the
six-step story). Code: https://github.com/Dinhho1902/subscription-reviewer

Sources are listed at the end. Figures marked *(vendor)* come from vendor marketing and are weaker evidence.

---

## 1. Why should this product exist?

**More investors, smaller tickets, same manual review.**
- Private-markets AUM grew from $6.1T (2016) to $16.7T (Dec 2025) [1].
- Growth is shifting to individual investors:
  - US evergreen funds are close to $500B [2].
  - Interval and tender-offer funds took in more than $40B net inflows by Sep 2025, against $35B for all of 2024 [2].
  - Individuals hold only 16% of alternatives AUM, but that share is forecast to grow at a 12% CAGR [3].
- Each new investor is one more booklet to check, so review work grows with the number of investors,
  not with the capital raised.

**Fundraising is harder, so every LP counts.**
- Global fundraising is on track to fall for a fifth straight year [1].
- Slow or messy onboarding now costs real money. In one survey, 63% of GPs said they lost investors or
  reinvestments because of AML/KYC problems, and 61% named missing or incomplete documents as the cause [4].

**Anduin has solved online subscriptions. PDF booklets and the final good-order decision are still manual.**
- Investors who subscribe online fill in Anduin's forms, which check the answers as they type [5].
- Investors who send a PDF still need someone to re-key it. Instant Extraction (Apr 2026) pulls the data
  out, but its own page promises "80%+ accuracy out of the box" and leaves fields it is unsure of to a
  person [6].
- Anduin's CEO wants to compress "manual review from days to minutes" [7]. A Review Agent is on the 2026
  timeline [8], and fund operations panels at GP Con 2026 asked for exception-based review [9].

**Why now:** models can now read messy documents well enough to be held to a go-live test set in advance,
which was not true two years ago.

## 2. What pain does it solve?

**Job to be done:** *"When a booklet arrives, I need to know quickly whether it is in good order and
exactly what is missing, so we close on time and never accept a booklet with an error."*

| Who | Pain today |
|---|---|
| Reviewer at the fund administrator or in the GP's operations team | Checks every booklet page by page: signature, amount in words against figures, fund minimum, accredited-investor status, tax form. Anduin itself describes subscriptions processed "one clause at a time and late into the night" [7]. PDF booklets are re-keyed by hand [6]. |
| Investor (LP) and their adviser | Finds out late that something is wrong, then goes back and forth by email. |
| GP and investor relations | The close date slips, and some investors drop out [4]. |
| Compliance | The worst case is not a slow review but a wrong acceptance: no accredited-investor basis, or the wrong tax form. |

## 3. Is the pain big?

**Yes on time and lost investors; the error rate itself is less certain.**

| Evidence | Strength |
|---|---|
| 74% of fund managers say KYC adds 6 to 30 days to fund closings; 48% still run it on spreadsheets and email [10] | Survey, 2026 |
| 63% of GPs lost investors over AML/KYC; missing or incomplete documents were the main cause (61%) [4] | Survey, n=400, 2025 |
| About 50,000 new subscriptions on one platform in 2025 [11]; Anduin serves 76K+ unique investors [5] | Vendor volume counts |
| Even on a digital platform, 20% of subscription documents still need revisions (80% need none) [12] | Vendor |
| 30-60% of investment documents arrive not in good order; fixing one costs 3-4x a clean one [13] | Vendor estimate, 2020 |

**What I could not find:** no independent benchmark for subscription NIGO rates, and no published review
minutes per booklet. Competitors market a first-time-right number [12][14]; Anduin's current pages do not.
That is the first thing I would measure with customers.

**Counter-signal:** in iCapital's 2026 survey, financial advisers ranked automated subscription processing
lower than before (41% to 26%) [15]. The pain sits with fund administrators and GP operations, not
advisers, so they are the buyer and the user.

## 4. Is it worth doing?

| Test | Answer |
|---|---|
| Do customers want it? | Survey evidence above; Anduin's own users describe the manual review. |
| Can it be built? | This prototype: the AI reads the booklet, code checks that every value is backed by a quote on the page, fixed rules decide, a person approves. Test results in section 6. |
| Does it fit Anduin? | Matches Anduin's stated direction (Review Agent, exception-based review) [8][9]. Builds on what exists: Instant Extraction's confidence flags [6] and the rules already in each fund's online form [5]. The same rules can check online and PDF booklets. |
| Competition | Juniper Square already uses AI to pull data from offline subscriptions [16], and Allvue has launched AI document tools and agents [17]. Pulling data out is becoming standard; deciding whether a booklet is in good order, with evidence, is the next step. |
| Risk | Accepting a booklet with an error. Controlled by design: the AI never decides pass or fail, Approve is blocked while a serious error remains, and the go-live test below. |

**Go-live test, set before testing:** the pre-check may clear booklets without a reviewer only if it finds
every serious error in the test set and reads at least 95% of values correctly. Otherwise it stays an
assistant that pre-fills values, and a person still reviews every booklet.

## 5. What is the business impact?

**Main success measure:** days from receiving a booklet to a decision (accept or return). This is what
the pre-check changes directly.

The share of booklets in good order at first submission (first-time-right rate) becomes the main measure
only in the next phase, when the same checks run as the investor submits (section 7). A pre-check alone
finds errors faster; it does not stop investors from making them.

| For | What I would measure after launch | Why |
|---|---|---|
| Investors and GPs | Days from receiving a booklet to a decision; investors who drop out | What GPs feel at closing |
| Reviewers | Minutes per booklet; share of booklets cleared without review | The cost the product removes |
| Risk | Serious errors missed, checked by regular sample audits (target: zero) | The trust that allows clearing without review |
| Anduin | Uptake with Fund Subscription and Data Extraction customers; deals won; investors moved from PDF to online | Revenue and defensibility |

**Reviewer-time model (to fill with customer data in discovery):**
`reviewer hours = booklets x (flagged share x minutes per flagged booklet
                 + (1 - flagged share) x minutes per spot check) / 60`

*Illustrative only.* A big close can mean "over 1000 subscription agreements" to review in a few days [18].
If manual review took 30 minutes, 1,000 booklets cost 500 hours. If 35% are flagged and take 10 minutes
each, and the rest get a 2-minute spot check, review drops to about 80 hours. The 30 minutes, 35%,
10 minutes and 2 minutes are assumptions to measure, not findings. Step 5 of the demo has a calculator
with these as sliders; only the AI's speed and cost per booklet are measured.

## 6. What I built, and what the tests say

**The demo** walks through six steps, each with a PM note and a button to the next one:

1. **The problem:** the closing-week scenario, three sourced figures, who has the problem, and what
   Anduin already solves.
2. **The review queue:** the same 20 booklets with and without the AI pre-check. A diagram shows them
   going through the pre-check into 9 in good order and 11 sent to the reviewer, each with the reason.
3. **Inside one booklet** (the working product):
   - a replayable timeline of what happened to the booklet: AI reading time from the test run, and the
     evidence check and rules timed live (a few milliseconds);
   - the PDF page with the evidence highlighted, plus a zoomed image of the lines behind each problem;
   - a side-by-side card of the values each rule compared, for example "US$1,500,000 in figures"
     against "US$1,050,000 in words";
   - Approve (blocked while a serious error remains), Return to investor with a draft message written
     from the findings, an audit trail, and editable values that re-run the rules;
   - "Simulate the investor's correction": the booklet is checked again and becomes approvable. In
     practice the AI would read the corrected booklet again, which takes about 12 seconds.
4. **How accurate is it?** The go-live test, the results below and the v1 to v2 change.
5. **What does it save?** The reviewer-time calculator and the measures in section 5.
6. **Fit and next steps:** why it fits Anduin and the plan in section 7.

The public demo shows the AI's saved results from the test run; live AI calls and uploads are switched
off. Under the hood: 20 invented booklets (11 with planted errors) with known answers, Claude Opus 5.5
reading each booklet with page-and-quote evidence, an evidence check, fixed rules, and a test harness.

**Results** (20 booklets, Claude Opus 5.5 at medium effort, run through Claude Code):

| Measure | Version 1 | Version 2 |
|---|---|---|
| Serious errors found (go-live test: all) | 12 of 12 | 12 of 12 |
| Values read correctly (go-live test: 95%) | 100% | 100% |
| Problems flagged that were real | 100% | 100% |
| Values backed by a quote found on the page | 100% | 100% |
| Good booklets cleared without a reviewer | 7 of 9 | 9 of 9 |
| AI reading time per booklet | 11.3 s | 11.5 s |
| AI cost per booklet (list-price estimate) | $0.09 | $0.09 |

**What changed from version 1 to version 2:** the AI marked fields that do not apply (a signatory title
for an individual) as "unsure", which sent 2 good booklets to a reviewer. One sentence added to the AI's
instructions fixed it.

**What I learned**
- The hardest planted error was caught: US$1,500,000 in figures against "One Million Fifty Thousand"
  in words.
- In version 2, every booklet the AI was unsure about really had an error. Its doubt is a usable signal.
- In version 1 the AI questioned a joint account signed by only one holder. My rules do not check that
  every joint holder signs. The version 2 change silenced that doubt, so this becomes a fixed rule rather
  than something left to the AI.

**Why 100% is not the headline.** Twenty clean, typed booklets make an easy test. Real booklets are
scanned, handwritten, longer and come with side letters. The next test set has to come from real NIGO
cases (step 1 below). Cost was measured through Claude Code, which adds its own context; a direct API
call should cost less, and that needs measuring too.

## 7. What I would do next

1. **Learn (weeks 1-2):** sit with three fund administrators during a close. Measure minutes per booklet,
   the NIGO rate and the five most common errors. Replace every assumption in section 5.
2. **Pilot (weeks 3-8):** run on PDF booklets after Instant Extraction, with a reviewer still approving
   every one. Track missed errors, reviewer minutes and how often reviewers disagree with the AI.
3. **Check at submission:** run the same checks when the investor submits, so errors are fixed before the
   booklet reaches the administrator. That is where NIGO back-and-forth actually stops.
4. **Next rule:** every holder of a joint account must sign (found by the AI in version 1).
5. **Left out on purpose:** scanned and handwritten pages, side letters, e-signature validation, and a
   screen for editing fund terms.

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
17. Allvue, Oct 2026 - itbrief.com.au/story/allvue-adds-agentic-ai-tools-for-private-markets-platform
18. Cadwalader, Fund Finance Friday, 26 Jul 2024 - fundfinancefriday.com/index.php?nid=305
