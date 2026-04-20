import re


class SqlJournalQuartileGateway:
    def __init__(self, db_factory):
        self._db = db_factory

    def obtener_cuartil(self, issn_input: str | None) -> str:
        if not issn_input:
            return "Sin Q"

        issn_clean = re.sub(r"[^a-zA-Z0-9]", "", str(issn_input)).strip()
        if not issn_clean:
            return "Sin Q"

        try:
            with self._db() as conn:
                # Exact match on either ISSN column
                row = conn.execute(
                    "SELECT quartile FROM aneca_journal_index WHERE issn_1 = ? OR issn_2 = ? LIMIT 1",
                    (issn_clean, issn_clean),
                ).fetchone()
                if row:
                    return row["quartile"]

                # Fuzzy fallback
                row = conn.execute(
                    "SELECT quartile FROM aneca_journal_index WHERE issn_1 LIKE ? LIMIT 1",
                    (f"%{issn_clean}%",),
                ).fetchone()
                return row["quartile"] if row else "Sin Q"
        except Exception:
            return "Sin Q"
