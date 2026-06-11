import re
from dataclasses import dataclass
from datetime import date

from app.verification.extraction import Citation


@dataclass(frozen=True)
class ApaIssue:
    severity: str  # critica | mayor | menor
    code: str
    message: str
    citation_raw: str | None = None


def run_apa_checks(citations: list[Citation], today: date) -> list[ApaIssue]:
    if not citations:
        return [ApaIssue(
            "menor", "sin_citas",
            "El proyecto no contiene ninguna cita en-texto APA (Autor, año).",
        )]

    issues: list[ApaIssue] = []
    for c in citations:
        if c.missing_comma:
            issues.append(ApaIssue(
                "mayor", "falta_coma",
                f"Falta la coma antes del año en {c.raw}; APA: (Autor, año).",
                c.raw,
            ))
        if c.narrative and "&" in c.raw:
            issues.append(ApaIssue(
                "menor", "ampersand_en_narrativa",
                f"En citas narrativas se escribe 'y' en vez de '&': {c.raw}.",
                c.raw,
            ))
        if not c.narrative and re.search(r"\by\b", c.raw):
            issues.append(ApaIssue(
                "menor", "y_en_parentetica",
                f"Dentro de paréntesis APA usa '&' en vez de 'y': {c.raw}.",
                c.raw,
            ))
        if len(c.surnames) >= 3:
            issues.append(ApaIssue(
                "mayor", "demasiados_autores",
                f"Con 3+ autores cita solo el primero seguido de 'et al.': {c.raw}.",
                c.raw,
            ))
        if c.year[:4].isdigit() and int(c.year[:4]) > today.year + 1:
            issues.append(ApaIssue(
                "mayor", "anio_futuro",
                f"El año de {c.raw} está en el futuro; verifica la fecha.",
                c.raw,
            ))
    return issues
