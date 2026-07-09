"""Embedded coding prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import INT, STR, PromptTemplate, arr, obj

CODE_REVIEWER = PromptTemplate(
    system_prompt=(
        "Role: senior embedded C/C++ reviewer. Review the code for correctness, safety and "
        "standards. overall_score is 0-100. Report MISRA violations with rule id, line and "
        "description. Flag memory issues (leaks, overflow, aliasing), concurrency issues "
        "(races, ISR/reentrancy) and style issues. Be precise and cite lines. "
        "Output ONLY valid JSON:\n"
        '{"overall_score":int,"misra_violations":[{"rule":str,"line":int,"description":str}],'
        '"memory_issues":[str],"concurrency_issues":[str],"style_issues":[str],'
        '"positive_aspects":[str],"improvement_suggestions":[str]}'
    ),
    user_template="Language: {language}\nContext: {context}\n\nCode:\n{code}",
    task_type=TaskType.CODING,
    max_tokens=2048,
    expected_output_schema=obj(
        overall_score=INT,
        misra_violations=arr(obj(rule=STR, line=INT, description=STR)),
        memory_issues=arr(STR),
        concurrency_issues=arr(STR),
        style_issues=arr(STR),
        positive_aspects=arr(STR),
        improvement_suggestions=arr(STR),
    ),
)

CHALLENGE_GENERATOR = PromptTemplate(
    system_prompt=(
        "Role: embedded coding challenge author. Create a self-contained challenge for the "
        "skill at the given difficulty. Provide compilable starter_code, deterministic "
        "test_cases (input and expected), progressive hints and a correct reference_solution. "
        "difficulty is easy, medium or hard. Output ONLY valid JSON:\n"
        '{"title":str,"description":str,"starter_code":str,'
        '"test_cases":[{"input":str,"expected":str}],"hints":[str],'
        '"reference_solution":str,"skills_tested":[str],"difficulty":str}'
    ),
    user_template="Skill: {skill}\nDifficulty: {difficulty}\nFocus: {focus}",
    task_type=TaskType.CODING,
    max_tokens=2048,
    expected_output_schema=obj(
        title=STR,
        description=STR,
        starter_code=STR,
        test_cases=arr(obj(input=STR, expected=STR)),
        hints=arr(STR),
        reference_solution=STR,
        skills_tested=arr(STR),
        difficulty=STR,
    ),
)
