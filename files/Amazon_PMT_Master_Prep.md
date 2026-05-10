# Amazon PM-T Master Prep

> **Purpose**: Single source of truth for Amazon PM-T interview prep. Replaces 8 source files (LP question bank, PMT Guide, PM Interview process, PM-T vs TPM transcript, PMT key skills, Amazon Interview Questions PDF, PM Prep Guide 2016, PM Leveling xlsx).
>
> **Scope**: PM-T (Product Manager – Technical) for Vinayak. Companion files: `Candidate_Profile_Master.md`, `AI_ML_Reference.md` (ConsolidatedAIQB), and (pending) System Design OCR.

---

## 1. The Loop — what actually happens

**Timeline**: 4–6 weeks total. Faster than other FAANGs.

**Stages**:
1. **Resume screen** — ~90% of candidates filtered here. Resume is the highest-leverage artifact.
2. **Recruiter call** — 30 min. Standard. Some recruiters slip in 1–2 LP questions.
3. **Hiring manager / peer phone screen** — 60 min. Half PM competencies, half LP. PM-T candidates: technical product-lifecycle knowledge in the second half.
4. **Writing assessment** — 1–2 pages, sent ~48 hours before the loop. Two prompts, pick one. Common asks: *most innovative project you led* or *time you simplified a complex experience for customers*. Interviewers read it and may probe it during the loop.
5. **Onsite loop** — 5 rounds × 60 min. Mix of peers, hiring manager, senior leader, and one **Bar Raiser** (more on this below).
6. **Decision** — recruiter follow-up within 5 days.

**Each onsite round** focuses on **2–3 of the 16 LPs** plus product/technical/stakeholder skills. You're rated 1–5 across four skill areas:
- Leadership Principles
- Functional product skills (strategy, vision, execution)
- Technical depth
- Stakeholder management

**Bar Raiser**: Outside the hiring team, has veto power, focused on culture/LP fit beyond team-specific needs. Often probes one or two LPs hard. Trained to keep the bar from drifting down. Treat Bar Raiser as the highest-stakes round, not the lowest.

**Down-leveling**: Amazon down-levels often. If your scope of work, technical depth, or stakeholder narrative doesn't match the target level, they'll offer the level below. Misalignment with any LP = immediate "no hire."

---

## 2. PM-T vs PM vs TPM — get this straight

| Role | Owns | Tech depth | Typical question |
|---|---|---|---|
| **PM** (e-commerce, retail) | Product features, customer experience | Light. No CS background needed. | "How would you make Amazon.com better?" |
| **PM-T** (AWS, AI, devices, infra) | Product strategy + tech architecture decisions | Deep. Must defend architectural choices. CS/eng background expected. | "Tell me about the architecture of your last product." |
| **TPM** (engineering program mgmt) | Lifecycle delivery of complex systems | Deepest. Whiteboards system designs in interviews. | "Design a system with these ambiguous requirements." |

**For Vinayak (target: PM-T)** — your CS undergrad + 4 years SWE + Vinsight architecture work is your moat vs. generalist PMs. **Lead with technical fluency.** Don't be the PM who hand-waves on system trade-offs.

PM-T technical depth they probe:
- System design (at least one round; "quasi-system-design" common: *"walk me through the architecture of X"*)
- Identifying when a design is over-engineered or limits scale
- Influencing engineering teams on architectural decisions
- SQL (rare but possible)
- Domain tech (if AI role: ML basics; if AWS: cloud primitives)

**No coding interviews** for PM-T.

---

## 3. PM Leveling — L5 vs L6 (from Amazon's own rubric)

Confirm with your recruiter which level you're targeting. Pay sits ~30–40% higher at L6.

| Dimension | L5 (PM II) | L6 (PM III) |
|---|---|---|
| **Ambiguity** | Strategy is defined; you nail down feature design & business approach | Strategy may not be defined; you define vision + design + business approach with limited guidance |
| **Scope** | Manages product features; influences customers, vendors, external partners, eng priorities | Manages a product or major features; influences strategic direction & org priorities |
| **Execution** | Voice of customer; tactical; mitigates risks; **begins** to mentor | Tactical + strategic; aligns stakeholders; makes time/effort/feature trade-offs; **actively** mentors; may own launch coordination |
| **Communication** | Drives feature discussions; PR/FAQs; functional specs; may train sales | Drives vision/goals/tenets/roadmap/narratives at exec level; contributes to OP1; sales training |
| **Impact** | CX, feature usability, team-level business goals | Product brand, segment adoption, **eng roadmaps**, org-level business goals |
| **Experience** | MBA + up to 2 yrs PM | MBA + 5+ yrs PM |

