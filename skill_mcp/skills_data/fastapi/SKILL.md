---
name: fastapi
description: >
  Build production-grade REST APIs with FastAPI and Python. Covers request/response models with
  Pydantic v2, path/query/body parameters, dependency injection, authentication (JWT, OAuth2),
  background tasks, async database access with SQLAlchemy 2.0, middleware, error handling, OpenAPI
  documentation, and testing with pytest and httpx. Use when building a Python REST API, adding
  endpoints to a FastAPI app, writing FastAPI middleware, or setting up FastAPI with a database.
license: Apache-2.0
metadata:
  author: community
  version: "1.0"
  tags: [fastapi, python, rest-api, pydantic, asyncio, sqlalchemy, jwt, backend]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - build a REST API with FastAPI
    - FastAPI endpoint
    - FastAPI Pydantic model
    - FastAPI authentication
    - FastAPI database
    - FastAPI dependency injection
    - FastAPI middleware
    - FastAPI testing
    - Python REST API
    - FastAPI JWT
    - async Python API
---

# FastAPI REST API Skill

## Step 1: Setup

```bash
pip install fastapi uvicorn[standard] pydantic[email] pydantic-settings
```

### Project Structure
```
app/
├── main.py              # App instance, lifespan, router includes
├── config.py            # Settings via pydantic-settings
├── dependencies.py      # Shared dependencies (DB session, auth)
├── routers/
│   ├── users.py
│   └── posts.py
├── models/
│   ├── user.py          # SQLAlchemy models
│   └── post.py
├── schemas/
│   ├── user.py          # Pydantic request/response schemas
│   └── post.py
└── services/
    ├── auth.py          # Auth business logic
    └── users.py         # User business logic
```

---

## Step 2: Application Setup with Lifespan

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from .models import Base
from .routers import users, posts

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: close connections
    await engine.dispose()

app = FastAPI(
    title="My API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],  # or ["*"] for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(posts.router, prefix="/posts", tags=["posts"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

---

## Step 3: Pydantic Schemas (Request / Response)

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM mode

    id: UUID
    name: str
    email: str
    created_at: datetime
    # Never include password in response
```

---

## Step 4: Router with CRUD Endpoints

```python
# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..dependencies import get_db, get_current_user
from ..schemas.user import UserCreate, UserUpdate, UserResponse
from ..services import users as user_service

router = APIRouter()

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await user_service.get_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return await user_service.create(db, data)

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    user = await user_service.update(db, user_id, data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await user_service.list_all(db, skip=skip, limit=limit)
```

---

## Step 5: Dependency Injection

```python
# app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .database import AsyncSessionLocal
from .services.auth import verify_token

# Database session dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Auth dependency
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    user = await verify_token(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

---

## Step 6: JWT Authentication

```python
# app/services/auth.py
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

async def verify_token(db, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
    except JWTError:
        return None
    return await get_user_by_id(db, user_id)
```

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

---

## Step 7: Async SQLAlchemy 2.0

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DATABASE_URL = os.environ["DATABASE_URL"]  # postgresql+asyncpg://...

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# app/models/user.py
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4
from datetime import datetime
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

---

## Step 8: Global Error Handling

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Validation failed"},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the full exception internally
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )
```

---

## Step 9: Testing with pytest + httpx

```python
# tests/test_users.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post("/users/", json={
        "name": "Alice Smith",
        "email": "alice@example.com",
        "password": "securepassword123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "password" not in data

@pytest.mark.asyncio
async def test_get_unknown_user_returns_404(client: AsyncClient):
    response = await client.get("/users/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
```

---

## Common Mistakes

- **Blocking the event loop** — use `async` for all I/O; use `run_in_executor` for CPU-bound work
- **Not using `response_model`** — always set `response_model` to prevent leaking sensitive fields
- **Mutable default arguments** — use `Field(default_factory=list)` not `= []` in Pydantic models
- **Missing 404 checks** — always verify resources exist before returning
- **Not committing or rolling back DB session** — handle this in the dependency (see `get_db` above)
- **Putting business logic in routes** — use service layer; routes should only validate and delegate
- **Hardcoding secrets** — use `pydantic-settings` with `.env` files
