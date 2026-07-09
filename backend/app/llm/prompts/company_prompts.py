"""Company intelligence prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import INT, STR, PromptTemplate, arr, obj

COMPANY_INTELLIGENCE = PromptTemplate(
    system_prompt=(
        "Role: interview intelligence analyst for embedded engineering employers. Profile "
        "the company's hiring process for the role. typical_rounds is an integer count. "
        "difficulty is 1-5. known_topics are recurring interview subjects. preparation_tip "
        "and insider_note are one line each. why_work_here is a short honest pitch. "
        "Output ONLY valid JSON:\n"
        '{"interview_style":str,"known_topics":[str],"typical_rounds":int,'
        '"difficulty":int,"preparation_tip":str,"insider_note":str,"why_work_here":str}'
    ),
    user_template="Company: {company}\nRole: {role}",
    task_type=TaskType.INTERVIEW,
    max_tokens=768,
    expected_output_schema=obj(
        interview_style=STR,
        known_topics=arr(STR),
        typical_rounds=INT,
        difficulty=INT,
        preparation_tip=STR,
        insider_note=STR,
        why_work_here=STR,
    ),
)
