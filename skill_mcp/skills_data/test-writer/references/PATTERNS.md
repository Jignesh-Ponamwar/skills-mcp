# Testing Patterns Reference

Core patterns for writing reliable, maintainable tests: fixtures, mocking, parametrization, async testing, and common pitfalls.

---

## Naming Convention

Test names should be self-documenting:

```
test_<unit_under_test>_<scenario>_<expected_outcome>
```

Examples:
- `test_calculate_discount_gold_tier_returns_20_percent`
- `test_send_email_smtp_unavailable_raises_service_error`
- `test_parse_date_empty_string_returns_none`

---

## pytest Fixtures

### Function-scoped fixture (default — fresh per test)
```python
import pytest

@pytest.fixture
def sample_user():
    return {"id": "u1", "name": "Alice", "email": "alice@example.com", "tier": "gold"}

def test_apply_discount_gold_user(sample_user):
    result = apply_discount(sample_user, amount=100.0)
    assert result == 80.0
```

### Session-scoped fixture (expensive setup — reused across all tests)
```python
@pytest.fixture(scope="session")
def embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")  # load once per test run
```

### Database fixtures
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session  # session is rolled back automatically
    Base.metadata.drop_all(engine)
```

### Parametrized fixtures
```python
@pytest.fixture(params=["postgresql", "sqlite"])
def db_dialect(request):
    return request.param

def test_query_works_on_all_dialects(db_dialect):
    result = run_query(dialect=db_dialect)
    assert result is not None
```

### Fixture factories
```python
@pytest.fixture
def make_order():
    """Factory fixture — returns a callable to create orders with custom attrs."""
    def _make(status="pending", total=100.0, **kwargs):
        return Order(status=status, total=total, **kwargs)
    return _make

def test_refund_pending_order(make_order):
    order = make_order(status="pending", total=50.0)
    result = process_refund(order)
    assert result.status == "refunded"
```

---

## Mocking

### patch as decorator
```python
from unittest.mock import patch, MagicMock

@patch("myapp.email.smtp_client")
def test_send_invoice_calls_smtp(mock_smtp):
    mock_smtp.send.return_value = {"message_id": "abc123"}
    
    result = send_invoice(user_id="u1", amount=50.0)
    
    mock_smtp.send.assert_called_once()
    call_args = mock_smtp.send.call_args
    assert call_args.kwargs["to"] == "u1@example.com"
    assert result["message_id"] == "abc123"
```

### patch as context manager
```python
def test_get_weather_api_failure():
    with patch("myapp.weather.httpx.get") as mock_get:
        mock_get.side_effect = httpx.ConnectTimeout("timeout")
        
        with pytest.raises(WeatherServiceUnavailable):
            get_weather("London")
```

### Mocking return values for different calls
```python
mock_db.execute.side_effect = [
    MagicMock(fetchone=lambda: {"id": 1}),   # first call returns a row
    MagicMock(fetchone=lambda: None),          # second call returns nothing
]
```

### Asserting mock calls
```python
# Called once
mock_fn.assert_called_once()

# Called with specific arguments
mock_fn.assert_called_with("arg1", key="value")

# Called N times
assert mock_fn.call_count == 3

# Check all calls in order
mock_fn.assert_has_calls([
    call("first"),
    call("second"),
])

# Never called
mock_fn.assert_not_called()
```

---

## Parametrize

### Basic parametrize
```python
@pytest.mark.parametrize("tier,expected", [
    ("gold", 80.0),
    ("silver", 90.0),
    ("bronze", 95.0),
    ("standard", 100.0),
])
def test_discount_by_tier(tier, expected):
    assert calculate_discount(price=100.0, tier=tier) == expected
```

### Parametrize with ids (readable test names)
```python
@pytest.mark.parametrize("email,is_valid", [
    ("alice@example.com", True),
    ("not-an-email", False),
    ("@missing-local.com", False),
    ("missing-at-sign.com", False),
    ("a@b.c", True),
], ids=[
    "valid-standard",
    "no-at-sign",
    "no-local-part",
    "no-domain-dot",
    "short-but-valid",
])
def test_email_validation(email, is_valid):
    assert validate_email(email) == is_valid
```

### Nested parametrize
```python
@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP"])
@pytest.mark.parametrize("amount", [0, 1, 100, 999999])
def test_format_currency(amount, currency):
    result = format_currency(amount, currency)
    assert isinstance(result, str)
    assert len(result) > 0
```

---

## Async Testing

```python
import pytest

@pytest.mark.asyncio
async def test_async_fetch_user():
    result = await fetch_user("u1")
    assert result["name"] == "Alice"

@pytest.mark.asyncio
async def test_concurrent_requests():
    import asyncio
    results = await asyncio.gather(
        fetch_user("u1"),
        fetch_user("u2"),
    )
    assert len(results) == 2
```

Configure in `pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

---

## Testing Exceptions

```python
# Assert exception type
with pytest.raises(ValueError):
    parse_date("not-a-date")

# Assert exception message
with pytest.raises(ValueError, match="Invalid date format"):
    parse_date("not-a-date")

# Assert exception attributes
with pytest.raises(HTTPError) as exc_info:
    client.get("/missing-endpoint")
assert exc_info.value.status_code == 404
```

---

## Common Pitfalls

| Pitfall | Why it's bad | Fix |
|---------|-------------|-----|
| Tests share mutable state | Test order dependence → flaky | Use fixtures with function scope |
| `time.sleep()` in tests | Slow and flaky | Mock `time.sleep` or use `freezegun` |
| Asserting on dict without `.get()` | KeyError hides the real failure | Use `assert data.get("key") == value` |
| Mocking too broadly (`patch("os")`) | Hides real behavior | Mock at the boundary, not the stdlib |
| No assertion at all | Test always passes | Always assert something |
| Asserting `== True` for booleans | Accepts truthy values | Use `is True` for strict boolean check |
| Testing implementation details | Breaks on refactor | Test behavior through public API |
