from unittest.mock import patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from cc.middleware import firebase_auth_required


def ok_view(request):
    return JsonResponse({"user": request.firebase_user})


def call(view, header=None, claims=None, verify_error=None):
    factory = RequestFactory()
    extra = {"HTTP_AUTHORIZATION": header} if header is not None else {}
    request = factory.get("/", **extra)
    with patch("cc.middleware.auth.verify_id_token") as verify:
        if verify_error:
            verify.side_effect = verify_error
        else:
            verify.return_value = claims or {}
        response = view(request)
    return response, verify


class FirebaseAuthRequiredTests(SimpleTestCase):
    @override_settings(DEBUG=True)
    def test_dev_token_in_debug_grants_owner_without_verifying(self):
        view = firebase_auth_required(min_role="owner")(ok_view)
        response, verify = call(view, "Bearer dev")
        self.assertEqual(response.status_code, 200)
        verify.assert_not_called()
        self.assertIn(b'"role": "owner"', response.content)

    @override_settings(DEBUG=False)
    def test_dev_token_outside_debug_is_verified_like_any_token(self):
        view = firebase_auth_required(ok_view)
        response, verify = call(view, "Bearer dev", verify_error=ValueError("bad"))
        self.assertEqual(response.status_code, 401)
        verify.assert_called_once_with("dev")

    def test_missing_header_is_401(self):
        view = firebase_auth_required(ok_view)
        response, verify = call(view)
        self.assertEqual(response.status_code, 401)
        verify.assert_not_called()

    def test_non_bearer_header_is_401(self):
        view = firebase_auth_required(ok_view)
        response, _ = call(view, "Basic abc")
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_is_401(self):
        view = firebase_auth_required(ok_view)
        response, _ = call(view, "Bearer x", verify_error=Exception("expired"))
        self.assertEqual(response.status_code, 401)

    def test_bare_decorator_requires_base_role(self):
        view = firebase_auth_required(ok_view)
        response, _ = call(view, "Bearer x", claims={"uid": "u"})
        self.assertEqual(response.status_code, 200)

    def test_role_claim_is_compared_against_min_role(self):
        cases = [
            ("base", "admin", 403),
            ("admin", "admin", 200),
            ("admin", "owner", 403),
            ("owner", "owner", 200),
            ("owner", "base", 200),
            ("none", "base", 403),
        ]
        for role, min_role, expected in cases:
            with self.subTest(role=role, min_role=min_role):
                view = firebase_auth_required(min_role=min_role)(ok_view)
                response, _ = call(view, "Bearer x", claims={"role": role})
                self.assertEqual(response.status_code, expected)

    def test_unknown_role_is_treated_as_base(self):
        base_view = firebase_auth_required(min_role="base")(ok_view)
        admin_view = firebase_auth_required(min_role="admin")(ok_view)
        claims = {"role": "superuser"}
        self.assertEqual(call(base_view, "Bearer x", claims=claims)[0].status_code, 200)
        self.assertEqual(call(admin_view, "Bearer x", claims=claims)[0].status_code, 403)

    def test_numeric_privilege_level_maps_to_role(self):
        view = firebase_auth_required(min_role="admin")(ok_view)
        cases = [(0, 403), (1, 403), (2, 200), (3, 200), (9, 403)]
        for level, expected in cases:
            with self.subTest(level=level):
                response, _ = call(view, "Bearer x", claims={"privilege_level": level})
                self.assertEqual(response.status_code, expected)

    def test_non_int_privilege_level_is_ignored(self):
        view = firebase_auth_required(min_role="admin")(ok_view)
        response, _ = call(view, "Bearer x", claims={"privilege_level": "3"})
        self.assertEqual(response.status_code, 403)

    @override_settings(FIREBASE_OWNER_UIDS=["boss"])
    def test_owner_uid_setting_grants_owner(self):
        view = firebase_auth_required(min_role="owner")(ok_view)
        self.assertEqual(
            call(view, "Bearer x", claims={"uid": "boss"})[0].status_code, 200
        )
        self.assertEqual(
            call(view, "Bearer x", claims={"uid": "other"})[0].status_code, 403
        )

    def test_decoded_token_is_attached_to_request(self):
        view = firebase_auth_required(ok_view)
        response, _ = call(view, "Bearer x", claims={"uid": "abc", "role": "base"})
        self.assertIn(b'"uid": "abc"', response.content)

    def test_wraps_preserves_view_name(self):
        self.assertEqual(firebase_auth_required(ok_view).__name__, "ok_view")
