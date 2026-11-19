# github-actions-devsecops-pipeline

A pull request pipeline that checks a small Flask API for leaked secrets, insecure code, vulnerable dependencies, risky Dockerfile settings and a vulnerable container image before anything merges.

> Personal lab project on my own GitHub account. The company scenario below is fictional. This is not work I did for any employer or client. The app is a tiny demo API, not a production system.

## Scenario (fictional)

A small fintech startup ships one Flask API. The team wants every pull request checked for leaked secrets, vulnerable code and dependencies, and an unsafe container before merge, without trusting third party Actions they cannot verify.

## What the pipeline does

Five jobs run in parallel on every pull request and every push to main. Any red job blocks the merge.

| Job | Tool | What it checks |
|---|---|---|
| test | pytest | the app still works |
| secrets-scan | Gitleaks 8.30.1 | secrets anywhere in the git history |
| sast | Semgrep 1.186.0 | insecure code patterns (python and flask rule sets) |
| dockerfile-scan | Checkov 3.4.5 | Dockerfile best practice |
| vuln-scan | Trivy 0.76.1 | source, dependencies and config, then the built image (started and checked with a smoke test), plus an SBOM |

Image gate policy: any CRITICAL fails the build. A HIGH fails the build only when a fix exists. Findings with no fix yet are written to a report and do not block, because a pipeline that is red forever gets ignored.

## Design decisions

1. Every Action is pinned to a full commit SHA, not a tag. Only two third party Actions are used: checkout and upload-artifact.
2. Scanners run as binaries, not as marketplace Actions. Gitleaks and Trivy are downloaded and checked against a SHA 256 checksum written into the workflow. Semgrep and Checkov are installed from PyPI at pinned versions.
3. The workflow token is read only (contents: read) and checkouts do not persist credentials.
4. Every job has a timeout, superseded runs are cancelled, and the runner image is pinned to ubuntu-24.04.
5. The base image is pinned by digest for reproducible builds. Dependabot (with a 7 day cooldown) proposes updates for Actions, the Docker base image and Python packages.
6. The image runs as a non root user (uid 10001), has a HEALTHCHECK, has pip removed from the final image, and gets one targeted apt upgrade for a fixed zlib1g.

Why pin SHAs and avoid the scanner Actions: in March 2026 the Trivy project was hit by a supply chain compromise (advisory GHSA-69fq-xp46-6x23). A malicious release binary was published and tags of its GitHub Action were repointed. Pipelines that trusted a tag ran attacker code. This pipeline does not depend on a tag, and it verifies the binary checksum before running it.

## What the scans found (real findings, nothing planted)

Baseline on the source and dependencies was clean (evidence 01 to 04). The first scan of the container image on python:3.14-slim found:

1. 48 HIGH and 0 CRITICAL in the Debian layer, almost all with no fix available yet.
2. 5 HIGH in Python packages (msgpack, setuptools, urllib3). These were not my dependencies. They were copies bundled inside pip in the base image.

What I did: removed pip from the final image because the app does not need a package manager at runtime, and upgraded zlib1g, which had a fixed version. A newer base image digest did not help at the time, because the tag already pointed at the digest I had pinned.

Result: no HIGH or CRITICAL finding that has an available fix (evidence 06). The remaining findings with no fix are listed in evidence 07 and are accepted risk until Debian ships fixes.

## Proof the gates fail

A green pipeline proves little, so I opened a pull request on purpose with planted problems in ordinary looking files ([PR 1](https://github.com/antidotwale/github-actions-devsecops-pipeline/pull/1), closed and never merged). Logs are in evidence 08.

| Planted problem | Caught by |
|---|---|
| random fake secret in a settings file | Gitleaks (generic-api-key) |
| old requests 2.19.0 | Trivy (CVE-2018-18074, HIGH, fixed in 2.20.0) |
| Dockerfile with no USER line | Trivy (DS-0002) and Checkov (CKV_DOCKER_3) |
| shell=True subprocess call and MD5 | Semgrep (2 findings) |
| eval on a function argument | not caught |

Semgrep reported 2 findings for the 3 patterns I planted. I do not know why it missed eval. The lesson is that no single scanner catches everything, so layers and code review still matter.

A second lesson: after the PR, main went red. Gitleaks scans every branch it can see, so the planted secret on the demo branch failed the scan on main. Deleting the branch fixed it.

A third lesson: Dependabot opened a pull request bumping the base image to python 3.15-slim and it passed every gate, but my unit tests run on the GitHub runner's Python, not inside the image. So I added a smoke test that starts the container, calls /health and checks it runs as uid 10001. My first version failed on main with a connection reset. The most likely reason is that the port accepted the connection before gunicorn was listening, and curl does not retry a reset by default. I fixed the test with --retry-all-errors, not the app.

## What I would improve

1. Scan only the pull request commit range for secrets, and run the full history scan on a schedule.
2. Install Semgrep and Checkov from hash pinned requirements.
3. Sign the image and attach the SBOM (planned in supply-chain-sbom-signing).
4. Add dynamic testing (planned in dast-zap-baseline-pipeline) and SonarQube (planned in sonarqube-self-hosted-lab).
5. Give accepted risks an owner and an expiry date.
6. Run the unit tests inside the container image, so they use the same Python as production.

## Evidence

| File | What it shows |
|---|---|
| evidence/01 to 04 | baseline scans of source, dependencies and Dockerfile |
| evidence/05 | image scan before the fix |
| evidence/06 | image scan after the fix, fixable findings only |
| evidence/07 | remaining findings with no fix, accepted |
| evidence/08 | failed pipeline logs from the planted flaws PR |

## Run it locally

    docker build -t devsecops-demo:local .
    trivy image --severity HIGH,CRITICAL --ignore-unfixed devsecops-demo:local
