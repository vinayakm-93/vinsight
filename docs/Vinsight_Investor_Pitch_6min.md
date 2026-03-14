# Vinsight — 6-Minute Investor Pitch Script

**Total Runtime:** ~6 minutes (~900 words at natural pace)  
**Format:** Slide-by-slide with speaker notes and timing cues

---

## SLIDE 1 — THE HOOK (0:00 – 0:30)

> **"How many of you have ever Googled 'Is [stock] a good buy?'"**
>
> You probably got a Reddit thread, a 3-year-old Motley Fool article, and a ChatGPT answer that ended with *"I'm not a financial advisor."*
>
> Here's the reality: **130 million people** have brokerage accounts globally. Most of them *want* to invest. Almost none of them feel *confident* doing it. And the reason isn't that they're not smart enough. It's that the tools designed to make them confident — Bloomberg, FactSet, Morningstar — cost **$25,000 a year.**
>
> **Vinsight exists to close that gap.**

*[Slide visual: Split screen — Bloomberg terminal on one side ($25K/yr), Reddit thread on the other ($0). Vinsight logo in the middle.]*

---

## SLIDE 2 — THE PROBLEM (0:30 – 1:15)

> Over the last twenty years, fintech democratized *access to data*. But it never democratized the *synthesis* of that data. And that's the actual hard part.
>
> A single earnings call transcript is **50,000 words**. An annual report is **200 pages**. A retail investor has maybe 30 minutes on a Sunday. They can't process it. So what do they do? They rely on gut feeling, Reddit sentiment, and confirmation bias — and they make bad decisions.
>
> Meanwhile, the hedge fund across the street has a team of 12 analysts doing nothing but reading those same transcripts and building models. **The information asymmetry isn't about access anymore. It's about processing power.**
>
> And for the first time in history, AI can actually solve that.

*[Slide visual: The "Analysis Gap" — Data is democratized, Synthesis is not. Arrow from raw data → analyst team → investment decision, showing where retail investors fall off.]*

---

## SLIDE 3 — THE SOLUTION (1:15 – 2:15)

> **Vinsight is an AI-native financial intelligence platform.** It does three things that no other product on the market does together:
>
> **One — it reads everything.** We ingest SEC filings, earnings transcripts, market data, and news in real-time. Our AI doesn't browse the web and guess. We feed it verified numbers and force it to reason against hard data.
>
> **Two — it argues with itself.** Our flagship feature is the **Thesis Agent**. You give it your investment idea — say, *"Nvidia will keep growing because of AI infrastructure demand."* The system spins up a **Bull Agent** and a **Bear Agent** that debate each other using the same factual evidence. A **Judge Agent** synthesizes a verdict: Thesis Intact, At Risk, or Broken. It's adversarial by design, because humans aren't. We are hardwired for confirmation bias. This system is structurally engineered to fight it.
>
> **Three — it knows *you*.** Vinsight learns your risk tolerance, your time horizon, your actual financial goals. If you're saving for a house in two years, the system will actively penalize a volatile growth stock — even if the fundamentals are strong. That's fiduciary-grade personalization, available to anyone.
>
> And we've already built and shipped all of this.

*[Slide visual: The Thesis Agent debate flow — Fact Dossier → Bull vs. Bear → Judge Verdict. Clean, simple diagram.]*

---

## SLIDE 4 — THE MARKET & TRACTION (2:15 – 3:00)

> Our immediate market is the **13–19 million "active researcher" retail investors** globally — the people who already pay for tools like Seeking Alpha or Morningstar. That's a **billion-dollar-plus TAM** just on the consumer side.
>
> But the bigger opportunity is **B2B**. There are over **30,000 Registered Investment Advisory firms** in the US alone. They are legally required to document their due diligence. Today, that means junior analysts spending hours writing reports. With Vinsight, an RIA can generate a fully cited, evidence-grounded analysis in minutes. That's not a nice-to-have — it's a compliance cost they're already paying humans to do.
>
> We're live at [**vinsight.page**](https://www.vinsight.page). The product is deployed on Google Cloud Run, the scoring engine has passed 18 regression tests, and the full multi-agent debate system is operational in production.

