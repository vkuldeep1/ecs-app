# ECS Fargate + Docker Hub + GitHub Actions (Learning Project)

This repository documents an **end‑to‑end container deployment** using **Amazon ECS (Fargate)**, **Docker Hub**, and **GitHub Actions CI/CD**.

The goal of this project is **learning by building**, not production optimization. Every component is explained from a *systems perspective* so you understand **what exists, why it exists, and how data flows**.

---

## 1. Big Picture (One‑Minute Overview)

**What you built:**

> A system where GitHub builds a Docker image, ECS runs it as a managed service, and an Application Load Balancer routes traffic to it — without managing servers.

High‑level flow:

```
GitHub commit
   ↓
Docker image built (CI)
   ↓
Image pushed to Docker Hub
   ↓
ECS task definition references image
   ↓
ECS service runs the task (Fargate)
   ↓
ALB routes HTTP traffic to the task
```

No EC2 instances. No SSH. No manual restarts.

---

## 2. Core Concepts (What Each Thing Actually Is)

### 2.1 Application

* Simple web app (Flask / FastAPI style)
* Listens on **port 8000**
* Completely unaware of AWS

AWS never touches your code directly. It only runs containers.

---

### 2.2 Docker Image (Unit of Deployment)

* Your app + runtime + dependencies
* Built once per Git commit
* Stored in Docker Hub

Image naming strategy:

```
vkuldeep1/myapp:<commit-sha>
```

**Why commit SHA as tag?**

* Immutable (never overwritten)
* Perfect traceability
* Easy rollback

If the image **does not exist**, ECS cannot run anything. Image existence is non‑negotiable.

---

### 2.3 Task Definition (How to Run the Image)

Think of a task definition as a **saved `docker run` command**.

It answers:

* Which image to run
* CPU and memory
* Which port the container listens on
* Logging configuration

Important rules:

* Task definitions **do not run containers**
* They are pure configuration
* Each change creates a new *revision*

---

### 2.4 ECS Service (Keep It Running)

The service answers:

> “How many copies of this task should always be running?”

Responsibilities:

* Starts tasks
* Restarts failed tasks
* Performs rolling deployments
* Registers tasks with the load balancer

Key setting:

```
Desired count = N
```

* `N = 1` → one container runs (costs money)
* `N = 0` → nothing runs (no cost)

---

### 2.5 Fargate (Serverless Compute)

Fargate provides:

* CPU + memory on demand
* No EC2 instances
* No capacity planning

You pay **only while tasks are running**.

---

### 2.6 Application Load Balancer (Traffic Entry Point)

ALB provides:

* Stable DNS name
* HTTP routing
* Health checks

Traffic path:

```
User → ALB → ECS Task → App
```

Important clarifications:

* ALB never starts containers
* ALB never pulls images
* ALB only forwards traffic to *healthy* targets

---

### 2.7 Security Groups (Explicit Network Permissions)

Security groups are **allowlists**.

Final trust chain:

```
Internet
   ↓
ALB Security Group (port 80 open)
   ↓
ECS Task Security Group (port 8000 only from ALB SG)
   ↓
Container
```

Rules:

* Default SG is never modified
* ALB SG allows public traffic
* Task SG only trusts ALB SG

---

## 3. CI/CD Explained Simply

CI/CD is **automation**, not magic.

### 3.1 CI (Continuous Integration)

Purpose:

> “Can this code be turned into a Docker image?”

Steps:

1. Checkout code
2. Build Docker image
3. Tag with commit SHA
4. Push to Docker Hub

CI produces an **artifact** (the image).

---

### 3.2 CD (Continuous Deployment)

Purpose:

> “Should ECS start running this image?”

Steps:

1. Read current task definition
2. Create new revision with new image tag
3. Update ECS service
4. ECS performs rolling deployment

Deployment is **manual** (`workflow_dispatch`) to avoid surprise costs.

---

### 3.3 Why Rollbacks Worked Automatically

If a new task revision fails (bad image, wrong port):

* ECS detects failure
* New deployment is marked unhealthy
* ECS switches back to last healthy revision

This behavior is built into ECS services.

---

## 4. Common Failure Modes (What You Actually Hit)

### 4.1 Wrong Image Name