**Vinayak's profile maps to L6** based on years (8) and scope (Zynga PM II owning two titles, $1M+ DTC migration, GoMechanic B2B platform). The interview will test whether your stories *demonstrate* L6 scope, not just whether your tenure suggests it.

**L6 promotion signals** (from the rubric):
- Influence technical priorities & business strategy through data-driven contributions
- Make a case for resource allocation
- Build narratives, PR/FAQs, strategic docs
- Foster constructive dialogue, harmonize discordant views (Earn Trust + Disagree and Commit)
- Set up mechanisms (audits, metrics, evaluation standards) — i.e., process, not just delivery
- Proactively identify risks with mitigation plans

These are the bar a Bar Raiser is checking against. Stories should signal them implicitly.

---

## 4. The 16 Leadership Principles — definitions (single source)

> Use this as your reference. Don't memorize verbatim, but understand each.

1. **Customer Obsession** — Start with the customer and work backwards. Earn and keep customer trust. Pay attention to competitors but obsess over customers.
2. **Ownership** — Think long-term. Don't sacrifice long-term value for short-term results. Act on behalf of the entire company, not just your team. Never say "that's not my job."
3. **Invent and Simplify** — Expect and require innovation. Find ways to simplify. Externally aware. Not limited by "not invented here." Accept being misunderstood for long periods.
4. **Are Right, A Lot** — Strong judgment, good instincts. Seek diverse perspectives. Work to **disconfirm** your own beliefs.
5. **Learn and Be Curious** — Never done learning. Always seek to improve. Curious about new possibilities and act on them.
6. **Hire and Develop the Best** — Raise the performance bar with every hire/promotion. Recognize and move exceptional talent. Coach others. Career Choice.
7. **Insist on the Highest Standards** — Standards many think are unreasonably high. Continually raise the bar. Don't send defects down the line. Fix problems so they stay fixed.
8. **Think Big** — Thinking small is a self-fulfilling prophecy. Bold direction. Different thinking. Look around corners for ways to serve customers.
9. **Bias for Action** — Speed matters. Many decisions are reversible and don't need extensive study. Calculated risk-taking.
10. **Frugality** — Accomplish more with less. Constraints breed resourcefulness, self-sufficiency, invention. No bonus for headcount/budget/expense.
11. **Earn Trust** — Listen attentively. Speak candidly. Treat others respectfully. Vocally self-critical. Benchmark against the best.
12. **Dive Deep** — Operate at all levels. Stay connected to details. Audit frequently. Skeptical when metrics and anecdote differ. No task beneath you.
13. **Have Backbone; Disagree and Commit** — Respectfully challenge decisions. Conviction and tenacity. Don't compromise for social cohesion. Once decided, commit wholly.
14. **Deliver Results** — Focus on key inputs. Right quality, timely. Despite setbacks, never settle.
15. **Strive to be Earth's Best Employer** — Safer, more productive, higher-performing, more diverse, more just work environment. Lead with empathy. Have fun. Help people grow.
16. **Success and Scale Bring Broad Responsibility** — We're big and impact the world. Be humble and thoughtful about secondary effects. Create more than you consume. Leave things better.

---

## 5. PM-T Priority LPs — what interviewers weight most

Per ex-Amazon PM-T interviewers and Diana (Amazon Sr. PM):

**Top 7 for PM-T loops**:
1. Customer Obsession
2. Invent and Simplify
3. Are Right, A Lot
4. Think Big
5. Earn Trust
6. Dive Deep
7. Have Backbone; Disagree and Commit

