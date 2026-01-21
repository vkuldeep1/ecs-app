# Phase 6 — Security Groups & Trust Boundaries (Who Can Talk to Whom)

This phase explains **why two security groups were required**, why the default security group was avoided, and why direct access to task public IPs stopped working after the load balancer was introduced.

---

## 1. Purpose of Security Groups

A security group answers exactly one question:

> “Is traffic from *this source* to *this destination* on *this port* allowed?”

Security groups are:

* Stateful allowlists
* Attached to **network interfaces (ENIs)**
* Enforced before traffic reaches the container

They do **not**:

* Route traffic
* Inspect HTTP payloads
* Start or stop containers

---

## 2. Why Two Security Groups Exist

You created **two distinct security groups** because there are **two distinct trust zones**:

1. The **public entry point** (ALB)
2. The **private workload** (ECS tasks)

Each zone answers a different trust question.

---

## 3. ALB Security Group (Public Trust Boundary)

### 3.1 What the ALB Represents

The Application Load Balancer is the **only internet-facing component**.

Its responsibility:

* Accept traffic from users
* Forward traffic internally

### 3.2 ALB Security Group Rules

Effective rules:

```
Inbound:
  TCP 80 from 0.0.0.0/0

Outbound:
  All traffic
```

This means:

* Anyone on the internet may reach the ALB
* The ALB may forward traffic internally

This security group **must be permissive inbound**, otherwise users cannot connect.

---

## 4. ECS Task Security Group (Private Trust Boundary)

### 4.1 What the ECS Task Represents

An ECS task is an **internal workload**, not a public service.

It:

* Runs ephemeral containers
* Is replaced freely by ECS
* Should never be addressed directly by users

### 4.2 ECS Task Security Group Rules

Effective rules:

```
Inbound:
  TCP 8000 from ALB-Security-Group

Outbound:
  All traffic
```

This means:

* Only the ALB may talk to the task
* No direct internet access is allowed

---

## 5. The Trust Chain (End-to-End)

With both security groups in place, the trust chain becomes:

```
Internet
   ↓ (80)
ALB ENI (ALB SG)
   ↓ (8000)
ECS Task ENI (Task SG)
   ↓
Container
```

Every arrow exists because of an explicit allow rule.

No implicit trust is assumed.

---

## 6. Why the Default Security Group Was Not Used

The default VPC security group has a dangerous property:

```
Allows all traffic from itself
```

Consequences:

* Any resource using the default SG can talk to any other
* Trust boundaries collapse silently
* Isolation is lost

For this reason:

* The default SG was never modified
* Dedicated SGs were created for ALB and ECS tasks

This is a foundational AWS security practice.

---

## 7. Public IP Does Not Mean Public Access

ECS tasks were configured with:

```
Auto-assign public IP: Enabled
```

Important distinction:

> **Having a public IP ≠ being reachable**

After security groups were locked down:

* Tasks still had public IPs
* Direct access to those IPs failed
* Only ALB access worked

This is correct and intentional.

---

## 8. Why Direct Task Access Must Be Blocked

Allowing direct access to task IPs would:

* Bypass the load balancer
* Bypass health checks
* Bypass future TLS and WAF rules

Blocking direct access ensures:

* All traffic is observable
* All traffic is health-checked
* All traffic follows the same path

This is not a limitation — it is the security model.

---

## 9. Common Security Group Failure Modes Observed

| Symptom                   | Root Cause                 |
| ------------------------- | -------------------------- |
| ALB works, task IP fails  | Correct configuration      |
| Both ALB and task IP work | Task SG too permissive     |
| Nothing works             | Missing inbound rule       |
| ALB unhealthy targets     | Task SG missing ALB source |

Each symptom directly maps to a trust rule.

---

## 10. Why Security Groups Belong to Services, Not Code

Security groups protect:

* Network interfaces
* Traffic paths

They do not protect:

* Python code
* Containers directly

This separation ensures:

* Code changes do not alter network trust
* Network changes do not require rebuilds

---

## 11. Phase 6 Outcomes

At the end of Phase 6:

* Trust boundaries were explicit
* Direct container access was eliminated
* ALB became the sole entry point
* Network behavior became predictable

This completed the **security layer** of the system.

---

## 12. Transition to Phase 7

With security boundaries enforced:

> The next challenge becomes **automation of builds and deployments**.

That is covered in **Phase 7 — CI/CD Pipeline (GitHub Actions)**.