*[Slide visual: TAM breakdown — Retail ($1B+) + RIA ($300K+ firms) + API/Developer. Small "Live Product" badge.]*

---

## SLIDE 5 — COMPETITIVE MOAT & DEFENSIBILITY (3:00 – 3:45)

> You might ask: *"Why can't ChatGPT just do this?"*
>
> Three reasons.
>
> **First**, general LLMs are sycophantic. Ask GPT *"Why is Tesla a good buy?"* and it will agree with you. Our architecture forces an **asymmetric debate** — the Bear Agent's job is to tear your thesis apart. The structure prevents confirmation bias, not just the prompt.
>
> **Second**, general LLMs hallucinate numbers. Our scoring engine is **deterministic Python** — the AI doesn't compute the score, it only provides a ±10 narrative adjustment. The math is locked down.
>
> **Third**, we're building **three compounding moats**: a behavioral intelligence dataset that gets smarter with every user interaction, a community research marketplace with network effects, and a structured fact database built from raw SEC filings that transforms public data into proprietary, queryable intelligence.
>
> These moats widen with every user and every analysis.

*[Slide visual: "Why Not ChatGPT?" — Three cards: Sycophancy → Adversarial Debate, Hallucination → Deterministic Scoring, Generic → Domain-specialized FinBERT.]*

---

## SLIDE 6 — BUSINESS MODEL (3:45 – 4:30)

> Our model is built on a simple insight: **financial research is episodic, not continuous.** You care a lot during earnings season. You might not log in for three weeks during a flat market.
>
> A fixed $30/month subscription punishes casual users — they churn because they feel they're not using it. And it subsidizes power users who are burning through our LLM budget.
>
> So we built a **credit consumption model on top of a freemium + Pro tier.**
>
> Free users get basic analysis and one Thesis Agent. **Pro users** pay $15–25/month and get 500 credits included — enough for about 10 full deep-dive analyses. If you want more during earnings week, you buy credits on demand. The result: our revenue **scales with the value we deliver**, and our margins stay above **70%** because our Fact Box architecture cuts LLM token consumption by 60%.
>
> Later, Phase 4, we open the API. Hedge funds, trading bots, and other AI agents pay per-thousand-calls for our scoring engine and sentiment endpoints. At that point, we don't even need the retail user — we become **infrastructure.**

*[Slide visual: Pricing tiers — Free / Pro / API. Arrow showing "Revenue scales with value delivered." Margin callout: 70%+.]*

---

## SLIDE 7 — GO-TO-MARKET (4:30 – 5:00)

> Our GTM is designed to be capital-efficient.
>
> **Phase 1 is content-led.** We programmatically generate AI research reports on trending stocks and publish them as SEO content. Every report is a free taste of the product with a CTA to run the full Thesis Agent. Target: 10,000 organic signups in six months at under $5 CAC.
>
> **Phase 2 is creator-driven.** Finance YouTubers and TikTokers need research tools that look good on camera. We give them Pro accounts and they demonstrate the Thesis Agent live. It's authentic product placement.
>
> **Phase 3 is enterprise.** We sell directly to RIA firms. They buy credits in bulk — $500+ a month — because the alternative is paying a junior analyst $60K a year to write the same compliance reports.

*[Slide visual: Funnel — SEO Content → Organic Signups → Free Users → Pro Conversion → Enterprise Expansion.]*

---

## SLIDE 8 — THE ASK (5:00 – 5:30)