Task definition used:

```
your-dockerhub-username/your-app
```

But real image was:

```
vkuldeep1/myapp
```

ECS is literal. One character mismatch = pull failure.

---

### 4.2 Missing Image Tag

Public repository ≠ tag exists.

If ECS requests:

```
vkuldeep1/myapp:<sha>
```

That exact tag **must exist** in Docker Hub.

---

### 4.3 Port Mismatch

* App listened on `8000`
* Task definition exposed `80`

ALB sent traffic to the wrong port → guaranteed failure.

Rule:

> Container port must equal app listen port.

---

### 4.4 ALB Not Attached to Service

Creating an ALB does **nothing** by itself.

Only when:

* ECS service is explicitly attached
* Container name + port match

will targets be registered.

---

## 5. Cost Control Rules (Learning‑Safe Defaults)

| Component               | Cost Behavior      |
| ----------------------- | ------------------ |
| ECS Cluster             | Free               |
| Task Definition         | Free               |
| IAM                     | Free               |
| ECS Service (desired=0) | Free               |
| Running Task            | Charged per second |
| ALB                     | Charged per hour   |
| CloudWatch Logs         | Charged per GB     |

Golden rule:

> **Create freely. Run briefly. Delete aggressively.**

End of session cleanup:

* Set service desired count = 0
* Delete ALB

---

## 6. Mental Models to Keep

### Model 1 — Responsibilities

| Component       | Responsibility     |
| --------------- | ------------------ |
| Docker Hub      | Store images       |
| Task Definition | Describe container |
| ECS Service     | Run containers     |
| ALB             | Route traffic      |
| CI/CD           | Move images        |

---

### Model 2 — Deployment Truth

> ECS never deploys code. It runs images.

---

### Model 3 — Debug Order

If something breaks, check in this order:

1. Image exists?
2. Image name correct?
3. Container port correct?
4. Service attached to ALB?
5. Security groups chained correctly?

---

## 7. Final State Achieved

You now have:

* Immutable image deployments
* Serverless container runtime
* Health‑checked service
* Automatic rollback
* Controlled CI/CD

This is the **core ECS Fargate pattern** used in real systems.

---

## 8. Next Possible Extensions

* HTTPS with ACM
* Auto scaling (CPU‑based)
* OIDC auth for GitHub Actions
* Infrastructure as Code (Terraform / CDK)
* Full teardown & rebuild drill

---

## 9. One Sentence Summary

> **GitHub builds images, ECS runs them, ALB routes traffic — nothing else is magic.**

# Phase 1 — Application & Containerization (Foundation)

This phase establishes the **entire foundation** of the system. Every later AWS component (ECS, ALB, CI/CD) assumes that this phase is correct. If Phase 1 is wrong, nothing else can work.

---

## 1. Purpose of Phase 1

The goal of Phase 1 is simple:

> Turn application code into a **portable, deterministic unit** that can run anywhere without modification.

This unit is the **Docker image**.

AWS never runs your Python code directly. It only runs containers. Therefore, container correctness is non‑negotiable.

---

## 2. Application Overview (`app.py`)

### 2.1 Full Source Code

```python
import os
import sys
from flask import Flask, jsonify

# ---- REQUIRED ENV VARIABLES ----
REQUIRED_VARS = ["APP_NAME", "ENVIRONMENT", "SECRET_KEY"]

missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
if missing:
    print(f"Missing required environment variables: {missing}", file=sys.stderr)
    sys.exit(1)

APP_NAME = os.getenv("APP_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")

app = Flask(__name__)

@app.route("/")
def home():
    return f"{APP_NAME} running in {ENVIRONMENT}
"

@app.route("/health")
def health():
    return jsonify(status="ok")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False
    )
```

---

## 3. Application Design Decisions (Why This Code Looks Like This)

### 3.1 Mandatory Environment Variables

```python
REQUIRED_VARS = ["APP_NAME", "ENVIRONMENT", "SECRET_KEY"]
```

The application **refuses to start** if required environment variables are missing.

Why this matters:

* Failing fast is better than running misconfigured
* Configuration is externalized (12‑factor principle)
* ECS failures become **visible immediately**

This behavior later helped surface misconfiguration early during task startup.

---

