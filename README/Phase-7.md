# Phase 7 — CI/CD Pipeline (GitHub Actions)

This phase explains **how code changes turn into running containers**, what the pipeline actually does (and does not do), and why several failures you saw were expected behaviors of a correct system.

---

## 1. Purpose of CI/CD in This System

CI/CD exists to answer two separate questions:

1. **CI (Continuous Integration)** — Can this code be turned into a container image?
2. **CD (Continuous Deployment)** — Should ECS start running that image?

Key principle:

> **CI builds artifacts. CD points the runtime at artifacts.**

Nothing in CI/CD runs traffic or manages servers.

---

## 2. Why CI and CD Are Intentionally Separated

They were kept together in one workflow file, but logically they are distinct.

### CI responsibilities

* Checkout code
* Build Docker image
* Tag image immutably
* Push image to Docker Hub

### CD responsibilities

* Read current ECS task definition
* Create a new revision with a new image
* Update the ECS service

This separation prevented partial failures from causing outages.

---
### CI/CD Code

```
name: Build and Deploy to ECS

on:
  workflow_dispatch:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ github.sha }}

    steps:
      - uses: actions/checkout@v4

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: your-dockerhub-username/your-app:${{ github.sha }}

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'workflow_dispatch'

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Register new task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition ${{ secrets.TASK_FAMILY }} \
            --query taskDefinition \
            > taskdef.json

          jq \
            --arg IMAGE "your-dockerhub-username/your-app:${{ github.sha }}" \
            '.containerDefinitions[0].image = $IMAGE
             | del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.compatibilities,.registeredAt,.registeredBy)' \
            taskdef.json > new-taskdef.json

          aws ecs register-task-definition \
            --cli-input-json file://new-taskdef.json

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster ${{ secrets.ECS_CLUSTER }} \
            --service ${{ secrets.ECS_SERVICE }} \
            --force-new-deployment

```

---

## 3. Trigger Strategy (Manual Deploys)

The workflow used **manual triggers** (`workflow_dispatch`).

Why this matters:

* No surprise deployments
* No surprise AWS costs
* Full control during learning

CI could run automatically, but **CD required explicit intent**.

---

## 4. Image Build & Tagging Strategy

The pipeline tagged images using the Git commit SHA:

```
vkuldeep1/myapp:<commit-sha>
```

Properties of this strategy:

* One image per commit
* No overwrites
* Deterministic rollbacks

This is why Docker Hub accumulated many SHA tags over time.

---

## 5. CI Stage: What Actually Happened

During CI:

1. GitHub runner checked out the repository
2. Docker built the image using the Dockerfile
3. Image was tagged with `${{ github.sha }}`
4. Image was pushed to Docker Hub

If CI failed:

* No image existed
* CD was skipped
* ECS was never touched

This prevented broken builds from reaching AWS.

---

## 6. CD Stage: Deploying to ECS

The deploy step performed **configuration changes only**.

What it did:

1. Fetched the current task definition
2. Created a copy
3. Replaced only the image field
4. Registered a new task definition revision
5. Updated the ECS service to use it

What it did **not** do:

* Build images
* Restart ALB
* Modify security groups

---

## 7. Why the Deploy Step Was Skipped

Observed behavior:

* CI succeeded
* CD step was skipped

Explanation:

* The workflow required a manual trigger
* Automatic pushes ran CI only
* CD ran only when explicitly requested

This was intentional and correct.

---

## 8. Why ECS Rolled Back Automatically

When the deploy step pointed ECS to an invalid image:

* ECS tried to start a new task
* Image pull failed
* Task never reached steady state
* Deployment was marked failed
* ECS rolled back to the last healthy revision

This behavior required **no CI/CD logic**.

Rollback lives in ECS, not in GitHub Actions.

---

## 9. Image Name Mismatch Failure (Key Incident)

Failure scenario:

```
Task definition image:
your-dockerhub-username/your-app:<sha>

Actual image:
vkuldeep1/myapp:<sha>
```

Result:

* `CannotPullContainerError`
* Failed deployment
* Automatic rollback

Lesson:

> **CI/CD is literal glue. One wrong string breaks the system.**

---

## 10. Why CI/CD Never Talks to the Load Balancer

ALB behavior is independent:

* It routes to healthy targets
* It ignores unhealthy ones

CI/CD:

* Changes what ECS runs
* Never touches traffic paths

This decoupling enables zero‑downtime deploys without coordination.

---

## 11. Observability During CI/CD

Primary debugging tools during deploys:

* GitHub Actions logs (build errors)
* ECS service events (deploy failures)
* Task stopped reasons
* CloudWatch logs

Each tool answered a different question.

---

## 12. Phase 7 Outcomes

At the end of Phase 7:

* Builds were automated
* Deployments were controlled
* Rollbacks were trusted
* CI/CD behavior became predictable

The pipeline became a **safe delivery mechanism**, not a risk.

---

## 13. Transition to Phase 8

With automation complete:

> The final step is to **document the real debugging journey**.

That is covered in **Phase 8 — Debugging Timeline & Failure Analysis**.
