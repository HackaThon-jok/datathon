# 最小可运行任务看板

[简体中文](KANBAN_CN.md) · [English](KANBAN.md) · [项目总览](README_CN.md)

> **目标：** 将现有 Python/FastAPI 服务通过 Amazon ECS Fargate 对外提供，使用 Amazon ECR 中的不可变镜像，同时保留 DuckDB 作为上线前本地测试引擎。
>
> **更新规则：** 只有具备表中所列证据，任务才能移至 **Done**。**In Progress** 同时最多保留一至两项。

## 完成定义

任务只有在实现、验证命令／输出及相关文档均可供团队查看时才算完成。只创建资源或文件但未验证，不算完成。

## Done（已完成）

| ID | Phase | 最小任务 | 负责人 | 证据 |
|---|---|---|---|---|
| AWS-001 | 1 | 创建非 Root 用户 `datathon-architect` 并启用 MFA | Cloud Engineer | Console Access 显示 MFA 已启用 |
| AWS-002 | 1 | 在本地以 `datathon-architect` 登录 AWS CLI | Cloud Engineer | `sts get-caller-identity` 返回账户 `045740834598` 及预期用户 ARN |
| AWS-003 | 1 | 验证 `us-east-1` 默认 VPC、公共子网及有效 Internet Gateway 路由 | Cloud Engineer | 已记录 VPC、六个公共子网及有效 `0.0.0.0/0` 路由 |
| AWS-004 | 1 | 创建不可变且已加密的 ECR Repository `datathon-api` | Cloud Engineer | 已记录 Repository URI、`IMMUTABLE` 和 `AES256` |
| DEV-001 | 1 | 验证本地 Docker Daemon 及 ECR 登录 | API 负责人 | Docker 返回 Linux/x86_64，且 ECR 登录成功 |
| APP-001 | 1 | 使用 DuckDB 运行本地 FastAPI 服务 | API 负责人 | `/health`、`/data-profile` 和 `/sample` 均成功返回 |
| DOC-001 | 1 | 统一所有 README：本地 Python/DuckDB，线上 ECR/ECS Fargate | Solution Architect | 中英文 README 对使用相同三个 Phase |
| DATA-001 | 1 | 确认“按月、地区销售额”定义及独立基准 | Data Analyst | 已批准双语 KPI 契约及四个月已对账基准 |

## In Progress（进行中）

| ID | Phase | 最小任务 | 负责人 | 验收证据 |
|---|---|---|---|---|
| APP-002 | 2 | 完成 FastAPI 服务的 `Dockerfile` 和 `.dockerignore` | API 负责人 | 两个文件均非空，并且镜像构建成功 |
| TEAM-001 | 1 | 与团队确认负责人、MVP 边界及验收标准 | Solution Architect | 每张 Ready 卡都有具名负责人，并保存会议决定 |

## Ready — 首个线上可运行版本

按顺序完成以下任务。

| 顺序 | ID | Phase | 最小任务 | 负责人 | 验收证据 |
|---:|---|---|---|---|---|
| 1 | REPO-001 | 1 | 删除或忽略 `.DS_Store`、空 `history_database` 文件及重复的 `.Dockerignore` 文件名 | API 负责人 | `git status --short` 不再包含意外的本地文件 |
| 2 | APP-003 | 2 | 使用唯一版本 Tag 构建 Linux/amd64 镜像 | API 负责人 | `docker build` 成功，并记录镜像 Tag |
| 3 | APP-004 | 2 | 在本地通过 8080 端口运行容器 | API 负责人 | 容器的 `/health`、`/data-profile` 和 `/sample` 检查通过 |
| 4 | AWS-005 | 2 | 将不可变的版本化镜像推送至 ECR `datathon-api` | Cloud Engineer | ECR `describe-images` 返回预期 Tag 和 Digest |
| 5 | IAM-001 | 2 | 创建受限 ECS Task Execution Role 和 Infrastructure Role | Cloud Engineer | Trust Policy 与所需权限已评审，未使用 IAM User Access Key |
| 6 | AWS-006 | 2 | 在 `us-east-1` 创建 ECS Express Mode/Fargate Service | Cloud Engineer | Service 稳定运行预期镜像 Digest |
| 7 | TEST-001 | 2 | 测试 AWS 公网健康检查及数据概况接口 | API 负责人 | 公网 `/health` 返回 200，`/data-profile` 返回受控数据集的预期数量 |
| 8 | DOC-002 | 2 | 记录部署 URL、镜像 Tag/Digest、命令、成本假设及清理步骤 | Solution Architect | 另一名成员可依据文档重建或移除 MVP |

## Ready — 完整 AWS 数据 MVP

以下任务在首个线上接口成功后进行，不得阻塞首次上线。

| 顺序 | ID | Phase | 最小任务 | 负责人 | 验收证据 |
|---:|---|---|---|---|---|
| 1 | DATA-002 | 1 | 使用一条本地命令生成 RAW/STAGING/MART 输出及验证证据 | Data Engineer | 命令可重复，且重跑不会产生重复结果 |
| 2 | AWS-007 | 2 | 将不可变源文件／Manifest 和 Parquet 输出保存到私有加密 S3 Prefix | Data Engineer | S3 Key、Checksum、行数和加密证据 |
| 3 | IAM-002 | 2 | 仅向 ECS Task Role 授予所需 S3/Athena/Glue 权限 | Cloud Engineer | 权限成功与拒绝测试均通过 |
| 4 | DATA-003 | 2 | 在 Glue 注册候选表，并通过受限 Athena Workgroup 查询 | Data Engineer | 查询成功，Result Location 与扫描上限受控 |
| 5 | VAL-001 | 2 | 对账 DuckDB 与 Athena 的 Schema、行数及 KPI | Data Scientist | PASS、PASS WITH ACCEPTED EXCEPTIONS 或 FAIL 报告 |
| 6 | RELEASE-001 | 2 | 只发布验证通过的 View／版本 | Solution Architect | 失败候选无法替换上一个已验证结果 |
| 7 | UI-001 | 2 | 决定 Datathon 演示是否需要 Streamlit | Data Analyst | 明确纳入或延期；如纳入，UI 只读取已验证数据 |
| 8 | DOC-003 | 2 | 更新架构图以匹配已验证的 ECS 与 AWS 数据链路 | Solution Architect | 架构图与 README 描述相同的已部署组件 |

## Blocked／待决策

| ID | 决策 | 负责人 | 解锁条件 |
|---|---|---|---|
| DEC-001 | MVP 演示是否需要 Streamlit，还是 FastAPI 加 `/docs` 已足够？ | Team | UI 开发前记录一个明确选择 |
| DEC-002 | 谁分别负责 API、AWS 部署、数据 Pipeline、验证及发布批准？ | Solution Architect | 每项职责有一名具名负责人 |
| DEC-003 | AWS MVP 使用什么预算告警阈值和资源清理日期？ | Account Owner | 记录金额、通知对象和清理日期 |

## Phase 3 Parking Lot — 最小可运行版本不需要

- 基础设施即代码及环境隔离。
- CI/CD、镜像漏洞门禁及自动回滚。
- EventBridge／Step Functions 调度与 Replay。
- CloudWatch Dashboard、Alarm 及运维 Runbook。
- Secret 轮换、事故演练及恢复测试。
