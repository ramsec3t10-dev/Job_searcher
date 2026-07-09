"""Resume domain prompts."""
from app.llm.model_selector import TaskType
from app.llm.prompts.base import INT, NUM, STR, PromptTemplate, arr, obj

RESUME_PARSER = PromptTemplate(
    system_prompt=(
        "Role: resume parser for embedded/firmware engineering candidates. "
        "Extract only data present in the text; infer nothing. Normalise skill "
        "names to lowercase. Output ONLY valid JSON, no prose, exactly this shape:\n"
        '{"skills":[str],'
        '"experience":[{"company":str,"title":str,"years":number,"highlights":[str]}],'
        '"education":[{"degree":str,"institution":str,"year":int}],'
        '"projects":[{"name":str,"description":str}],'
        '"certifications":[str],'
        '"contact":{"name":str,"email":str,"phone":str},'
        '"summary":str,"total_years":number}'
    ),
    user_template="Resume text:\n{resume_text}",
    task_type=TaskType.EXTRACTION,
    max_tokens=1536,
    expected_output_schema=obj(
        skills=arr(STR),
        experience=arr(obj(company=STR, title=STR, years=NUM, highlights=arr(STR))),
        education=arr(obj(degree=STR, institution=STR, year=INT)),
        projects=arr(obj(name=STR, description=STR)),
        certifications=arr(STR),
        contact=obj(name=STR, email=STR, phone=STR),
        summary=STR,
        total_years=NUM,
    ),
)

RESUME_SCORER = PromptTemplate(
    system_prompt=(
        "Role: ATS and technical resume reviewer for embedded engineering roles. "
        "Score the resume against the job description. score and ats_score are 0-100. "
        "missing_keywords are job keywords absent from the resume. weak_bullets quote "
        "resume lines that are vague or lack metrics. Output ONLY valid JSON:\n"
        '{"score":int,"ats_score":int,"missing_keywords":[str],'
        '"weak_bullets":[str],"strengths":[str],"improvements":[str]}'
    ),
    user_template="Job description:\n{job_description}\n\nResume:\n{resume_text}",
    task_type=TaskType.MATCHING,
    max_tokens=1024,
    expected_output_schema=obj(
        score=INT,
        ats_score=INT,
        missing_keywords=arr(STR),
        weak_bullets=arr(STR),
        strengths=arr(STR),
        improvements=arr(STR),
    ),
)

RESUME_REWRITER = PromptTemplate(
    system_prompt=(
        "Role: resume writer for embedded engineers. Rewrite bullets tailored to the "
        "target job: action verbs, quantified impact, job keywords woven in naturally. "
        "Never fabricate experience. estimated_score_improvement is 0-100 delta. "
        "Output ONLY valid JSON:\n"
        '{"rewritten_bullets":[str],"summary":str,"keywords_added":[str],'
        '"estimated_score_improvement":int}'
    ),
    user_template="Target job:\n{job_description}\n\nCurrent resume:\n{resume_text}",
    task_type=TaskType.PLANNING,
    max_tokens=1536,
    expected_output_schema=obj(
        rewritten_bullets=arr(STR),
        summary=STR,
        keywords_added=arr(STR),
        estimated_score_improvement=INT,
    ),
)
