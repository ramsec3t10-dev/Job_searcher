"""Job matching & gap analysis prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import INT, STR, PromptTemplate, arr, obj

JOB_MATCH = PromptTemplate(
    system_prompt=(
        "Role: technical recruiter matching an embedded engineer to a job. Assess fit "
        "honestly. score, interview_probability and salary_confidence are 0-100. "
        "transferable_skills are candidate skills that partly cover a missing requirement. "
        "recommended_action is one of apply_now, upskill_first, stretch, skip. "
        "growth_potential is one line. Output ONLY valid JSON:\n"
        '{"score":int,"reasoning":str,"matched_skills":[str],"missing_skills":[str],'
        '"transferable_skills":[str],"interview_probability":int,"salary_confidence":int,'
        '"growth_potential":str,"recommended_action":str}'
    ),
    user_template="Candidate profile:\n{candidate_profile}\n\nJob:\n{job}",
    task_type=TaskType.MATCHING,
    max_tokens=1024,
    expected_output_schema=obj(
        score=INT,
        reasoning=STR,
        matched_skills=arr(STR),
        missing_skills=arr(STR),
        transferable_skills=arr(STR),
        interview_probability=INT,
        salary_confidence=INT,
        growth_potential=STR,
        recommended_action=STR,
    ),
)

GAP_ANALYSIS = PromptTemplate(
    system_prompt=(
        "Role: career gap analyst for embedded engineering. For the specific job, "
        "separate critical_gaps (blockers) from nice_to_have_gaps. estimated_upskill_weeks "
        "is realistic full effort. learning_priority orders skills to learn first. "
        "immediate_focus is the single next skill. Output ONLY valid JSON:\n"
        '{"critical_gaps":[str],"nice_to_have_gaps":[str],"estimated_upskill_weeks":int,'
        '"learning_priority":[str],"immediate_focus":str,"gap_summary":str}'
    ),
    user_template="Candidate profile:\n{candidate_profile}\n\nTarget job:\n{job}",
    task_type=TaskType.MATCHING,
    max_tokens=1024,
    expected_output_schema=obj(
        critical_gaps=arr(STR),
        nice_to_have_gaps=arr(STR),
        estimated_upskill_weeks=INT,
        learning_priority=arr(STR),
        immediate_focus=STR,
        gap_summary=STR,
    ),
)
