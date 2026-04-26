---
name: test-writer
description: Write unit tests, integration tests, and end-to-end tests following best practices. Covers pytest, Jest, Go testing, and JUnit. Generates tests for functions, classes, REST endpoints, and database operations. Use when the user wants to write tests, increase test coverage, practice TDD, or add a test suite to existing code.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [testing, pytest, jest, tdd, unit-tests, integration-tests, coverage]
  platforms: [claude-code, cursor, any]
  triggers:
    - write tests for this
    - add unit tests
    - test this function
    - TDD
    - increase test coverage
    - write pytest tests
    - write jest tests
    - create a test suite
    - integration test
    - test this endpoint
    - missing tests
---

# Test Writer Skill

## Overview
Generate comprehensive, maintainable test suites. Focuses on correctness, isolation, and readability — tests that catch real bugs and survive refactoring.

## Principles
1. **One assertion concept per test** — each test validates one specific behavior
2. **Descriptive names** — `test_<unit>_<scenario>_<expected>` format
3. **Isolation** — no shared mutable state between tests; mock external dependencies
4. **Determinism** — no flakiness from time, randomness, or network
5. **Coverage** — happy path + edge cases + error paths

## Step-by-Step Process

### Step 1: Analyse the Code Under Test
Identify:
- **Inputs**: parameters, types, valid ranges, optional vs required
- **Outputs**: return values, side effects (file writes, DB calls, HTTP requests)
- **Dependencies**: external systems to mock (DB, HTTP, clock, filesystem)
- **Behaviors**: branching logic, loops, error handling paths

### Step 2: Define Test Cases

For each function/method, write test cases for:
| Category | Examples |
|----------|----------|
| Happy path | Valid inputs → expected output |
| Boundary values | 0, -1, max int, empty string, empty list |
| None / null | Missing optional fields, None arguments |
| Type errors | Wrong types where applicable |
| Domain errors | Negative price, future birth date, invalid email |
| External failure | DB down, HTTP 500, file not found |

### Step 3: Python / pytest

```python
import pytest
from myapp.billing import calculate_discount

class TestCalculateDiscount:
    def test_gold_tier_applies_20_percent(self):
        assert calculate_discount(price=100.0, tier="gold") == 80.0

    def test_standard_tier_applies_no_discount(self):
        assert calculate_discount(price=100.0, tier="standard") == 100.0

    def test_zero_price_returns_zero(self):
        assert calculate_discount(price=0.0, tier="gold") == 0.0

    def test_negative_price_raises_value_error(self):
        with pytest.raises(ValueError, match="Price must be non-negative"):
            calculate_discount(price=-10.0, tier="gold")

    def test_unknown_tier_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            calculate_discount(price=100.0, tier="diamond")

    @pytest.mark.parametrize("tier,expected", [
        ("gold", 80.0),
        ("silver", 90.0),
        ("bronze", 95.0),
    ])
    def test_tier_discounts_parametrized(self, tier, expected):
        assert calculate_discount(price=100.0, tier=tier) == expected
```

**Mocking external dependencies**
```python
from unittest.mock import patch, MagicMock
import pytest

def test_send_invoice_calls_email_service():
    with patch("myapp.billing.email_client") as mock_email:
        mock_email.send.return_value = {"status": "sent"}
        result = send_invoice(user_id="u1", amount=50.0)
        mock_email.send.assert_called_once_with(
            to="user@example.com", subject="Your invoice", amount=50.0
        )
        assert result["status"] == "sent"
```

**Fixtures**
```python
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()

def test_create_user_persists_to_db(db_session):
    user = create_user(db_session, name="Alice", email="alice@example.com")
    fetched = db_session.get(User, user.id)
    assert fetched.name == "Alice"
```

### Step 4: JavaScript / Jest

```javascript
// billing.test.js
import { calculateDiscount } from './billing';

describe('calculateDiscount', () => {
  it('applies 20% for gold tier', () => {
    expect(calculateDiscount(100, 'gold')).toBe(80);
  });

  it('returns 0 for zero price', () => {
    expect(calculateDiscount(0, 'gold')).toBe(0);
  });

  it('throws for negative price', () => {
    expect(() => calculateDiscount(-10, 'gold')).toThrow('Price must be non-negative');
  });

  it.each([
    ['gold', 80],
    ['silver', 90],
    ['bronze', 95],
  ])('tier %s gets expected discount', (tier, expected) => {
    expect(calculateDiscount(100, tier)).toBe(expected);
  });
});
```

**Mocking in Jest**
```javascript
jest.mock('./emailClient');
import { emailClient } from './emailClient';

test('sendInvoice calls email client with correct args', async () => {
  emailClient.send.mockResolvedValue({ status: 'sent' });
  await sendInvoice('u1', 50);
  expect(emailClient.send).toHaveBeenCalledWith(
    expect.objectContaining({ amount: 50 })
  );
});
```

### Step 5: API / Endpoint Tests (pytest + httpx)

```python
import pytest
from httpx import AsyncClient
from myapp.server import app

@pytest.mark.asyncio
async def test_get_user_returns_200():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

@pytest.mark.asyncio
async def test_get_unknown_user_returns_404():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/users/99999")
    assert response.status_code == 404
```

## Coverage Checklist
- [ ] Happy path test exists for every public function
- [ ] `None` / empty inputs tested for functions that accept optional args
- [ ] All `if` branches exercised (aim for >80% branch coverage)
- [ ] Every exception type the code raises has a test
- [ ] All external dependencies (DB, HTTP, clock) are mocked
- [ ] No test depends on execution order or global state