### 3.2 Explicit Crash on Misconfiguration

```python
sys.exit(1)
```

This is intentional.

In containerized systems:

* Silent misconfiguration is dangerous
* Crash → restart → observable failure
* ECS services rely on crashes to detect bad deployments

This enables **automatic rollback** later.

---

### 3.3 Network Binding (`0.0.0.0`)

```python
app.run(host="0.0.0.0", port=8000)
```

This line is **critical**.

Why:

* `127.0.0.1` would bind only inside the container
* ECS and ALB communicate via the container network interface
* Binding to `0.0.0.0` exposes the app to the container network

If this were wrong, ALB health checks would fail even if the app was running.

---

### 3.4 Port Choice (8000)

The application listens on **port 8000**.

This choice is arbitrary but must be **consistent everywhere**:

* App runtime
* Dockerfile
* ECS task definition
* ALB target group

A later failure occurred when ECS was configured for port 80 while the app listened on 8000.

---

### 3.5 Health Endpoint

```python
@app.route("/health")
def health():
    return jsonify(status="ok")
```

This endpoint exists **only for infrastructure**, not users.

Purpose:

* ALB health checks
* ECS task health validation
* Zero‑downtime deployments

Without this, ECS would rely on process‑level health only.

---

## 4. Dependencies (`requirements.txt`)

### 4.1 Full File

```text
flask==3.0.0
```

### 4.2 Why This Is Minimal

* Fewer dependencies = smaller image
* Smaller image = faster pull time
* Faster pull = faster task startup

In container platforms, **image size directly affects reliability**.

---

## 5. Dockerfile (Container Definition)

### 5.1 Full Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

CMD ["python", "app.py"]
```

---

## 6. Dockerfile Explained Line by Line

### 6.1 Base Image

```dockerfile
FROM python:3.11-slim
```

* Official Python image
* Slim variant reduces attack surface
* OS dependencies kept minimal

---

### 6.2 Working Directory

```dockerfile
WORKDIR /app
```

Sets a deterministic execution context.

Avoids:

* Hard‑coded absolute paths
* Inconsistent file locations

---

### 6.3 Dependency Installation Layer

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

This layer is intentionally separated.

Why:

* Docker layer caching
* Dependencies only reinstall when `requirements.txt` changes
* Faster rebuilds during CI

---

### 6.4 Application Code Layer

```dockerfile
COPY app.py .
```

Keeps application changes isolated from dependency changes.

---

### 6.5 Port Declaration

```dockerfile
EXPOSE 8000
```

This is **documentation**, not enforcement.

It signals:

* Which port the container expects traffic on
* What ECS and ALB should be configured to use

Mismatch here later caused ECS‑ALB failures.

---

### 6.6 Container Startup Command

```dockerfile
CMD ["python", "app.py"]
```

Defines the container process.

Important implications:

* If this process exits → container is unhealthy
* ECS uses this exit signal to detect failures

---

## 7. Local Container Build & Test (Pre‑AWS Validation)

Before any AWS usage, the container was validated locally.

Typical commands:

```bash
docker build -t myapp:local .
docker run -p 8000:8000 \
  -e APP_NAME=myapp \
  -e ENVIRONMENT=local \
  -e SECRET_KEY=dummy \
  myapp:local
```

Verification:

* App reachable on `http://localhost:8000`
* Missing env vars → container exits

This step isolates:

* Application bugs
* Dependency issues
* Container misconfiguration

AWS was not involved yet.

---

## 8. Why Phase 1 Is the Most Important Phase

Every later failure traced back to assumptions made here:

* Wrong port → ALB 503
* Wrong image → ECS pull failure
* Missing env vars → task crash

ECS, ALB, and CI/CD are **multipliers**. They amplify correctness or amplify mistakes.

Phase 1 determines which one happens.

---

## 9. Phase 1 Outcomes

At the end of Phase 1:

* Application runs deterministically
* Configuration is externalized
* Container exposes correct port
* Image can run locally and in cloud

This container becomes the **single source of truth** for all later phases.

---

## 10. Transition to Phase 2

With a validated container:

> The next problem becomes **distribution** — making the image available to ECS.

That is addressed in **Phase 2: Image Registry (Docker Hub)**.
