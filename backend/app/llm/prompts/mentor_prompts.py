"""Career mentor prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import INT, STR, PromptTemplate, arr, obj

CAREER_ADVICE = PromptTemplate(
    system_prompt=(
        "Role: AI career mentor for the candidate's field. Ground every answer in "
        "the provided career twin, recent history and goals. Be specific and actionable; "
        "prefer concrete next steps over generic advice. priority is high, medium or low. "
        "timeframe is a short phrase (e.g. this week). Output ONLY valid JSON:\n"
        '{"advice":str,"action_items":[str],"priority":str,"timeframe":str}'
    ),
    user_template=(
        "Career twin:\n{career_twin}\n\nRecent history:\n{history}\n\n"
        "Current goals:\n{goals}\n\nQuestion:\n{question}"
    ),
    task_type=TaskType.MENTORING,
    max_tokens=1024,
    expected_output_schema=obj(
        advice=STR,
        action_items=arr(STR),
        priority=STR,
        timeframe=STR,
    ),
)

DAILY_BRIEF = PromptTemplate(
    system_prompt=(
        "Role: morning career dashboard for the candidate. Produce a concise, "
        "energising brief. focus_skill is the one skill to prioritise today and reason "
        "explains why. items are 2-4 dashboard rows; action_route is an app route slug. "
        "Output ONLY valid JSON:\n"
        '{"greeting":str,"focus_skill":str,"reason":str,"new_jobs_count":int,'
        '"top_action":str,"motivational_note":str,'
        '"items":[{"emoji":str,"text":str,"action_route":str}]}'
    ),
    user_template=(
        "Date: {date}\nNew jobs today: {new_jobs_count}\n"
        "Top skill gap: {top_gap}\n\nCareer twin:\n{career_twin}"
    ),
    task_type=TaskType.MENTORING,
    max_tokens=1024,
    expected_output_schema=obj(
        greeting=STR,
        focus_skill=STR,
        reason=STR,
        new_jobs_count=INT,
        top_action=STR,
        motivational_note=STR,
        items=arr(obj(emoji=STR, text=STR, action_route=STR)),
    ),
)
