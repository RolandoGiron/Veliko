"""Citas doradas para evaluar el lookup contra las APIs vivas. NO corre en CI."""

# (surname, year, expected_status) — reales famosas vs inventadas
GOLDEN_CITATIONS: list[tuple[str, int, str]] = [
    ("Bandura", 1977, "encontrada"),      # Self-efficacy
    ("Hattie", 2009, "encontrada"),       # Visible Learning
    ("Creswell", 2014, "encontrada"),     # Research Design
    ("Vygotsky", 1978, "encontrada"),     # Mind in Society
    ("Kuhn", 1962, "encontrada"),         # Structure of Scientific Revolutions
    ("Zzyzwiczak", 2019, "no_encontrada"),
    ("Quetzalfuegoz", 2021, "no_encontrada"),
    ("Brzemyslawski", 2015, "no_encontrada"),
]
