# Phase 5 — Load Balancer & Traffic Flow (How Requests Reach Containers)

This phase explains **how user traffic actually reaches your container**, why ALB behavior looked confusing at first, and how target registration, health checks, and security groups work together.

---

## 1. Purpose of the Load Balancer Layer

Containers in ECS:

* Have ephemeral IPs
* Can be replaced at any time
* Cannot be addressed reliably by users

The load balancer solves this by providing:

* A **stable DNS endpoint**
* Health‑based routing
* Automatic attachment/detachment of tasks

Key principle:

> **ALB routes traffic. It never starts containers.**

---

## 2. Target Group Configuration (Ground Truth)

Your target group configuration was:

```
Target type: IP
Protocol: HTTP
Port: 8000
Protocol version: HTTP/1
VPC: vpc-0b61c099068351de4
IP address type: IPv4
Attached load balancer: ECSLoadBalancer
```

This configuration is the **contract** between ALB and ECS.

---

## 3. Why Target Type = IP Was Mandatory

Because your task definition used:

```
networkMode = awsvpc
```

Each task received:

* Its own ENI
* Its own private IP

Therefore:

* ALB must target **IP addresses**
* Instance‑based targeting would never work

This is why the target group type had to be **IP**, not instance.

---

## 4. Port Alignment (The Final Gate)

ALB forwards traffic to:

```
HTTP → port 8000
```

This must match **three separate layers**:

1. Application listens on `8000`
2. Container port mapping exposes `8000`
3. Target group forwards to `8000`

When any one of these was wrong, traffic failed silently.

This explains why earlier configurations produced:

* Empty target groups
* Endless `503 Service Temporarily Unavailable`

---

## 5. Target Registration Lifecycle

Target registration is **not manual**.

The sequence is:

```
Service starts task
   ↓
Task gets IP
   ↓
Service registers IP with target group
   ↓
ALB begins health checks
```

If the service is not attached to the load balancer:

* Registration never happens
* Target group shows `0 healthy / 0 unhealthy`

This was observed earlier and was correct behavior.

---

## 6. Health Checks vs Task State

Important distinction:

* **Task RUNNING** ≠ **Target HEALTHY**

Health checks are performed by ALB:

* HTTP request to container IP
* On port `8000`
* Expecting HTTP 200

Only after passing health checks:

* Target is marked **healthy**
* Traffic is routed

This is why tasks could be running while ALB still returned `503`.

---

## 7. Why ALB Returned `503 Service Temporarily Unavailable`

ALB returns `503` when:

```
No healthy targets exist
```

Not when:

* The app is broken
* The container crashed

Just when:

* Targets are missing
* Targets are unhealthy

This error was a **signal**, not a bug.

---

## 8. Security Groups as Traffic Gates

Traffic path after correct configuration:

```
Internet
   ↓ (80)
ALB Security Group
   ↓ (8000)
ECS Task Security Group
   ↓
Container
```

Key consequences:

* Direct task IP access is blocked
* All traffic must flow through ALB
* ALB becomes the only supported entry point

This explains why public IP access stopped working after ALB setup.

---

## 9. What Happens During Deployments

During a rolling deployment:

1. New task starts
2. New IP is registered
3. Health checks pass
4. Old task is deregistered
5. Old task stops

Traffic never hits:

* Unhealthy tasks
* Stopping tasks

This behavior required **no pipeline coordination**.

---

## 10. Failure Modes Observed in This Phase

| Symptom              | Root Cause           |
| -------------------- | -------------------- |
| 503 error            | No healthy targets   |
| 0/0 targets          | Service not attached |
| Target never healthy | Port mismatch        |
| Task reachable by IP | SG misconfiguration  |

Each failure mapped cleanly to one configuration error.

---

## 11. Phase 5 Outcomes

At the end of Phase 5:

* Traffic flow was deterministic
* ALB behavior was predictable
* Health checks became meaningful
* Security boundaries were enforced

This completed the **request‑routing layer** of the system.

---

## 12. Transition to Phase 6

With traffic flowing correctly:

> The next challenge becomes **security boundaries and isolation**.

That is covered in **Phase 6 — Security Groups & Trust Boundaries**.
