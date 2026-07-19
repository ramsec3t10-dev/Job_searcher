"""Learning roadmap prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import INT, STR, PromptTemplate, arr, obj

ROADMAP_GENERATOR = PromptTemplate(
    system_prompt=(
        "Role: learning architect for the candidate's field. Build a week-by-week roadmap "
        "that closes the candidate's gaps toward the target role, respecting available "
        "hours and learning velocity. Each week targets one skill/topic with concrete "
        "activities, a checkpoint to prove mastery and a projected readiness score (0-100). "
        "Output ONLY valid JSON:\n"
        '{"weeks":[{"number":int,"skill":str,"topic":str,"hours":int,"activities":[str],'
        '"checkpoint":str,"projected_score":int}],'
        '"total_weeks":int,"career_path":str,"summary":str}'
    ),
    user_template=(
        "Target role: {target_role}\nHours per week: {hours_per_week}\n"
        "Learning velocity: {learning_velocity}\n\nCareer twin:\n{career_twin}\n\n"
        "Interview history:\n{interview_history}"
    ),
    task_type=TaskType.ROADMAP,
    max_tokens=2560,
    expected_output_schema=obj(
        weeks=arr(
            obj(
                number=INT,
                skill=STR,
                topic=STR,
                hours=INT,
                activities=arr(STR),
                checkpoint=STR,
                projected_score=INT,
            )
        ),
        total_weeks=INT,
        career_path=STR,
        summary=STR,
    ),
)

WEEK_PLANNER = PromptTemplate(
    # Haiku task: routed via SUMMARIZATION which maps to the Haiku tier.
    system_prompt=(
        "Role: daily study planner. Break one week of learning a skill topic into daily "
        "tasks. Each day has a focused topic, duration in minutes, one named resource with "
        "a URL and a concrete exercise. Output ONLY valid JSON:\n"
        '{"days":[{"day":int,"skill":str,"topic":str,"duration_minutes":int,'
        '"resource_title":str,"resource_url":str,"exercise":str}]}'
    ),
    user_template="Skill: {skill}\nTopic: {topic}\nTotal hours: {hours}\nLevel: {level}",
    task_type=TaskType.SUMMARIZATION,
    max_tokens=1024,
    expected_output_schema=obj(
        days=arr(
            obj(
                day=INT,
                skill=STR,
                topic=STR,
                duration_minutes=INT,
                resource_title=STR,
                resource_url=STR,
                exercise=STR,
            )
        )
    ),
)
