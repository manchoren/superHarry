"""Read-only validator must never send generation calls or disclose keys."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.validate_omniroute import OmnirouteValidator


@pytest.mark.parametrize("endpoint", [
    "http://remote.example:20128", "http://127.0.0.2:20128",
    "http://user:secret@127.0.0.1:20128", "http://127.0.0.1:20128/?key=secret",
    "http://127.0.0.1:20128/v1/chat/completions", "https://127.0.0.1:20128",
])
def test_rejects_untrusted_gateway_destination(endpoint):
    with pytest.raises(ValueError, match="gateway_endpoint_invalid"):
        OmnirouteValidator({"OMNIROUTE_ENDPOINT": endpoint, "OMNIROUTE_API_KEY": "secret-value"})


@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:20128", "http://localhost:20128/v1/",
                                      "http://[::1]:20128/v1"])
def test_read_only_probes_do_not_leak_key_or_follow_redirects(endpoint, capsys):
    key = "synthetic-secret-value"
    responses = [MagicMock(status_code=200), MagicMock(status_code=401), MagicMock(status_code=200)]
    session = MagicMock()
    session.get.side_effect = responses
    session.__enter__.return_value = session
    with patch("scripts.validate_omniroute.requests.Session", return_value=session):
        validator = OmnirouteValidator({"OMNIROUTE_ENDPOINT": endpoint, "OMNIROUTE_API_KEY": key})
        assert validator.run_all_tests()
        report = validator.generate_report()
    assert session.trust_env is False
    assert session.get.call_count == 3
    session.post.assert_not_called()
    if "localhost" in endpoint:
        assert all(call.args[0].startswith("http://127.0.0.1:20128/")
                   for call in session.get.call_args_list)
    assert all(call.kwargs["allow_redirects"] is False and call.kwargs["stream"] is True
               for call in session.get.call_args_list)
    assert [call.args[0].split("20128")[-1] for call in session.get.call_args_list] == [
        "/api/health", "/v1/models", "/v1/models"]
    assert session.get.call_args_list[0].kwargs["headers"] == {}
    assert session.get.call_args_list[1].kwargs["headers"] == {}
    assert session.get.call_args_list[2].kwargs["headers"] == {"Authorization": f"Bearer {key}"}
    assert key not in report + capsys.readouterr().out
    for response in responses:
        response.close.assert_called_once_with()


def test_failure_is_sanitized_and_redirect_is_not_accepted(capsys):
    secret = "synthetic-secret-value"
    session = MagicMock()
    session.__enter__.return_value = session
    session.get.side_effect = [requests.RequestException(secret), MagicMock(status_code=302),
                               requests.RequestException(secret)]
    with patch("scripts.validate_omniroute.requests.Session", return_value=session):
        validator = OmnirouteValidator({"OMNIROUTE_API_KEY": secret})
        assert not validator.run_all_tests()
        report = validator.generate_report()
    assert secret not in report + capsys.readouterr().out
    assert "request_failed" in report
    assert "models_unauthenticated: FAIL (302)" in report
    session.post.assert_not_called()
