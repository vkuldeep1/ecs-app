# Phase 3 — ECS Task Definition (How Containers Are Run)

This phase explains **how ECS understands your container**, why some configurations worked immediately, and why others caused silent failures or rollbacks.

---

## 1. Purpose of the Task Definition

A task definition answers one question only:

> “If ECS were to run this container, **how exactly should it do so?**”

It is the ECS equivalent of a fully‑specified `docker run` command.

Important constraints:

* A task definition **does not start anything**
* It is inert configuration
* Every change creates a **new revision**

---

## 2. High‑Level Properties of Your Task Definition

From revision **9**, the task definition establishes the following invariants:

* Launch type: **AWS Fargate**
* Operating system: **Linux / x86_64**
* Network mode: **awsvpc**
* Task size: **0.25 vCPU / 1 GB memory**
* One essential container

Each of these decisions directly enabled later stages (ALB, IP targets, scaling).

---

## 3. Launch Type: AWS Fargate

Choosing **Fargate** means:

* No EC2 instances
* No host management
* No capacity planning

ECS provisions compute **only when tasks run**.

This is why setting service desired count to `0` resulted in **zero runtime cost**.

---

## 4. Network Mode: `awsvpc` (Critical)

```text
Network mode: awsvpc
```

This is one of the most important fields in the entire system.

### What `awsvpc` means

* Each task gets its **own ENI** (Elastic Network Interface)
* Each task gets its **own IP address**
* Security groups attach **directly to the task**

This is why:

* ALB target type had to be **IP**
* Security groups were attached to the ECS service
* Direct IP connectivity was possible before ALB

Without `awsvpc`, none of that would work.

---

## 5. Task‑Level Resource Sizing

```text
CPU: 0.25 vCPU
Memory: 1 GB
```

These values define the **hard ceiling** for the task.

Key points:

* Task‑level limits apply to all containers combined
* Exceeding memory limits terminates the task
* CPU is throttled, not killed

These limits are enforced by Fargate, not by Docker.

---

## 6. IAM Roles in the Task Definition

### 6.1 Task Role

```text
Task role: escTaskRole-exec
```

This role is assumed **inside the container**.

Purpose:

* Allows the application to call AWS APIs
* Used for SSM, Secrets Manager, etc.

In this phase, the role was defined but not heavily exercised.

---

### 6.2 Task Execution Role

```text
Task execution role: ecsTaskExecutionRole
```

This role is assumed by **ECS itself**, not your code.

Used for:

* Pulling container images
* Writing logs to CloudWatch
* Fetching secrets for environment variables

Misconfiguration here later caused image‑pull confusion.

---

## 7. Container Definition (The Core)

Each task definition revision contained exactly **one essential container**.

### 7.1 Container Identity

```text
Name: app-container
Essential: true
```

Why this matters:

* If this container exits → task is unhealthy
* ECS service restarts it automatically

---

### 7.2 Image Reference (Source of a Major Failure)

Originally, the image field contained:

```text
your-dockerhub-username/your-app:<sha>
```

But the real image was:

```text
vkuldeep1/myapp:<sha>
```

Because ECS pulls **exactly** this string, the task failed with:

```text
CannotPullContainerError
```

This caused:

* Task start failure
* Service deployment failure
* Automatic rollback to older revision

Once corrected, the task started successfully.

---

## 8. Port Mappings (Second Major Failure)

```text
Container port: 8000
Protocol: TCP
App protocol: HTTP
```

This mapping must match:

* The port the application listens on
* The ALB target group port

Earlier revisions exposed port **80**, while the app listened on **8000**.

Result:

* ALB could not reach the container
* Targets were never registered
* ALB returned `503`

Fixing the port mapping immediately resolved target registration.

---

## 9. Environment Variables & Secrets

The container received configuration via environment variables:

```text
APP_NAME       ← SSM Parameter
ENVIRONMENT    ← SSM Parameter
SECRET_KEY     ← Secrets Manager
```

Important behaviors:

* Missing variables caused the app to exit
* Exit code ≠ 0 signaled ECS of failure
* ECS service reacted correctly by restarting tasks

This validated the **fail‑fast configuration strategy** from Phase 1.

---

## 10. Logging Configuration

```text
Log driver: awslogs
Log group: /ecs/myapp
Stream prefix: ecs
```

This configuration allowed:

* Immediate log visibility
* Task‑level debugging
* Correlation of failures with deploy attempts

CloudWatch logs became the primary debugging interface.

---

## 11. Why Multiple Task Definition Revisions Existed

Revisions accumulated because:

* Image name fixes
* Port mapping fixes
* Environment variable wiring

This is expected.

Task definition revisions are **immutable history**, not clutter.

---

## 12. Phase 3 Outcomes

At the end of Phase 3:

* ECS could start tasks successfully
* Containers received correct config
* Network behavior was predictable
* Failures were observable and recoverable

This enabled Phase 4: **ECS Services and lifecycle management**.

---

## 13. Transition to Phase 4

With tasks runnable:

> The next challenge becomes **keeping them alive and replacing them safely**.

That is covered in **Phase 4 — ECS Service & Fargate Lifecycle**.
