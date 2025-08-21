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


def firebase_auth_required(view_func):
    """
    Decorator for views that checks if the user has a valid Firebase token.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        # Check if Authorization header is present and in correct format
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"error": "Unauthorized: No valid authentication credentials found"},
                status=401,
            )

        # Extract the token
        token = auth_header.split("Bearer ")[1]

        try:
            # Verify the token with Firebase
            decoded_token = auth.verify_id_token(token)

            # Add the user info to the request for use in views
            request.firebase_user = decoded_token

            # Continue with the view
            return view_func(request, *args, **kwargs)

        except auth.InvalidIdTokenError:
            return JsonResponse({"error": "Unauthorized: Invalid token"}, status=401)
        except Exception as e:
            return JsonResponse({"error": f"Unauthorized: {str(e)}"}, status=401)

    return wrapped_view
