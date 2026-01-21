# Phase 2 — Image Registry & Tagging (Docker Hub)

This phase explains **how container images move from your laptop to AWS**, and why **image naming and tagging errors caused real failures** later.

---

## 1. Purpose of Phase 2

Once a container works locally, the next question is:

> “How does ECS get this exact container image?”

The answer is a **container registry**. In this project, that registry is **Docker Hub**.

ECS never builds images. It only **pulls** them.

---

## 2. Docker Hub as a Distribution System

Docker Hub acts as:

* Central storage for images
* Versioned history of builds
* Source of truth for ECS

Each image is identified by:

```
<repository>:<tag>
```

Example:

```
vkuldeep1/myapp:8fa451e16e19eccec6c3965bae99a077f7706796
```

Both parts must exist **exactly**.

---

## 3. Tag Strategy Used in This Project

This project intentionally used **multiple tags over time**, which is important for understanding later behavior.

Observed tags:

* Commit SHAs (multiple)
* One manual tag: `0.1`

Examples:

```
vkuldeep1/myapp:303b5555bb2016d35117146a311bf96fd073ee25
vkuldeep1/myapp:501f7095adc4024f86b26466571210acb4fed1b0
vkuldeep1/myapp:8fa451e16e19eccec6c3965bae99a077f7706796
vkuldeep1/myapp:6ceb3746ee5b8438c5ab939e003a5fffdf060d3b
vkuldeep1/myapp:c3587dcfbc7c1a8d8a727a51e2bd5df750292ebf
vkuldeep1/myapp:0.1
```

---

## 4. Commit SHA Tags (Why They Matter)

A **commit SHA** is Git’s unique identifier for a commit.

Example:

```
8fa451e16e19eccec6c3965bae99a077f7706796
```

Using commit SHAs as image tags guarantees:

* One image per commit
* No accidental overwrites
* Exact rollback capability

This is why the CI pipeline used:

```
${{ github.sha }}
```

---

## 5. Manual Tag (`0.1`) and Why It’s Dangerous

The tag:

```
vkuldeep1/myapp:0.1
```

was pushed manually.

Problems with mutable tags:

* Can be overwritten
* ECS may pull a *different image* than expected
* Rollbacks become ambiguous

This tag later caused ECS to roll back to an older but valid image when newer SHA tags failed.

---

## 6. Public Repository ≠ Always Pullable

Even though the repository is **public**, ECS can still fail to pull images if:

* The tag does not exist
* The image name is wrong
* The task definition references a placeholder name

This happened when ECS tried to pull:

```
your-dockerhub-username/your-app:<sha>
```

while the real image was:

```
vkuldeep1/myapp:<sha>
```

Result:

```
CannotPullContainerError
pull access denied
```

The error message was misleading — the real problem was **name mismatch**.

---

## 7. ECS Pull Behavior (Critical Insight)

ECS behavior is strict and literal:

* It pulls **exactly** the string in the task definition
* It does not search
* It does not guess
* It does not fallback

If the string does not exist in Docker Hub → task fails → service rolls back.

---

## 8. Why Multiple Tags Existed

Multiple SHA tags exist because:

* Each GitHub Actions run built a new image
* Each commit produced a new SHA
* Images were immutable

This is correct and expected behavior.

The registry became a **timeline of deployments**.

---

## 9. Debugging Signals Learned in Phase 2

| Symptom                            | Meaning                      |
| ---------------------------------- | ---------------------------- |
| `CannotPullContainerError`         | Image name or tag wrong      |
| Rollback to older revision         | ECS found last working image |
| Image pulls locally but not in ECS | Task definition mismatch     |

These signals were reused repeatedly in later phases.

---

## 10. Phase 2 Outcomes

At the end of Phase 2:

* Images were versioned immutably
* Docker Hub became the single image source
* ECS image pull behavior was fully understood

This phase directly enabled Phase 3 (task definitions).

---

## 11. Transition to Phase 3

With image distribution solved:

> The next challenge becomes **telling ECS how to run the image**.

That is covered in **Phase 3 — ECS Task Definitions**.