**By product stage** (Diana's framework — adjust your story emphasis to the team):
- **Defining vision from scratch** → Think Big + Invent and Simplify
- **Driving the team forward / removing blockers** → Bias for Action + Ownership
- **Shipping** → Deliver Results
- **Cross-functional alignment** → Earn Trust + Disagree and Commit
- **Always** → Customer Obsession

**By role universally probed**:
- Top 5 questions across all Amazon roles: *"Why Amazon"*, *failure*, *challenge*, *disagreement*, *tight-deadline decision*. Have rock-solid answers to these — they show up regardless of LP focus.

---

## 6. Question Bank — by LP (deduplicated)

> Practice these out loud. Map your stories from `Candidate_Profile_Master.md` § 7.

### Customer Obsession
- Tell me about a time you had to deal with a difficult customer.
- Describe a time when a customer asked you for one thing, but you knew they needed something else.
- Tell me about a time you went above and beyond for a customer.
- Tell me about a time you couldn't meet a customer demand. *(Or: said no to a customer request and why.)*
- Tell me about a project where you put the customer first.
- Tell the story of the last time you had to apologize to someone.
- How have you measured customer satisfaction in the past?
- When working with many customers, how do you prioritize?

### Ownership
- Tell me about a time you did something at work that wasn't your responsibility.
- Tell me about a time you had to make an important decision without approval from your boss.
- How would you make Amazon.com better?
- Tell me about a project you took full ownership of and the outcome.
- Tell me about a time you took complete ownership of a project and drove it to completion despite obstacles.
- Tell me about a time you designed a plan and failed to execute it. Why?
- Tell me about a time you had to leave a task unfinished.
- Tell me about a time you had to work on a project with unclear responsibilities.

### Invent and Simplify
- Tell me about a time you re-designed/improved a process and why.
- Tell me about a time you solved a big problem in your company.
- Tell us about a time you solved a really complex problem with a simple solution.
- Tell me about a time you gave a simple solution to a complex problem.
- Tell me about a time you created a new way of doing something that gave the company a competitive advantage.
- Tell me about an out-of-the-box idea you had and its impact.

### Are Right, A Lot
- Tell me about how you deal with ambiguity.
- Tell me about a time you applied judgment to a decision when data was not available.
- **Tell me about a time you were wrong.** *(Critical — see § 9 gap analysis.)*
- Tell me about a recent event where you went against the natural flow or group conviction. How did it pan out?
- Describe a time you made a decision against the suggestion of your larger team.
- Tell me about a time you had to work with incomplete data and were proposing a solution others doubted that turned out in your favor.

### Learn and Be Curious
- Tell me about a time you had to learn something quickly.
- Tell me about your biggest career failure and what you learned.
- Tell me about a time you taught yourself a skill.
- What did you learn recently?
- Tell me about a time you realized you didn't have the skills needed for the job.
- Tell me about a time you influenced a change by only asking questions.

### Hire and Develop the Best *(senior/mgr roles primarily)*
- Tell me about a time you provided feedback that was helpful to a peer.
- Tell me about a time you hired or worked with people smarter than you.
- Tell me about a time you stepped in to help a struggling teammate.
- Tell me about a time you coached a member of your team.
- Talk about a time you fired someone.

### Insist on the Highest Standards
- Tell me about the most successful project you've done.
- Tell me about a project that you wish you had done better.
- Tell me about a time you had a goal that was hard to achieve.
- How would you improve [project on your resume] if you had more time?
- Tell me about a time you couldn't meet your own expectations.
- Tell me about a time a teammate didn't meet your expectations.
- Tell about a time you had to trade off quality vs. timely delivery.

### Think Big
- Tell me about your most significant accomplishment. Why was it significant?
- Tell me about a time you proposed a non-intuitive solution.
- What was the largest project you've executed?
- Tell me about a time you challenged the status quo.
- Give me an example of how you innovated in your area.
- Tell me about a time you went way beyond the scope and delivered.

### Bias for Action
- Tell me about a time you had to make an urgent decision without data.
- Tell me about a time you launched a feature with known risks.
- Tell me about a time you found an opportunity no one else saw.
- Describe a time you saw a problem and took initiative to correct it instead of waiting.
- Tell me about a time you took a calculated risk.
- Tell me about a time you saw an issue your team could face and proactively mitigated it.
- Tell me about a time you had to change approach to avoid missing a deadline.
- Tell me about a time you had to pivot.

### Frugality
- Tell me about a time you delivered with limited budget or resources.
- Tell me about a time you figured out how to keep an approach simple or save expenses.
- Describe a time you needed a bigger budget but didn't get it. How did you overcome it?
- Tell me about a time you saved money for the company in a clever way.

### Earn Trust
- How do you earn trust within a team?
- Tell me a piece of difficult feedback you received and how you handled it.
- A coworker constantly arrives late to a recurring meeting. What would you do?
- Tell me about a time you managed cross-functional stakeholders.
- Tell me about a time the team's trust was damaged by you or someone else, and how you fixed it.
- How do you communicate to stakeholders when there's a change in direction?
- What would you do if you found out your closest friend at work was stealing?
- Tell me about a time you had to tell someone a harsh truth.

### Dive Deep
- Tell me about a project where you had to deep dive into analysis.
- Tell me about the most complex problem you've worked on.
- Tell me about a time you used a lot of data in a short period.
- Tell me about a time you devised a new way of looking at data that improved performance.
- Describe a time you personally resolved a challenging technical situation that should have been done by someone else.
- How do you ramp up to learn a new space/area?

### Have Backbone; Disagree and Commit
- **Tell me about a time you disagreed with your manager.** *(Asked in nearly every PM-T loop.)*
- Tell me about a time you had a conflict with a coworker/manager and how you approached it.
- Tell me about a time when people in your team didn't agree with you.
- Tell me about a time your manager challenged you to think differently.
- Have you ever stood against your boss to address a customer situation?
- Tell me about a time you had to persuade a stakeholder to take a different approach.
- Tell me about an unpopular decision of yours.
- If your direct manager was instructing you to do something you disagreed with, how would you handle it?

### Deliver Results
- Tell me about a time the deadline given was earlier than expected.
- Tell me about the most challenging project you've worked on.
- Tell me about a time you had to handle pressure.
- Tell me about a project where you oversaw implementation from design to delivery.
- Tell me a situation where you didn't hit your goal. How did you manage?
- Give me an example of a time you not only exceeded a goal but vastly surpassed it.
- Tell me about a time you were 75% of the way through a project and had to pivot strategy.
- Tell me about a time you had significant obstacles delivering a project. *(Diana's favorite.)*

### Strive to be Earth's Best Employer *(senior/mgr)*
- How do you manage a low performer?
- Tell me about a time you went above and beyond for an employee.
- How do you identify a good performer and help their career growth?
- Tell me about a time you saw an issue that could negatively impact your team.

### Success and Scale Bring Broad Responsibility
- Tell me about a time you made a decision that impacted the team or company.
- Tell me about a decision about your work that you regret now.
- Tell me about a time you failed to do the right thing.
- Talk about a time you were halfway to a goal and realized it might not be the best goal.

### Coaches' favorite cross-LP probes (high signal, multi-LP)
- *"Tell me about a time you had significant obstacles delivering a project."* (Diana — covers Deliver Results, Ownership, Disagree and Commit, Customer Obsession, follow-up gold mine.)
- *"Tell me about a time you had to deliver something with very limited resources or tight constraints."* (Anurag — Frugality + Invent and Simplify + Bias for Action + Ownership.)
- *"Tell me about a time you realized you couldn't meet a commitment on a long-running initiative."* (Artiom — Ownership primary; Deliver Results, Earn Trust, Bias for Action, Dive Deep, Backbone secondary.)

---

## 7. Answer Frameworks

Pick one and stick with it. Don't switch mid-loop.

### STAR (Amazon's official recommendation)
- **Situation** — context (role, team, market). Minimum needed.
- **Task** — specific goal you were working toward.
- **Action** — what *you* did. "I" not "we." Specific steps.
- **Result** — outcome with metrics. What you accomplished. What you learned.

### SPSIL (preferred by many coaches — cleaner separation)
- **Situation** — context.
- **Problem** — what was broken/at stake.
- **Solution** — what you did, with focus on your contribution.
- **Impact** — quantified outcome.
- **Lessons** — what you learned (often the highest-value sentence in the answer).

### Why SPSIL beats STAR
1. STAR's "Task" and "Action" blur — candidates ramble.
2. STAR doesn't enforce **Lessons**, which is what separates a good story from a great one. Amazon interviewers look for self-awareness; "Lessons" forces it.

### Universal rules regardless of framework
- **Set the situation in 30 seconds or less.** This is the #1 mistake — over-narration of context.
- **Use "I" for actions, "we" for team context.** Get the balance right.
- **Quantify everything.** Amazon is data-driven; stories without numbers don't land.
- **End with the lesson.** Even if the framework doesn't ask for it, leadership-level interviewers want it.
- **Adapt to follow-ups.** The interviewer's follow-up questions reveal which LP they're probing in the second layer. Listen carefully.

---

## 8. The Writing Assessment

A 1–2 page narrative document. Two prompts; pick one. ~48 hours before the loop.

**Common prompts**:
- Most innovative project you've led
- Time you simplified a complex experience for customers
- A difficult product decision and how you made it

**What they're scoring**:
- Clear thinking made visible — how you frame problems
- Customer-back reasoning, not feature-out
- Trade-off awareness
- Data-driven decisions
- Cross-functional collaboration
- Ownership of ambiguous scope

**If you don't have Amazon-scale numbers**:
- Frame scale as **incremental benefit** — show before/after.
- Emphasize **complexity** — trade-offs, ambiguity, prioritization tension.
- Highlight **cross-functional collaboration** — multiple teams, misaligned goals, influence without authority.
- Show **work outside your formal scope** — where you stepped up because ownership was unclear.

**Format**: Amazon-native is PR/FAQ — press release for the customer + FAQ for stakeholders. Even if not asked for one, structuring your assessment in PR/FAQ-adjacent style ("imagine the day this launches; what does the customer see?") signals fluency in their writing culture.

**Expect interviewers to reference the doc during the loop.** Be ready to defend every claim with data.

---

## 9. Vinayak's Coach Playbook — what to focus on

### LP coverage assessment (from Candidate_Profile_Master.md § 7)

**Strong** (multiple stories, deep): Customer Obsession, Invent and Simplify, Insist on Highest Standards, Think Big, Frugality, Earn Trust, Dive Deep, Learn and Be Curious.

**Medium** (one story, may need more depth): Ownership, Are Right A Lot, Bias for Action, Deliver Results.

**Weak — gap to close**:
1. **Have Backbone; Disagree and Commit** — *Critical gap.* This is one of the top 7 PM-T LPs and you have no story written. Without this, expect a Bar Raiser "no hire."
2. **Hire and Develop the Best** — Only ISB Recruiter Relations (29-person team). Need a Zynga peer-coaching or junior-PM mentoring story for L6.
3. **Strive to be Earth's Best Employer** — Same gap. L6 expects this.
4. **"I was wrong" recovery story** for Are Right A Lot — Amazon explicitly probes this. Pure-success stories raise red flags about self-awareness.

### Top 5 stories to memorize cold (your strongest)
1. **Zynga DTC webstore $1M+ migration** — Think Big + Deliver Results + Ownership.
2. **CM Fellow — Dialogue Palghar forum, $300K, 11 MOUs** — Earn Trust + Backbone + Think Big.
3. **GoMechanic 45→7 day reconciliation** — Highest Standards + Earn Trust + Bias for Action.
4. **Vinsight 0→1 multi-agent platform** — Learn and Be Curious + Invent and Simplify + Think Big. Use this for technical-depth probes.
5. **Zynga D7 ARPU diagnosis & economy reshape** — Dive Deep + Are Right A Lot. Strongest data-driven decision story.

### Stories to *avoid* leading with
- Anything from Barclays — too junior, ages your timeline.
- Software Engineer GoMechanic — keep for tech-depth probes only, not LP stories.
- 2021 ISB extracurriculars — only as backup color.

### Technical depth — your specific edges
- **Architecture defense**: Vinsight MCP server, hybrid LLM routing, RAG-grounded retrieval. Be ready to whiteboard the agent architecture.
- **Database**: MongoDB migration at GoMechanic — speak to NoSQL trade-offs vs. relational, when each makes sense.
- **Pipelines**: Zynga DLC delivery transition, Vinsight real-time data pipeline — latency / throughput / caching trade-offs.
- **ML basics**: XGBoost stock prediction, churn prediction, social recommendation algorithms. Know precision/recall, train/eval/test, basic loss functions.
- **System design weak areas to shore up**: distributed systems trade-offs (CAP, consistency models), API design, event-driven architectures. *(See companion System Design OCR doc when ready.)*

### Stakeholder management — your story patterns
- **Without authority**: GoMechanic partner ecosystem (thousands of SMBs you didn't formally manage), Dialogue Palghar (80+ NGOs, no command structure).
- **Disagreement → alignment**: *(Need to develop — this maps to the Backbone gap above.)*
- **Influence up**: Zynga LiveOps decisions, prioritization with eng leads.

---

## 10. Sample Answer — for calibration

**Question**: *Tell me about a time you failed at work. What did you learn from it?* (Ownership LP)

**Answer (SPSIL format, ~90 seconds spoken)**:

> **Situation**: At my last role, I was PM for a key feature on a product about to launch. R&D was running ahead of schedule, so in an exec update I told the CPO we'd ship a week early. She was pleased and rearranged downstream launch dates accordingly.
>
> **Problem**: I'd gotten swept up in the early progress and committed to the new date without validating with my eng lead or QA. As we approached integration, late-stage details took longer than I'd planned for. We weren't going to hit the new earlier deadline.
>
> **Solution**: Since the bad commitment was mine, not the team's, I owned the recovery. I took some loose-end tasks onto my own plate to free up engineering, worked extra hours to clean them up, and immediately re-met with the CPO to walk back the commitment. We re-aligned to the original deadline rather than scramble.
>
> **Impact**: We launched on the original date — a few days earlier than original plan, not the full week I'd promised. The launch went clean. But the CPO had moved cross-team commitments based on my word and had to walk those back, which damaged trust in my forecasting.
>
> **Lessons**: Two things. First, I never commit a date upward without validating downstream with the people doing the work. Second, when you do miscommit, the only recovery is fast and visible — own it, fix what you can, and surface the rest immediately. Sitting on bad news to "see if it works out" is the failure mode, not the missed estimate itself.

**Why this works**:
- 30-second situation. ✓
- Failure is genuine, not "I worked too hard." ✓
- Action is specific and personal ("I" not "we"). ✓
- Result is honest about residual damage (trust). ✓
- Lessons are specific and structural, not platitudes. ✓

---

## 11. Interview-Day Tactics

1. **Have your top 5 stories memorized cold** — situation, problem, solution, impact, lessons. You should be able to start any of them in under 5 seconds.
2. **Have 8–10 secondary stories prepped** — at least one per LP for the top 7 PM-T LPs.
3. **Pause before answering.** Asking for 30 seconds to think is a signal of strength, not weakness.
4. **Listen for follow-up clues.** "Walk me through how you decided that" → they want Dive Deep / Are Right A Lot. "What did your manager say?" → they're probing Backbone.
5. **Don't bulldoze.** Backbone stories need to land collaborative. Show conviction, not aggression.
6. **Ask thoughtful questions at the end.** Avoid Google-able questions. Ask about team operating cadence, how the team uses data, what the manager wishes hires did differently in the first 90 days.
7. **Treat it as a conversation.** You're evaluating them too. Do this visibly.

---

## 12. Prep Cadence

If you have **2 weeks** to a loop:
- **Days 1–3**: Lock the resume. Write top 5 stories in SPSIL format. Practice each out loud, timed.
- **Days 4–7**: Fill the LP gaps (Backbone, Hire & Develop, "I was wrong"). Write 5 more stories.
- **Days 8–10**: Mock interview with a peer or coach. Get specific feedback on situation length, "I" vs. "we" balance, lesson clarity.
- **Days 11–12**: Practice technical depth — whiteboard Vinsight architecture, walk through one system design.
- **Days 13–14**: Writing assessment dry run on a likely prompt. Light review only on day before.

If you have **4+ weeks**: same plan but add 2–3 mock interviews and more system design practice.

---

## 13. What's NOT in this doc (intentionally)

- **AI/ML reference content** — see `AI_ML_Reference.md` (ConsolidatedAIQB).
- **System design deep-dive** — pending OCR of System Design PDFs you mentioned you'll add separately.
- **Salary negotiation** — separate concern; tackle after offer.
- **Visual mockups / PR-FAQ samples** — search Working Backwards if you want models.

---

*End of master prep. Update this file as you generate new stories or learn new things from mocks.*
