---
name: github-actions
description: >
  Write GitHub Actions CI/CD workflows — automated testing, linting, building, Docker image
  publishing, deployment, and release management. Covers workflow syntax, triggers, jobs, steps,
  matrix builds, caching dependencies, secrets management, environment protection rules, and
  reusable workflows. Use when setting up CI/CD pipelines, automating tests on pull requests,
  deploying applications, publishing packages, or configuring GitHub Actions workflows.
license: Apache-2.0
metadata:
  author: community
  version: "1.0"
  tags: [github-actions, ci-cd, automation, testing, deployment, devops, workflows]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - GitHub Actions workflow
    - set up CI/CD
    - automate tests
    - CI pipeline
    - deploy on push
    - GitHub Actions CI
    - build and test on PR
    - Docker publish GitHub Actions
    - release automation
    - continuous integration
    - continuous deployment
---

# GitHub Actions CI/CD Skill

## Workflow File Location

All workflows live in `.github/workflows/` as YAML files.

---

## Step 1: Core Syntax

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest  # or: ubuntu-22.04, windows-latest, macos-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run lint
        run: npm run lint

      - name: Run tests
        run: npm test -- --coverage
```

---

## Step 2: Language-Specific Setup

### Python
```yaml
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
        cache: 'pip'

    - name: Install dependencies
      run: pip install -r requirements.txt -r requirements-dev.txt

    - name: Lint with ruff
      run: ruff check .

    - name: Type check with mypy
      run: mypy .

    - name: Run tests
      run: pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        token: ${{ secrets.CODECOV_TOKEN }}
```

### Go
```yaml
    - name: Set up Go
      uses: actions/setup-go@v5
      with:
        go-version: '1.22'
        cache: true

    - name: Download dependencies
      run: go mod download

    - name: Run vet
      run: go vet ./...

    - name: Run tests
      run: go test -race -coverprofile=coverage.out ./...
```

---

## Step 3: Matrix Builds

Test across multiple versions simultaneously:
```yaml
jobs:
  test:
    strategy:
      fail-fast: false  # don't cancel others if one fails
      matrix:
        node-version: ['18', '20', '22']
        os: [ubuntu-latest, windows-latest]

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm ci
      - run: npm test
```

---

## Step 4: Dependency Caching

```yaml
# Node.js — built into setup-node
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'      # or 'yarn', 'pnpm'

# Python — built into setup-python
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'

# Manual cache for arbitrary files
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.cargo/registry
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

---

## Step 5: Secrets and Environment Variables

```yaml
jobs:
  deploy:
    environment: production  # uses GitHub Environment protection rules
    steps:
      - name: Deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          NODE_ENV: production
        run: ./scripts/deploy.sh
```

**Secret management rules:**
- Add secrets in: GitHub repo → Settings → Secrets and variables → Actions
- Use GitHub Environments for production secrets (adds approval gates)
- Never print secrets — GitHub redacts known secrets but be careful with transformed values

---

## Step 6: Build and Push Docker Image

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  docker:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}  # built-in, no setup needed

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha,prefix=,suffix=,format=short

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## Step 7: Full CI + CD Pipeline

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ─── CI: Test and Lint ──────────────────────────────────────────────────────
  ci:
    name: Test and Lint
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --coverage

  # ─── CD: Deploy to Staging ─────────────────────────────────────────────────
  deploy-staging:
    name: Deploy to Staging
    needs: ci
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging

    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        env:
          DEPLOY_KEY: ${{ secrets.STAGING_DEPLOY_KEY }}
        run: ./scripts/deploy.sh staging

  # ─── CD: Deploy to Production (manual approval required) ───────────────────
  deploy-production:
    name: Deploy to Production
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production  # has required reviewers configured
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        env:
          DEPLOY_KEY: ${{ secrets.PROD_DEPLOY_KEY }}
        run: ./scripts/deploy.sh production
```

---

## Step 8: Automated Releases

```yaml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # for changelog generation

      - name: Build
        run: npm ci && npm run build

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            dist/*.zip
            dist/*.tar.gz
```

---

## Step 9: Reusable Workflows

```yaml
# .github/workflows/reusable-test.yml
on:
  workflow_call:
    inputs:
      node-version:
        type: string
        default: '20'
    secrets:
      CODECOV_TOKEN:
        required: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci && npm test

# ─── Call from another workflow ───────────────────────────────────────────────
# .github/workflows/ci.yml
jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

---

## Common Mistakes

- **Using `pull_request_target` carelessly** — it has write permissions and can expose secrets to PRs from forks; use `pull_request` for untrusted code
- **Pinning actions to `@master`** — always pin to a version tag: `actions/checkout@v4`
- **Missing `permissions`** — explicitly declare minimum required permissions in the job
- **Not using `npm ci`** — use `npm ci` (not `npm install`) in CI for reproducible installs
- **Hardcoding secrets in workflow files** — always use `${{ secrets.NAME }}`
- **No `fail-fast: false` in matrix** — by default, one matrix failure cancels all; set `fail-fast: false` for visibility
- **Missing `if: github.ref == 'refs/heads/main'`** — deploy jobs must gate on branch
- **Not caching dependencies** — always set up caching to reduce build times by 50-80%