> We're raising a **$1.5M seed round** to fund three things:
>
> **One — Hiring.** Three key engineers: a senior Python backend, an ML engineer to fine-tune our FinBERT pipeline, and a frontend specialist for data visualization.
>
> **Two — Infrastructure.** Brokerage integrations via Plaid and Alpaca so users connect portfolios directly — no more CSV uploads. Plus real-time data feeds to support passive monitoring.
>
> **Three — GTM.** Fund six months of content production and five finfluencer partnerships to hit our 10,000-user target.
>
> This gives us **18+ months of runway** to reach profitability on the Pro tier and prove out the RIA enterprise pipeline.

*[Slide visual: Use of funds pie chart — 50% Engineering, 25% Infrastructure, 25% GTM. "18+ months runway."]*

---

## SLIDE 9 — THE CLOSE (5:30 – 6:00)

> Let me leave you with this.
>
> The financial research market has been stuck in two extremes: **$25,000 terminals** for professionals, and **free Reddit threads** for everyone else. Generalist AI models won't solve this — they hallucinate numbers, they agree with you, and they have no memory.
>
> We've built something different. A system that **reads everything, argues with itself, and knows the user.** A system where the AI's explicit job is to protect you from your own biases before you risk your capital.
>
> The product is live. The engine is tested. The moats are compounding.
>
> We're looking for investors who understand that **the future of financial intelligence isn't a better dashboard — it's a reasoning API that powers the next generation of autonomous financial systems.**
>
> Thank you. I'd love to take your questions.

*[Slide visual: Vinsight logo. Single line: "Institutional Intelligence. Universal Access." Website URL.]*

---

## Appendix: Pitch Delivery Notes

### Timing Summary

| Section | Duration | Cumulative |
|:---|:---|:---|
| Hook | 30s | 0:30 |
| Problem | 45s | 1:15 |
| Solution | 60s | 2:15 |
| Market & Traction | 45s | 3:00 |
| Moat & Defensibility | 45s | 3:45 |
| Business Model | 45s | 4:30 |
| Go-To-Market | 30s | 5:00 |
| The Ask | 30s | 5:30 |
| Close | 30s | 6:00 |

### Delivery Tips

1. **Practice the Hook cold.** You need to land that Google question with energy. It's an audience participation moment — make eye contact, pause after the question, let people laugh or nod.

2. **Don't rush the Thesis Agent explanation.** This is your hero feature. Take the full 60 seconds. If you have a live demo available, show the Bull vs. Bear debate happening in real time — 15 seconds of a live product beats 60 seconds of explanation.

3. **Anticipate the ChatGPT question.** Investors will ask it. Rather than waiting for Q&A, address it proactively in the Moat slide. The three-point rebuttal (sycophancy, hallucination, generic) is designed to be remembered.

4. **Hit the numbers hard.** 130M accounts, $25K/yr Bloomberg, 50,000-word transcripts, 30,000 RIA firms, 70% gross margins, 18 months runway. Specificity builds credibility.

5. **End with conviction, not apology.** The close should feel like a statement, not a request. You're inviting them to participate, not asking for help.

### Likely Q&A Questions (Prepare These)

| Question | Key Talking Point |
|:---|:---|
| "How is this different from Seeking Alpha?" | They sell human opinions. We sell adversarial AI synthesis personalized to the user's actual goals. |
| "What's your LLM cost per analysis?" | Under $0.15 per full analysis at current usage. Fact Box optimization reduced token consumption by 60%. |
| "How do you prevent regulatory issues?" | All outputs are educational. No order execution. Hard guardrails prevent definitive recommendations. Disclaimers on everything. |
| "What's your current traction?" | Live product at vinsight.page. Full scoring engine with 18 passing regression tests. Multi-agent debate operational in production. |
| "Why now?" | LLMs can finally read and reason over financial text, but generalist models are guardrailed against finance. Vinsight fills that wedge. Plus, agent-to-agent economy is emerging and needs financial intelligence infrastructure. |
| "What if Bloomberg builds this?" | Bloomberg's moat is data access for institutions. They aren't incentivized to cannibalize $25K/yr terminals with a $25/mo product. Their innovation cycle is measured in years, not weeks. |
