# Interview bank data files (Phase 7)

One JSON file per subrole. `scripts/seed_interview_bank.py` loads every
`*.json` file here (idempotently — safe to re-run as tiers are added).

**Filename:** `<subrole_code>.json` (e.g. `backend_engineer.json`).

**Schema**

```json
{
  "domain_code": "software_it",
  "subrole_code": "backend_engineer",
  "questions": [
    {
      "question_text": "…",
      "category": "technical | behavioral | case_study | system_design",
      "difficulty": "junior | mid | senior",
      "model_answer_guideline": "what a strong answer covers (a guideline, not a script) — optional",
      "source_type": "curated | generated"
    }
  ]
}
```

`domain_code` must be a seeded JobDomain code (see `scripts/seed.py`).
Actual question data files are added per tier in a later phase.
