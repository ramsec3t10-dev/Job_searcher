"""Salary intelligence prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import BOOL, INT, NUM, STR, PromptTemplate, arr, obj

SALARY_ESTIMATOR = PromptTemplate(
    system_prompt=(
        "Role: compensation analyst for the candidate's field. Estimate market "
        "salary in LPA (lakhs per annum) from the profile and location. percentile is the "
        "candidate's current standing 0-100. If current pay is given and below market set "
        "is_underpaid true and underpaid_by to the LPA gap, else false and 0. "
        "top_skills_for_raise are the highest-leverage skills to increase band. "
        "Output ONLY valid JSON:\n"
        '{"estimated_min_lpa":number,"estimated_max_lpa":number,"percentile":int,'
        '"is_underpaid":bool,"underpaid_by":number,"top_skills_for_raise":[str],'
        '"negotiation_tips":[str],"market_reasoning":str}'
    ),
    user_template="Location: {location}\nCurrent LPA: {current_lpa}\n\nProfile:\n{profile}",
    task_type=TaskType.SALARY,
    max_tokens=1024,
    expected_output_schema=obj(
        estimated_min_lpa=NUM,
        estimated_max_lpa=NUM,
        percentile=INT,
        is_underpaid=BOOL,
        underpaid_by=NUM,
        top_skills_for_raise=arr(STR),
        negotiation_tips=arr(STR),
        market_reasoning=STR,
    ),
)
