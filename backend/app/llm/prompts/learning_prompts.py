"""Learning content prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import STR, PromptTemplate, arr, obj

LESSON_GENERATOR = PromptTemplate(
    system_prompt=(
        "Role: embedded systems instructor. Teach one skill topic at the given level with "
        "a clear explanation, key concepts, a practical example and a short runnable code "
        "snippet (C/C++ unless the topic implies otherwise). Add a 3-question quiz; each "
        "quiz item has options, the correct answer and a one-line explanation. "
        "Output ONLY valid JSON:\n"
        '{"topic":str,"explanation":str,"key_concepts":[str],"practical_example":str,'
        '"code_snippet":str,"quiz":[{"question":str,"options":[str],"answer":str,'
        '"explanation":str}]}'
    ),
    user_template="Skill: {skill}\nTopic: {topic}\nLevel: {level}",
    task_type=TaskType.ROADMAP,
    max_tokens=2048,
    expected_output_schema=obj(
        topic=STR,
        explanation=STR,
        key_concepts=arr(STR),
        practical_example=STR,
        code_snippet=STR,
        quiz=arr(obj(question=STR, options=arr(STR), answer=STR, explanation=STR)),
    ),
)

FLASHCARD_GENERATOR = PromptTemplate(
    # Haiku task: routed via EXTRACTION which maps to the Haiku tier.
    system_prompt=(
        "Role: spaced-repetition flashcard generator for embedded engineering. Create "
        "atomic cards: front is a question or term, back is a concise answer. difficulty "
        "is easy, medium or hard. tags label the sub-skill. Output ONLY valid JSON:\n"
        '{"cards":[{"front":str,"back":str,"difficulty":str,"tags":[str]}]}'
    ),
    user_template="Skill: {skill}\nTopic: {topic}\nCard count: {count}",
    task_type=TaskType.EXTRACTION,
    max_tokens=1024,
    expected_output_schema=obj(
        cards=arr(obj(front=STR, back=STR, difficulty=STR, tags=arr(STR)))
    ),
)
