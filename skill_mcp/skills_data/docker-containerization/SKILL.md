---
name: docker-containerization
description: >
  Containerize applications with Docker and orchestrate with Docker Compose. Covers writing
  production-ready Dockerfiles for Python, Node.js, and Go applications, multi-stage builds,
  security hardening (non-root users, minimal base images), Docker Compose for local development and
  multi-service stacks, health checks, volumes, networking, and optimization for layer caching. Use
  when containerizing an app, writing a Dockerfile, setting up Docker Compose, or debugging container
  issues.
license: Apache-2.0
metadata:
  author: community
  version: "1.0"
  tags: [docker, containers, dockerfile, docker-compose, devops, kubernetes, deployment]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - containerize this app
    - write a Dockerfile
    - Docker Compose
    - Docker multi-stage build
    - run app in Docker
    - Docker best practices
    - set up containers
    - Docker networking
    - Docker volumes
    - build a Docker image
    - deploy with Docker
---

# Docker Containerization Skill

## Step 1: Choose the Right Base Image

| Use Case | Base Image |
|----------|-----------|
| Python production | `python:3.12-slim` |
| Node.js production | `node:20-alpine` |
| Go production (final stage) | `gcr.io/distroless/static` |
| Debugging / dev | `python:3.12` or `node:20` |
| Minimal static binary | `scratch` |

**Rules:**
- Never use `latest` tag — pin exact versions for reproducibility
- Prefer `-slim` or `-alpine` over full images to reduce attack surface and size
- Use `distroless` or `scratch` for final stages of statically compiled languages

---

## Step 2: Production Dockerfiles

### Python Application
```dockerfile
# ─── Build Stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies separately for layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Final Stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user (security hardening)
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Copy application code
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Node.js Application
```dockerfile
# ─── Dependencies Stage ───────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# ─── Build Stage (if TypeScript/Next.js) ─────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ─── Final Stage ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

# Non-root user
RUN addgroup --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Production dependencies only
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000
ENV NODE_ENV=production PORT=3000

CMD ["node", "server.js"]
```

### Go Application
```dockerfile
# ─── Build Stage ─────────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Module download (separate layer for caching)
COPY go.mod go.sum ./
RUN go mod download

# Build (static binary, no CGO)
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo \
    -ldflags="-w -s" -o server ./cmd/server

# ─── Final Stage (distroless — no shell, minimal attack surface) ──────────────
FROM gcr.io/distroless/static:nonroot

WORKDIR /

COPY --from=builder /app/server /server

USER nonroot:nonroot

EXPOSE 8080

ENTRYPOINT ["/server"]
```

---

## Step 3: .dockerignore

Always create `.dockerignore` to prevent bloating the build context:
```
.git
.gitignore
node_modules
.next
__pycache__
*.pyc
.env
.env.*
*.log
.DS_Store
dist/
build/
coverage/
*.test.ts
*.spec.ts
README.md
docker-compose*.yml
```

---

## Step 4: Docker Compose for Local Development

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      target: builder  # use build stage for dev (includes dev deps)
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:password@db:5432/myapp
      - REDIS_URL=redis://cache:6379
    volumes:
      - .:/app                    # hot reload
      - /app/node_modules         # exclude node_modules from bind mount
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    ports:
      - "5432:5432"

  cache:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Override for Production
```yaml
# docker-compose.prod.yml
services:
  app:
    build:
      target: runner  # production stage
    environment:
      - NODE_ENV=production
    volumes: []  # no bind mounts in production
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
```

Run with: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

---

## Step 5: Essential Docker Commands

```bash
# Build
docker build -t myapp:1.0 .
docker build --target builder -t myapp:dev .        # specific stage
docker build --no-cache -t myapp:latest .           # force fresh build

# Run
docker run -p 3000:3000 --env-file .env myapp:1.0
docker run -d --name myapp -p 3000:3000 myapp:1.0  # detached

# Docker Compose
docker compose up -d          # start all services
docker compose up --build     # rebuild and start
docker compose logs -f app    # follow logs
docker compose exec app sh    # shell into running container
docker compose down -v        # stop and remove volumes

# Inspect / Debug
docker ps -a                  # list all containers
docker logs myapp             # view container logs
docker exec -it myapp sh      # interactive shell
docker inspect myapp          # full container metadata

# Cleanup
docker system prune -af       # remove all unused images and containers
docker volume prune           # remove unused volumes
```

---

## Step 6: Security Hardening

```dockerfile
# 1. Non-root user (mandatory)
USER appuser

# 2. Read-only filesystem
# docker run --read-only --tmpfs /tmp myapp

# 3. Drop capabilities
# docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myapp

# 4. No new privileges
# docker run --security-opt no-new-privileges myapp

# 5. Scan for vulnerabilities
# docker scout cves myapp:latest
# trivy image myapp:latest
```

---

## Layer Caching Optimization

Order Dockerfile instructions from **least frequently changing** to **most frequently changing**:

```dockerfile
# ✅ Optimal order
COPY package*.json ./     # changes infrequently → cache hit most of the time
RUN npm ci                # only re-runs when package.json changes
COPY . .                  # app code changes most often — put last
RUN npm run build

# ❌ Wrong order — kills caching
COPY . .                  # app code changes → invalidates all subsequent layers
RUN npm ci                # runs npm install on every code change!
```

---

## Common Mistakes

- **Using `latest` tags** — pin exact versions: `node:20.12.0-alpine`
- **Running as root** — always create and switch to a non-root user
- **Copying everything into the image** — always have a comprehensive `.dockerignore`
- **Installing dev dependencies in production** — use `--only=production` or multi-stage builds
- **Secrets in Dockerfile** — never `ARG API_KEY` or `ENV SECRET=` in Dockerfile; use Docker secrets or runtime env vars
- **Fat final images** — use multi-stage builds; copy only the compiled artifact
- **Missing health checks** — define `HEALTHCHECK` so orchestrators know when to restart
