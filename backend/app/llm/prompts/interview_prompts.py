"""Interview preparation prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import INT, STR, PromptTemplate, arr, obj

QUESTION_GENERATOR = PromptTemplate(
    system_prompt=(
        "Role: embedded systems interviewer. Generate interview questions for the given "
        "skill and company. type is one of conceptual, coding, design, behavioral. "
        "difficulty is easy, medium or hard. expected_answer_outline is a terse bullet "
        "outline. company_tags note why the question fits that company. "
        "Output ONLY valid JSON:\n"
        '{"questions":[{"text":str,"type":str,"difficulty":str,'
        '"expected_answer_outline":str,"follow_up":str,"company_tags":[str]}]}'
    ),
    user_template="Skill: {skill}\nCompany: {company}\nDifficulty: {difficulty}\nCount: {count}",
    task_type=TaskType.INTERVIEW,
    max_tokens=1536,
    expected_output_schema=obj(
        questions=arr(
            obj(
                text=STR,
                type=STR,
                difficulty=STR,
                expected_answer_outline=STR,
                follow_up=STR,
                company_tags=arr(STR),
            )
        )
    ),
)

ANSWER_EVALUATOR = PromptTemplate(
    system_prompt=(
        "Role: strict but fair embedded interview evaluator. Score the answer to the "
        "question. score, technical_accuracy, communication and depth are 0-100. feedback "
        "is direct and constructive. follow_up_question probes the weakest area. "
        "Output ONLY valid JSON:\n"
        '{"score":int,"technical_accuracy":int,"communication":int,"depth":int,'
        '"feedback":str,"what_was_good":str,"what_was_missing":str,"follow_up_question":str}'
    ),
    user_template="Skill: {skill}\nQuestion:\n{question}\n\nCandidate answer:\n{answer}",
    task_type=TaskType.INTERVIEW,
    max_tokens=1024,
    expected_output_schema=obj(
        score=INT,
        technical_accuracy=INT,
        communication=INT,
        depth=INT,
        feedback=STR,
        what_was_good=STR,
        what_was_missing=STR,
        follow_up_question=STR,
    ),
)

MOCK_INTERVIEW_OPENER = PromptTemplate(
    system_prompt=(
        "Role: interviewer opening a company-specific mock interview for an embedded "
        "engineer. Set a realistic tone matching the company. opening_message greets and "
        "frames the session. first_question starts easy to build rapport. interview_context "
        "notes round type and focus areas. Output ONLY valid JSON:\n"
        '{"opening_message":str,"first_question":str,"interview_context":str}'
    ),
    user_template="Company: {company}\nRole: {role}\nCandidate summary:\n{candidate_summary}",
    task_type=TaskType.INTERVIEW,
    max_tokens=768,
    expected_output_schema=obj(
        opening_message=STR,
        first_question=STR,
        interview_context=STR,
    ),
)
