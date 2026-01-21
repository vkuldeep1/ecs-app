# Phase 1 — Application & Containerization (Foundation)

This phase establishes the **entire foundation** of the system. Every later AWS component (ECS, ALB, CI/CD) assumes that this phase is correct. If Phase 1 is wrong, nothing else can work.

---

## 1. Purpose of Phase 1

The goal of Phase 1 is simple:

```
Turn application code into a portable, deterministic unit that can run anywhere without modification.
```

This unit is the **Docker image.**

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

