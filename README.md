# ECS Fargate + Docker Hub + GitHub Actions (Learning Project)

This repository documents an **end‑to‑end container deployment** using **Amazon ECS (Fargate)**, **Docker Hub**, and **GitHub Actions CI/CD**.

---

## 1. Big Picture

**What I built:**

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

