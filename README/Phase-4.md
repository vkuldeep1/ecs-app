# Phase 4 — ECS Service & Fargate Lifecycle (The Control Plane)

This phase explains **why the ECS service is the real brain of the system**, how deployments actually work, and why most of the confusing behavior you observed was correct behavior.

---

## 1. Purpose of the ECS Service

An ECS service answers one question:

> “What should be true *all the time*?”

In your case:

* How many tasks should run
* Which task definition revision is valid
* How failures should be handled
* How traffic should be routed

Everything else (tasks, IPs, restarts) is a side effect of this contract.

---

## 2. Scheduling Strategy: REPLICA

```text
Scheduling strategy: REPLICA
```

This means:

* ECS maintains a fixed number of identical tasks
* Tasks are interchangeable
* Individual task identity does not matter

This is why:

* Tasks can be killed and restarted freely
* ECS can replace failed tasks without asking you

---

## 3. Desired Count (The Most Important Knob)

```text
Desired tasks: 0 (or 1 during testing)
```

Desired count controls **everything**:

* `0` → no tasks, no runtime cost
* `1` → exactly one running task
* `N` → N identical tasks

Key realization you made:

> ECS clusters and services are free. **Running tasks are not.**

This is why you repeatedly set desired count back to `0` when done.

---

## 4. Deployment Controller: ECS

```text
Deployment controller type: ECS
```

This means:

* ECS itself manages deployments
* No external system (CodeDeploy) involved

Deployment logic is fully owned by the service.

---

## 5. Deployment Strategy: Rolling Update

```text
Deployment strategy: Rolling update
Min running tasks: 100%
Max running tasks: 200%
```

This configuration means:

* ECS never drops below the current desired count
* ECS may temporarily run **double** the tasks during deploy

Example with desired count = 1:

```
Old task: 1
New task starts: +1 (total 2)
New task healthy → old task stopped
```

This guarantees **zero downtime** *if* health checks pass.

---

## 6. Deployment Circuit Breaker & Rollback

```text
Deployment failure detection: Enabled
Rollback on failures: Enabled
```

This is why your system behaved safely when things went wrong.

What ECS does:

1. Starts new task revision
2. Waits for steady state
3. If task fails → deployment fails
4. ECS rolls back to last stable revision

This saved you during:

* Image pull failures
* Port mismatches

Rollback is a **feature**, not an error.

---

## 7. Launch Type: FARGATE

```text
Launch type: FARGATE
Platform version: 1.4.0
```

This confirms:

* No EC2 instances exist
* Compute is provisioned per task
* Scaling is instant

Fargate + service is what made this system serverless.

---

## 8. Networking Configuration

### 8.1 VPC & Subnets

```text
VPC: default
Subnets: ap-south-1a, 1b, 1c
```

This allowed:

* Multi‑AZ placement
* High availability by default

Even with desired count = 1, the service was AZ‑aware.

---

### 8.2 Security Group Attachment

```text
Security group: ECSTaskSG
```

Because network mode is `awsvpc`:

* Security groups attach **directly to tasks**
* Each task ENI is protected individually

This enabled strict ALB → task isolation.

---

### 8.3 Public IP Assignment

```text
Auto-assign public IP: Enabled
```

This was used only for learning/debugging.

Later, after ALB attachment:

* Direct public access was blocked by SG rules
* ALB became the only entry point

Public IP existence ≠ public reachability.

---

## 9. Load Balancer Attachment (Critical Moment)

```text
Load balancer: ECSLoadBalancer
Target group: ecs-demo-tg
Container mapping: app-container:8000
Listener: HTTP:80
```

This is where many failures occurred earlier.

Important behaviors:

* ECS registers task IPs automatically
* ALB does nothing unless the service is attached
* Container name + port must match task definition exactly

When this was missing:

* Target group showed `0 healthy / 0 unhealthy`
* ALB returned `503`

Once attached correctly:

* Target registered
* Health checks passed
* Traffic flowed

---

## 10. Health Check Grace Period

```text
Health check grace period: 0 seconds
```

This means:

* Health checks begin immediately
* Slow‑starting apps may fail

Your app started quickly, so this was safe.

In production, this value is usually increased.

---

## 11. Force New Deployment

```text
Force new deployment: Enabled (manual)
```

This allowed:

* Redeploying the same task definition
* Testing ALB registration
* Forcing ECS to re‑evaluate health

Used primarily during debugging.

---

## 12. Why Tasks Appeared and Disappeared

Observed behavior:

* Task starts
* Task fails
* Task disappears
* Old task returns

Explanation:

* Service enforces steady state
* Tasks are disposable
* Service correctness > task persistence

This is by design.

---

## 13. Phase 4 Outcomes

At the end of Phase 4:

* Service lifecycle behavior was understood
* Rollbacks were observed and trusted
* Cost was controlled via desired count
* ALB integration succeeded

This completed the **runtime control plane**.

---

## 14. Transition to Phase 5

With a stable service:

> The next challenge becomes **traffic routing and failure visibility**.

That is covered in **Phase 5 — Load Balancer & Traffic Flow**.
