# Phase 8 — Debugging Timeline & Failure Analysis (What Actually Went Wrong)

This phase documents the **exact sequence of failures you encountered**, in the order they happened, and explains *why each failure occurred* and *what signal told you where to look next*.

This is the most important phase for learning, because real systems are understood through failure, not success.

---

## 1. Failure #1 — "Container runs locally but not in ECS"

### Symptom

* App worked with `docker run`
* ECS task failed immediately
* Task stopped shortly after start

### Root Cause

* Missing required environment variables in ECS

Your application explicitly exits if these are missing:

```
APP_NAME
ENVIRONMENT
SECRET_KEY
```

Locally, you passed them manually. In ECS, they were initially absent.

### Signal That Mattered

* Task **STOPPED** with non‑zero exit code
* CloudWatch logs showed the missing variables

### Lesson

> A crashing container is not a failure — it is a configuration signal.

Fail‑fast behavior worked exactly as designed.

---

## 2. Failure #2 — Image Pull Error (`CannotPullContainerError`)

### Symptom

* ECS service deployment failed
* Error message:

```
CannotPullContainerError
pull access denied
```

### Root Cause

The task definition referenced:

```
your-dockerhub-username/your-app:<sha>
```

But the real image was:

```
vkuldeep1/myapp:<sha>
```

ECS does **string‑exact matching**. One wrong character breaks the pull.

### Signal That Mattered

* Task stopped **before** running
* ECS event log mentioned image pull

### Lesson

> Public registry ≠ correct image reference.

Image names are contracts, not suggestions.

---

## 3. Failure #3 — Service Keeps Rolling Back

### Symptom

* New task revision starts
* Fails
* ECS switches back to old revision automatically

### Root Cause

* ECS deployment circuit breaker detected failure
* Rollback was enabled

Nothing was "undoing" your work — ECS was protecting availability.

### Signal That Mattered

* ECS service events: *deployment failed, rolling back*

### Lesson

> Rollback is not an error. It is proof the service is working correctly.

---

## 4. Failure #4 — ALB DNS Returns `503 Service Temporarily Unavailable`

### Symptom

* ALB DNS name resolves
* Browser returns `503`

### Root Cause

* Target group had **no healthy targets**

At this stage, either:

* No tasks were registered
* Or tasks were unhealthy

ALB does not forward traffic unless at least one healthy target exists.

### Signal That Mattered

* Target group showed `0 healthy / 0 unhealthy`

### Lesson

> A 503 from ALB means "no destinations", not "app crashed".

---

## 5. Failure #5 — Targets Never Register

### Symptom

* Target group empty
* ECS tasks running

### Root Cause

* ECS service was **not attached to the load balancer**

Creating an ALB or target group alone does nothing.

Registration happens **only** when:

* ECS service references the target group
* Container name + port match

### Signal That Mattered

* Service configuration showed *no load balancer attached*

### Lesson

> Load balancers are inert until services bind them.

---

## 6. Failure #6 — Port Mismatch (The Silent Killer)

### Symptom

* Tasks registered
* Targets unhealthy
* ALB still returns `503`

### Root Cause

* Application listened on `8000`
* ECS / ALB were configured for `80`

Traffic reached the container but on the wrong port.

### Signal That Mattered

* Health checks failing
* No application logs showing requests

### Lesson

> Ports must align across **four layers**:
> app → Docker → task definition → target group

---

## 7. Failure #7 — "Why can’t I access the task public IP anymore?"

### Symptom

* Direct IP access stopped working
* ALB access worked

### Root Cause

* Task security group allowed inbound traffic **only from ALB SG**

Public IP still existed, but traffic was blocked by design.

### Signal That Mattered

* Security group inbound rules

### Lesson

> Security groups, not IPs, define reachability.

---

## 8. Failure #8 — CI Succeeds, Deploy Step Skipped

### Symptom

* Image built and pushed
* ECS not updated

### Root Cause

* CD was manual (`workflow_dispatch`)
* Only CI ran on push

This prevented accidental deployments and AWS costs.

### Signal That Mattered

* GitHub Actions workflow logs

### Lesson

> Automation without intent is risk. Manual CD was the right choice.

---

## 9. Debugging Pattern That Emerged

Across all failures, the same pattern worked every time:

1. **Read the error literally**
2. Identify which layer emitted it
3. Fix configuration at that layer
4. Let ECS retry

Guessing was never required.

---

## 10. Phase 8 Outcomes

At the end of Phase 8:

* Every failure had a clear cause
* Every fix mapped to a single layer
* Debugging became systematic, not emotional

This is the point where the system stopped feeling "mysterious".

---

## 11. Transition to Phase 9

With the full journey documented:

> The final step is to summarize **what this architecture guarantees and what it does not**.

That is covered in **Phase 9 — Final Architecture, Guarantees & Limits**.
