"""EMBEDHUNT AI — Resume PDF renderer.

Regenerates a clean, ATS-friendly PDF from the primary resume's parsed
profile, so the document employers see always matches the profile the
matching engine uses — including curriculum-verified skills."""
from __future__ import annotations

from fpdf import FPDF

_INK = (13, 13, 26)
_MUTED = (85, 85, 119)
_BRAND = (76, 70, 182)
_LINE = (229, 229, 240)


def render_resume_pdf(profile: dict, *, full_name: str, email: str,
                      phone: str | None = None) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.set_margins(16, 14, 16)

    def heading(text: str) -> None:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(*_BRAND)
        pdf.cell(0, 6, text.upper(), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*_LINE)
        pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
        pdf.ln(2)

    def body(text: str, size: float = 9.5, muted: bool = False) -> None:
        pdf.set_x(pdf.l_margin)  # multi_cell needs the full line width
        pdf.set_font("Helvetica", "", size)
        pdf.set_text_color(*(_MUTED if muted else _INK))
        pdf.multi_cell(0, 4.6, text)

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*_INK)
    pdf.cell(0, 9, full_name, new_x="LMARGIN", new_y="NEXT")
    contact = " | ".join(x for x in (email, phone or "",
                                     profile.get("location", "")) if x)
    body(contact, muted=True)

    if profile.get("summary"):
        heading("Summary")
        body(str(profile["summary"]))

    skills = profile.get("all_skills") or []
    if skills:
        heading("Skills")
        body(" - " + "  -  ".join(str(s) for s in skills[:40]))

    experience = [e for e in (profile.get("experience") or []) if isinstance(e, dict)]
    if experience:
        heading("Experience")
    for exp in experience[:8]:
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_INK)
        title = f"{exp.get('role', '')} - {exp.get('company', '')}".strip(" -")
        pdf.cell(0, 5.4, title, new_x="LMARGIN", new_y="NEXT")
        if exp.get("duration"):
            body(str(exp["duration"]), size=8.5, muted=True)
        for h in (exp.get("highlights") or [])[:5]:
            body(f"  - {h}")
        pdf.ln(1)

    for edu in (profile.get("education") or [])[:3]:
        if isinstance(edu, dict):
            heading("Education")
            body(f"{edu.get('degree', '')} - {edu.get('institution', '')} "
                 f"{edu.get('year', '')}".strip())
            break

    out = pdf.output()
    return bytes(out)
