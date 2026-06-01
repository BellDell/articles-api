# articles-api

A tiny, beginner-friendly Flask API for articles and authors.

Quick start
-----------

1. Run tests locally

- Install dev dependencies:

  python -m pip install --upgrade pip
  python -m pip install -r requirements-dev.txt

- Run the test suite:

  python -m pytest -q

2. Build and run with Docker (locally)

- Build the image:

  docker build -t articles-api:local .

- Run the container mapping port 5002 on the host to port 5000 in the container:

  docker run -p 5002:5000 articles-api:local

- The API will be available at: http://localhost:5002/

3. CI/CD (GitHub Actions)

- The repository includes a CI workflow (.github/workflows/ci-cd.yml) that:
  - Runs tests on push and pull requests
  - Builds a container and performs a simple health check
  - On pushes to master it logs in to GitHub Container Registry (GHCR) and pushes images

4. Published GHCR image

- The workflow is configured to publish images to: ghcr.io/belldell/articles-api

5. Docker Agent Review (manual run)

- There's a separate workflow (.github/workflows/agent-review.yml) you can run manually from the Actions tab named "Docker Agent Review".
- It uses a local agent definition (agent-review.yml) and requires an OpenAI API key to run.

6. Required GitHub secret

- Set the following repository secret for the Agent Review workflow to run:

  OPENAI_API_KEY

## Docker Agent workflow

Available agent configs and when to use them.

| Config | Model(s) | Use when | Avoid when |
|---|---|---|---|
| `agent.yaml` | DeepSeek | Small daily coding tasks: app.py, tests, small HTML/UI edits, small endpoint changes | Architecture-heavy tasks, broad review, or complex multi-step work |
| `agent-plan-review.yml` | GPT | Reviewing `PLAN.md` before implementation; finding critical/major gaps | You need code edits or test execution |
| `agent-ux-architect.yml` | Claude | UX, frontend wording, API contract, product flow, architecture review | Simple code changes or cheap daily iteration |
| `agent-multi.yml` | GPT + DeepSeek + Claude | Rare complex tasks that need coding + testing + architecture review in one run | Small edits, cost-sensitive work, or tasks that one agent can handle |

Default choice: use `agent.yaml`. Use the other configs only when their specific role is needed.

### 1. `agent.yaml`

- Single-agent DeepSeek coding mode.
- Use for daily small coding tasks.
- Good for app.py, tests, small HTML/UI edits, small endpoint changes.
- Cheapest/default mode.
- Avoid broad analysis.
- Usually run tests manually after the change.

**Example prompt:**

```
Improve the Broken Clock Calculator result wording. Edit only app/app.py. Do not run tests. Stop after summarizing the change.
```

### 2. `agent-plan-review.yml`

- GPT read-only plan reviewer.
- Use for reviewing PLAN.md before implementation.
- Must not edit files.
- Must not write code or pseudocode.
- Should report critical/major/minor/nit issues.
- Use when a feature is complex enough to need planning.

**Example prompt:**

```
Review PLAN.md for the multi-article-delete feature.
Check for missing edge cases, security gaps, and API contract consistency.
```

### 3. `agent-ux-architect.yml`

- Claude read-only UX/API/architecture reviewer.
- Use for frontend UX, wording, API contract, product flow, architecture concerns.
- Must not edit files by default.
- Good before larger UI changes or when the user flow is unclear.

**Example prompt:**

```
Review the proposed endpoint /api/articles/batch.
Is the request/response shape clear? Are there naming issues or UX concerns?
```

### 4. `agent-multi.yml`

- Multi-agent mode with GPT coordinator, DeepSeek coder, GPT tester, Claude architect.
- Use rarely.
- Use only when one task genuinely needs coding + testing + architecture review in one run.
- More expensive and slower because sub-agents create extra sessions/context.
- Do not use for simple edits.

**Example prompt:**

```
Add a paginated /api/articles endpoint with cursor-based pagination.
Coordinator: break the work into plan, code, tests, and architecture review.
```

### Cost-control notes

- Avoid sub-agents for small tasks.
- Prefer single DeepSeek session when possible.
- Use cross-model review through separate sessions instead of always using multi-agent.
- Manual GitHub Docker Agent Review should stay workflow_dispatch only.

### Example commands

```
export DEEPSEEK_API_KEY=...
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...

docker-agent run agent.yaml
docker-agent run agent-plan-review.yml
docker-agent run agent-ux-architect.yml
docker-agent run agent-multi.yml
```

Notes
-----
- This project uses an in-memory DATA structure (no database).
- The container exposes port 5000 internally; use -p to map it to any host port (examples use 5002).

