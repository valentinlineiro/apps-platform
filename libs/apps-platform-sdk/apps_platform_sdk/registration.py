"""Registration module — deprecated.

App self-registration via heartbeat has been replaced by declarative catalog
seeding in portal's static_apps.json. Apps expose GET /manifest instead.
This stub is kept so that any remaining import sites fail gracefully.
"""
import warnings


class RegistrationService:
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "RegistrationService is deprecated. Add your app to static_apps.json instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def start(self):
        pass

    def stop(self):
        pass


def start_registration(manifest: dict) -> RegistrationService:
    warnings.warn(
        "start_registration() is deprecated. Add your app to static_apps.json instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return RegistrationService()
