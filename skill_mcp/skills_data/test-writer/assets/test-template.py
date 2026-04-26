"""
Standard test file template — bundled with the test-writer skill.

Copy this file and replace {placeholders} with your actual module and function names.
Run with: pytest test_{module}.py -v

Demonstrates: fixtures, parametrize, mocking, async, and exception testing.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ── Module under test ─────────────────────────────────────────────────────────
# Replace with your actual import
# from myapp.{module} import {FunctionOrClass}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_user() -> dict:
    """A minimal valid user object for testing."""
    return {
        "id": "user-001",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "tier": "gold",
        "active": True,
    }


@pytest.fixture
def sample_order(sample_user: dict) -> dict:
    """A minimal valid order object for testing."""
    return {
        "id": "order-001",
        "user_id": sample_user["id"],
        "total": 100.0,
        "currency": "USD",
        "status": "pending",
        "items": [
            {"product_id": "p1", "quantity": 2, "price": 25.0},
            {"product_id": "p2", "quantity": 1, "price": 50.0},
        ],
    }


@pytest.fixture
def mock_db():
    """A mock database session for testing database interactions."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


@pytest.fixture
def mock_email_client():
    """A mock email client that records sent messages."""
    with patch("myapp.notifications.email_client") as mock:
        mock.send.return_value = {"message_id": "msg-abc123", "status": "sent"}
        yield mock


# ── Happy path tests ──────────────────────────────────────────────────────────

class TestCalculateDiscount:
    """Tests for the calculate_discount(price, tier) function."""

    def test_gold_tier_applies_20_percent(self, sample_user: dict) -> None:
        # result = calculate_discount(price=100.0, tier=sample_user["tier"])
        # assert result == 80.0
        pass  # Replace with actual assertion

    def test_standard_tier_has_no_discount(self) -> None:
        # result = calculate_discount(price=100.0, tier="standard")
        # assert result == 100.0
        pass

    def test_zero_price_returns_zero(self) -> None:
        # result = calculate_discount(price=0.0, tier="gold")
        # assert result == 0.0
        pass

    @pytest.mark.parametrize("tier,expected", [
        ("gold", 80.0),
        ("silver", 90.0),
        ("bronze", 95.0),
        ("standard", 100.0),
    ])
    def test_all_tier_discounts(self, tier: str, expected: float) -> None:
        # result = calculate_discount(price=100.0, tier=tier)
        # assert result == expected
        pass


# ── Edge case tests ───────────────────────────────────────────────────────────

class TestCalculateDiscountEdgeCases:

    def test_negative_price_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Price must be non-negative"):
            pass  # calculate_discount(price=-10.0, tier="gold")

    def test_unknown_tier_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown tier"):
            pass  # calculate_discount(price=100.0, tier="platinum")

    def test_none_tier_raises_type_error(self) -> None:
        with pytest.raises((TypeError, ValueError)):
            pass  # calculate_discount(price=100.0, tier=None)

    def test_very_large_price_does_not_overflow(self) -> None:
        # result = calculate_discount(price=999_999_999.99, tier="gold")
        # assert result > 0
        # assert isinstance(result, float)
        pass


# ── External dependency tests (mocked) ───────────────────────────────────────

class TestSendInvoice:
    """Tests for send_invoice — mocks the email client."""

    def test_invoice_sent_for_completed_order(
        self, sample_order: dict, mock_email_client: MagicMock
    ) -> None:
        sample_order["status"] = "completed"
        # result = send_invoice(order=sample_order)
        # mock_email_client.send.assert_called_once()
        # call_kwargs = mock_email_client.send.call_args.kwargs
        # assert call_kwargs["to"] == "alice@example.com"
        # assert "invoice" in call_kwargs["subject"].lower()
        pass

    def test_invoice_not_sent_for_pending_order(
        self, sample_order: dict, mock_email_client: MagicMock
    ) -> None:
        sample_order["status"] = "pending"
        # send_invoice(order=sample_order)
        # mock_email_client.send.assert_not_called()
        pass

    def test_email_failure_raises_notification_error(
        self, sample_order: dict, mock_email_client: MagicMock
    ) -> None:
        mock_email_client.send.side_effect = ConnectionError("SMTP unavailable")
        sample_order["status"] = "completed"
        # with pytest.raises(NotificationError):
        #     send_invoice(order=sample_order)
        pass


# ── Database tests ────────────────────────────────────────────────────────────

class TestGetUserById:
    """Tests for get_user_by_id — uses mock DB session."""

    def test_returns_user_when_found(self, mock_db: MagicMock, sample_user: dict) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        # result = get_user_by_id(db=mock_db, user_id="user-001")
        # assert result["name"] == "Alice Johnson"
        pass

    def test_returns_none_when_not_found(self, mock_db: MagicMock) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None
        # result = get_user_by_id(db=mock_db, user_id="nonexistent-id")
        # assert result is None
        pass


# ── Async tests ───────────────────────────────────────────────────────────────

class TestAsyncFetchUser:

    @pytest.mark.asyncio
    async def test_fetch_returns_user_dict(self) -> None:
        # result = await fetch_user_async("user-001")
        # assert isinstance(result, dict)
        # assert "id" in result
        pass

    @pytest.mark.asyncio
    async def test_fetch_raises_on_not_found(self) -> None:
        # with pytest.raises(UserNotFoundError):
        #     await fetch_user_async("nonexistent")
        pass
