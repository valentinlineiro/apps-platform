import json
import time


class SqlArticleRepository:
    def __init__(self, db_factory):
        self._db = db_factory

    def get_articles(self, user_id: str) -> list[dict]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT article_json FROM aneca_articles WHERE user_id = ? ORDER BY created_at",
                (user_id,),
            ).fetchall()
        return [json.loads(row["article_json"]) for row in rows]

    def save_articles(self, user_id: str, articles: list[dict]) -> None:
        now = time.time()
        with self._db() as conn:
            conn.execute("DELETE FROM aneca_articles WHERE user_id = ?", (user_id,))
            conn.executemany(
                "INSERT INTO aneca_articles (user_id, article_json, created_at) VALUES (?, ?, ?)",
                [(user_id, json.dumps(art), now) for art in articles],
            )
