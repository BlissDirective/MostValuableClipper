# GitHub Actions Workflow Guide

## Overview

This document describes the CI/CD pipeline for **MostValuableClipper** and how to manage, extend, and troubleshoot GitHub Actions workflows.

---

## Current Workflows

### 1. `ci.yml` — Continuous Integration & Deployment

**Location:** `.github/workflows/ci.yml`

**Triggers:**
| Event | Branches | Action |
|-------|----------|--------|
| `push` | `main`, `develop` | Run tests |
| `pull_request` | `main` | Run tests |

**Jobs:**

#### Job 1: `test`
- **Runner:** `ubuntu-latest`
- **Services:** Redis 7 (Alpine) on port 6379
- **Steps:**
  1. Checkout code
  2. Setup Python 3.11
  3. Install backend dependencies (`requirements.txt`)
  4. Lint with `flake8` (max line length: 120)
  5. Run `pytest` suite

#### Job 2: `deploy` (depends on `test`)
- **Runner:** `ubuntu-latest`
- **Condition:** Only on `main` branch
- **Steps:**
  1. Checkout code
  2. Setup Fly.io CLI (`flyctl`)
  3. Deploy to Fly.io (`flyctl deploy --remote-only`)

---

## Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions → Repository secrets** and add:

| Secret | Value | Where It Lives |
|--------|-------|----------------|
| `SUPABASE_URL` | `https://xbftsjerxodfwyqycmjl.supabase.co` | env.var |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbGciOiJIUzI1NiIs...` | env.var |
| `UPSTASH_REDIS_REST_URL` | `https://trusting-walleye-123237.upstash.io` | env.var |
| `UPSTASH_REDIS_REST_TOKEN` | `gQAAAAAAAeFlAAIgcDIy...` | env.var |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | `2b259349da0083baaee5670...` | env.var |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | `344994e22626d029b4207e2...` | env.var |
| `CLOUDFLARE_R2_API_TOKEN` | `cfat_KC3sY9xr6BwZ7S1O...` | env.var |
| `CLOUDFLARE_ACCOUNT_ID` | `2bb32a965806f844959920...` | env.var |
| `CLOUDFLARE_R2_BUCKET` | `mvc-clips` | env.var |
| `STRIPE_SECRET_KEY` | `sk_test_51TWneCPWFs4pr...` | env.var |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Set after webhook configured |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_51TWneCPWFs4pr...` | env.var |
| `FLY_API_TOKEN` | `FlyV1_fm2_lJPECAAAAA...` | env.var (FLY_ORG_TOKEN) |
| `ANTHROPIC_API_KEY` | `sk-ant-api03-pXcWHS5f...` | env.var (Claude LLM) |
| `GITHUB_TOKEN` | `ghp_Nd41EnP9VYJgX454...` | env.var |
| `APP_SECRET` | Any strong random string | Generate new |

> **Note:** The `GITHUB_TOKEN` secret in the table above is for backend API calls to GitHub (releases, issues). GitHub Actions automatically provides a *different* `GITHUB_TOKEN` for workflow operations — do not confuse the two.

---

## How to Add a New Workflow

1. Create a new file in `.github/workflows/<name>.yml`
2. Follow the YAML structure below:

```yaml
name: Workflow Name

on:
  push:
    branches: [main]
  # or: schedule, workflow_dispatch, release, etc.

jobs:
  job-name:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Step description
        run: echo "Your command here"
```

3. Commit and push — GitHub will auto-detect it

---

## Common Workflow Patterns

### Manual Trigger (Workflow Dispatch)
```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
```

### Scheduled Job (Cron)
```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
```

### Matrix Build (Multiple Python/Node versions)
```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

---

## Useful GitHub Actions References

| Action | Purpose |
|--------|---------|
| `actions/checkout@v4` | Clone repo |
| `actions/setup-python@v5` | Install Python |
| `actions/setup-node@v4` | Install Node.js |
| `superfly/flyctl-actions/setup-flyctl@master` | Install Fly CLI |
| `docker/login-action@v3` | Docker Hub login |
| `slackapi/slack-github-action@v1` | Slack notifications |

---

## Troubleshooting

### Workflow not running?
- Check branch filters in `on.push.branches`
- Check if file is in `.github/workflows/` (not `.github/workflow/`)

### Secrets not available?
- Secrets are NOT passed to forks
- Ensure secret name matches exactly (case-sensitive)

### Fly.io deploy fails?
- Verify `FLY_API_TOKEN` is valid: `flyctl tokens list`
- Check `backend/fly.toml` app name matches token scope

---

## Recommended Future Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `frontend-build.yml` | PR to `main` | Build Expo / React Native bundle |
| `release.yml` | GitHub Release created | Auto-tag Docker image, update changelog |
| `security-scan.yml` | Weekly cron | Run `pip-audit`, `npm audit` |
| `e2e-test.yml` | Nightly | Run Playwright/Cypress against staging |

---

## Quick Commands

```bash
# View workflow status
github.com/BlissDirective/MostValuableClipper/actions

# Trigger workflow manually (if workflow_dispatch configured)
gh workflow run ci.yml

# View recent runs
gh run list --limit 10

# Watch live logs
gh run watch
```

---

*Last updated: 2026-05-16*
