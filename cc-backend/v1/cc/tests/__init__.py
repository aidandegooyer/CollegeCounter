import requests.adapters


def _network_disabled(self, request, *args, **kwargs):
    raise RuntimeError(
        f"Tests must not make real HTTP requests (tried {request.method} {request.url}). "
        "Mock requests.get/requests.post where the code under test calls it."
    )


# Block real HTTP from any test, so a missed mock fails loudly instead of
# calling Faceit/LeagueSpot/Discord/etc. with whatever keys are in the env.
requests.adapters.HTTPAdapter.send = _network_disabled
