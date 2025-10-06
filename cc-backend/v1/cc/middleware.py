import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from django.http import JsonResponse
from functools import wraps

# Initialize Firebase Admin SDK
try:
    # Use the service account credentials from settings
    cred = credentials.Certificate(settings.FIREBASE_ADMIN_CREDENTIAL)
    firebase_admin.initialize_app(cred)
except (ValueError, Exception):
    # Handle cases where the app is already initialized or credentials are invalid
    # This might happen in development when server reloads
    pass


def firebase_auth_required(view_func=None, min_role="base"):
    """
    Decorator (works both with @firebase_auth_required and @firebase_auth_required(min_role="admin"))
    min_role: one of "base" (logged in), "admin", "owner"
    """
    ROLE_LEVELS = {"none": 0, "base": 1, "admin": 2, "owner": 3}

    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth_header.startswith("Bearer "):
                return JsonResponse(
                    {"error": "Authentication credentials were not provided."},
                    status=401,
                )

            id_token = auth_header.split(" ", 1)[1]
            try:
                decoded = auth.verify_id_token(id_token)
            except Exception:
                return JsonResponse({"error": "Invalid auth token"}, status=401)

            # attach decoded token to request for downstream use
            request.firebase_user = decoded

            # Determine role: prefer explicit custom claim "role" (string) or "privilege_level" (int)
            role = decoded.get("role")
            if not role:
                # fallback to numeric claim if present
                priv_level = decoded.get("privilege_level")
                if isinstance(priv_level, int):
                    # map numeric to roles (0..3)
                    inv_map = {v: k for k, v in ROLE_LEVELS.items()}
                    role = inv_map.get(priv_level, "base")
                else:
                    # owner override via settings list of UIDs (comma-separated in env)
                    owners = getattr(settings, "FIREBASE_OWNER_UIDS", [])
                    if decoded.get("uid") and decoded.get("uid") in owners:
                        role = "owner"
                    else:
                        # authenticated with no explicit role -> treat as base
                        role = "base"

            if ROLE_LEVELS.get(role, 1) < ROLE_LEVELS.get(min_role, 1):
                return JsonResponse(
                    {"error": "Forbidden - insufficient privileges"}, status=403
                )

            return func(request, *args, **kwargs)

        return _wrapped

    # support both @firebase_auth_required and @firebase_auth_required(min_role="admin")
    if view_func:
        return decorator(view_func)
    return decorator
