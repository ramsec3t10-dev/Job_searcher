"""EMBEDHUNT AI — Domain-specific interview kits (Phase 5).

Embedded and software/IT keep using the technical question bank (coding + systems)
via app.interview.generator. Sales and finance interviews look nothing like a
coding screen, so they get purpose-built kits here:

  * Sales   — behavioral/situational (STAR) + live negotiation/objection role-play.
  * Finance — technical-finance case studies (valuation, accounting scenarios) +
              behavioral. No coding topics for either.

Each kit matches the existing InterviewKit shape so the API response is uniform.
"""
from __future__ import annotations

from app.interview.generator import InterviewKit


def _q(q: str, category: str, qtype: str, difficulty: str, model: str = "") -> dict:
    return {"q": q, "question": q, "skill": category, "category": category,
            "type": qtype, "difficulty": difficulty, "model_answer": model}


# ── Sales ────────────────────────────────────────────────────────────────────
_SALES_BEHAVIORAL = [
    _q("Tell me about a deal you lost. What happened and what did you change afterward?",
       "behavioral", "behavioral", "medium",
       "STAR: name the deal, the real reason (not just 'budget'), the specific change to your process, and the measurable result next quarter."),
    _q("Walk me through the largest deal you've closed end to end.",
       "behavioral", "behavioral", "medium",
       "Situation, stakeholders mapped, your discovery, how you built the business case, and the close mechanics."),
    _q("Describe a time you turned a cold, unresponsive prospect into a customer.",
       "prospecting", "behavioral", "medium",
       "Show a repeatable outreach system: research, multi-thread, value-led message, persistence cadence."),
    _q("How do you build and prioritise your pipeline when you have 100 accounts and limited time?",
       "pipeline management", "situational", "medium",
       "ICP fit + intent signals + deal stage velocity; time-box prospecting; forecast honestly."),
]
_SALES_ROLEPLAY = [
    _q("ROLE-PLAY: The prospect says 'Your product is 30% more expensive than a competitor.' Respond live.",
       "objection handling", "role_play", "hard",
       "Acknowledge, isolate the objection, reframe to value/ROI and cost of inaction, quantify, then trial-close — never discount first."),
    _q("ROLE-PLAY: Procurement demands a 20% discount to sign this quarter. Negotiate.",
       "negotiation", "role_play", "hard",
       "Trade, never give: concede on price only for something (term length, case study, faster payment). Hold anchor, protect margin."),
    _q("ROLE-PLAY: Champion loves you but the economic buyer went silent. Re-engage them.",
       "closing", "role_play", "hard",
       "Multi-thread, bring a compelling event / business case to the EB directly, create urgency without desperation."),
]
_SALES_CHECKLIST = [
    "Research the company's product, ICP, and recent funding/news",
    "Prepare 2-3 STAR stories: a big win, a loss you learned from, a turnaround",
    "Know your numbers cold: quota, attainment %, average deal size, win rate",
    "Rehearse a discovery-call opening and 3 qualifying questions",
    "Prepare for a live role-play (objection handling / negotiation)",
    "Have questions ready about territory, comp plan, ramp, and sales tooling",
]

# ── Finance ──────────────────────────────────────────────────────────────────
_FINANCE_TECHNICAL = [
    _q("Walk me through the three financial statements and how they connect.",
       "core_accounting", "technical", "medium",
       "Net income flows to retained earnings (BS) and top of cash flow; CFS reconciles to cash on BS; D&A, working capital and capex link IS↔CFS↔BS."),
    _q("How would you value a company? Walk me through a DCF.",
       "financial_modeling", "case_study", "hard",
       "Project unlevered FCF, discount at WACC, terminal value (Gordon growth or exit multiple), sum PV, bridge EV→equity, sensitivity."),
    _q("A company is profitable but keeps running out of cash. What's going on?",
       "financial_analysis", "case_study", "hard",
       "Working-capital drain (receivables/inventory up, payables down), heavy capex, debt repayments — profit ≠ cash; inspect the CFS."),
    _q("How do you handle a bank reconciliation that won't tie out at month-end close?",
       "core_accounting", "technical", "medium",
       "Systematically: timing differences, unrecorded fees/interest, transposition errors, duplicates; document and adjust with a clear audit trail."),
    _q("Explain deferred revenue and where it appears. Give an example.",
       "compliance_regulatory", "technical", "medium",
       "A liability for cash received before delivery (e.g. annual SaaS prepaid); recognised to revenue over the service period per the standard."),
]
_FINANCE_BEHAVIORAL = [
    _q("Tell me about a time you found a material error or control weakness. What did you do?",
       "behavioral", "behavioral", "medium",
       "STAR: how you found it, materiality assessment, who you escalated to, the fix and the control you added to prevent recurrence."),
    _q("Describe a period-end close under heavy deadline pressure. How did you ensure accuracy?",
       "behavioral", "behavioral", "medium",
       "Checklist discipline, reconciliations, review controls, prioritising material accounts, and not cutting corners on documentation."),
]
_FINANCE_CHECKLIST = [
    "Refresh the 3-statement linkages and a DCF end to end",
    "Prepare accounting-standard examples (revenue recognition, leases, deferrals)",
    "Know the company's business model and unit economics",
    "Prepare 2 STAR stories: an error/control fix and a high-pressure close",
    "Brush up your primary tool (SAP / Tally / Excel) and be ready to talk workflows",
    "Have questions about the team, systems, audit cycle, and growth plans",
]

_DOMAIN_KITS = {
    "sales": (_SALES_BEHAVIORAL + _SALES_ROLEPLAY, _SALES_CHECKLIST,
              "Sales interviews test discovery, objection handling, negotiation and "
              "closing through STAR stories and live role-play — not coding."),
    "finance": (_FINANCE_TECHNICAL + _FINANCE_BEHAVIORAL, _FINANCE_CHECKLIST,
                "Finance interviews combine technical case studies (valuation, "
                "accounting scenarios) with behavioural questions on controls and close."),
}


def has_domain_kit(domain_code: str) -> bool:
    return domain_code in _DOMAIN_KITS


def build_domain_kit(domain_code: str, job_title: str, company: str,
                     matched_skills: list[str], match_score: int) -> InterviewKit:
    questions, checklist, blurb = _DOMAIN_KITS[domain_code]
    by_cat: dict[str, list[dict]] = {}
    for q in questions:
        by_cat.setdefault(q["category"], []).append(q)
    readiness = min(99, match_score + len(questions))
    focus = matched_skills[:5] or sorted(by_cat)[:5]
    summary = (f"{blurb} Estimated readiness: {readiness}/99 for {job_title} at {company}.")
    return InterviewKit(
        job_title=job_title, company=company, readiness_score=readiness,
        questions_by_skill=by_cat, all_questions=questions,
        focus_skills=focus, coding_topics=[],          # never coding for these domains
        checklist=checklist, total_questions=len(questions),
        preparation_summary=summary,
    )
