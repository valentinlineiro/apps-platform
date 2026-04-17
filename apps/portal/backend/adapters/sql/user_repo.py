import json
from domain.user import UserProfile, Preferences, TenantPreferences


class SqlUserRepository:
    """SQL-backed implementation of UserRepository.

    Accepts a db_factory callable (returns a context-manager connection)
    so it can be used with either the SQLite or Postgres backends without
    knowing which one is active.
    """

    def __init__(self, db_factory):
        self._db = db_factory

    # ── Profile ──────────────────────────────────────────────────────────────

    def get_profile(self, user_id: str) -> UserProfile:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return UserProfile()
        return UserProfile(
            avatar_url=row["avatar_url"],
            bio=row["bio"],
            display_name=row["display_name"],
            show_activity=bool(row["show_activity"]),
            show_email=bool(row["show_email"]),
        )

    def save_profile(self, user_id: str, profile: UserProfile) -> UserProfile:
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles
                  (user_id, avatar_url, bio, display_name, show_activity, show_email)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  avatar_url    = excluded.avatar_url,
                  bio           = excluded.bio,
                  display_name  = excluded.display_name,
                  show_activity = excluded.show_activity,
                  show_email    = excluded.show_email
                """,
                (
                    user_id,
                    profile.avatar_url,
                    profile.bio,
                    profile.display_name,
                    1 if profile.show_activity else 0,
                    1 if profile.show_email else 0,
                ),
            )
        return self.get_profile(user_id)

    # ── Preferences ──────────────────────────────────────────────────────────

    def get_preferences(self, user_id: str) -> Preferences:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return Preferences()
        return Preferences(
            theme=row["theme"],
            language=row["language"],
            timezone=row["timezone"],
            reduced_motion=bool(row["reduced_motion"]),
            font_scale=row["font_scale"],
            notification_email=bool(row["notification_email"]),
            notification_digest=row["notification_digest"],
        )

    def save_preferences(self, user_id: str, prefs: Preferences) -> Preferences:
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences
                  (user_id, theme, language, timezone, reduced_motion, font_scale,
                   notification_email, notification_digest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  theme               = excluded.theme,
                  language            = excluded.language,
                  timezone            = excluded.timezone,
                  reduced_motion      = excluded.reduced_motion,
                  font_scale          = excluded.font_scale,
                  notification_email  = excluded.notification_email,
                  notification_digest = excluded.notification_digest
                """,
                (
                    user_id,
                    prefs.theme,
                    prefs.language,
                    prefs.timezone,
                    1 if prefs.reduced_motion else 0,
                    prefs.font_scale,
                    1 if prefs.notification_email else 0,
                    prefs.notification_digest,
                ),
            )
        return self.get_preferences(user_id)

    # ── Tenant preferences ───────────────────────────────────────────────────

    def get_primary_tenant_id(self, user_id: str) -> str | None:
        with self._db() as conn:
            row = conn.execute(
                """
                SELECT tenant_id FROM tenant_memberships
                WHERE user_id = ?
                ORDER BY tenant_id
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        return row["tenant_id"] if row else None

    def get_tenant_preferences(self, user_id: str, tenant_id: str) -> TenantPreferences:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM user_tenant_preferences WHERE user_id = ? AND tenant_id = ?",
                (user_id, tenant_id),
            ).fetchone()
        if not row:
            return TenantPreferences()
        return TenantPreferences(
            default_home_app=row["default_home_app"],
            notify_app_ids=json.loads(row["notify_app_ids"] or "[]"),
        )

    def save_tenant_preferences(
        self, user_id: str, tenant_id: str, prefs: TenantPreferences
    ) -> TenantPreferences:
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO user_tenant_preferences
                  (user_id, tenant_id, default_home_app, notify_app_ids)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, tenant_id) DO UPDATE SET
                  default_home_app = excluded.default_home_app,
                  notify_app_ids   = excluded.notify_app_ids
                """,
                (user_id, tenant_id, prefs.default_home_app, json.dumps(prefs.notify_app_ids)),
            )
        return self.get_tenant_preferences(user_id, tenant_id)
