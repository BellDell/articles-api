# articles-api

A tiny, beginner-friendly Flask API for articles and authors.

Quick start
-----------

1. Run tests locally

- Install dev dependencies:

  python -m pip install --upgrade pip
  python -m pip install -r requirements-dev.txt

- Run the test suite:

  pytest -q

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

Notes
-----
- This project uses an in-memory DATA structure (no database).
- The container exposes port 5000 internally; use -p to map it to any host port (examples use 5002).

