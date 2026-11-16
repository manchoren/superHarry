from datetime import datetime, timedelta, timezone

import pytest

from home.guest_graphical_display import GuestDisplayError, GuestGraphicalDisplay


BASE = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def test_requires_explicit_enable_and_binds_exact_guest_session():
    display = GuestGraphicalDisplay()
    with pytest.raises(GuestDisplayError):
        display.enable("guest-1", explicit_enable=False, now=BASE)

    binding, secret = display.enable("guest-1", explicit_enable=True, now=BASE)
    assert display.bind("guest-1", secret, now=BASE) == binding
    assert binding.capabilities == ()
    assert binding.authority == ()


def test_wrong_session_or_secret_fails_closed():
    display = GuestGraphicalDisplay()
    _, secret = display.enable("guest-1", explicit_enable=True, now=BASE)
    with pytest.raises(GuestDisplayError):
        display.bind("guest-2", secret, now=BASE)
    with pytest.raises(GuestDisplayError):
        display.bind("guest-1", "wrong", now=BASE)


def test_only_one_active_binding_per_guest_session():
    display = GuestGraphicalDisplay()
    display.enable("guest-1", explicit_enable=True, now=BASE)
    with pytest.raises(GuestDisplayError):
        display.enable("guest-1", explicit_enable=True, now=BASE)


def test_expiry_and_revoke_remove_binding():
    display = GuestGraphicalDisplay(ttl=timedelta(minutes=5))
    _, secret = display.enable("guest-1", explicit_enable=True, now=BASE)
    with pytest.raises(GuestDisplayError):
        display.bind("guest-1", secret, now=BASE + timedelta(minutes=5))

    _, secret = display.enable("guest-1", explicit_enable=True, now=BASE + timedelta(minutes=6))
    display.revoke("guest-1", now=BASE + timedelta(minutes=6))
    with pytest.raises(GuestDisplayError):
        display.bind("guest-1", secret, now=BASE + timedelta(minutes=6))


def test_naive_time_and_invalid_session_are_rejected():
    display = GuestGraphicalDisplay()
    with pytest.raises(GuestDisplayError):
        display.enable("guest 1", explicit_enable=True, now=BASE)
    with pytest.raises(GuestDisplayError):
        display.enable("guest-1", explicit_enable=True, now=datetime(2026, 11, 15, 12, 0))
