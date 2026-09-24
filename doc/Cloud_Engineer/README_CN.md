# 云平台工程师

[简体中文](README_CN.md) · [English](README.md) · [项目总览](../../README_CN.md) · [架构图](../aws-python-architecture.html)

> **技术栈：** 本地使用 Python + DuckDB；线上使用 Amazon ECS Fargate 运行容器化 Python/FastAPI，并以 Amazon S3、AWS Glue Data Catalog 和 Amazon Athena 构建 AWS 数据链路。

## 职责

负责 AWS 基础资源、IAM、成本控制、部署路径和云端可运维性交接。不负责 KPI 定义、转换逻辑正确性或看板业务设计。

## Phase 1 — Local Prototype（本地原型）

**任务**

- 确认 AWS 账户、Region、服务配额、预算及资源命名规范。
- 设计 Pipeline 写入、Athena 开发、ECS Task 只读和管理员的最小权限角色。
- 说明本地 AWS 标准凭证链用法，不在仓库保存 Access Key。
- 定义 S3 Prefix、Glue Database／Table、Athena Workgroup、ECR Repository 及 ECS Service 名称。

**证据与退出条件**

- 已评审资源方案、IAM 矩阵、预算负责人及安全的本地配置指南。
- Git 中不存在 Secret 或敏感数据集。

## Phase 2 — AWS MVP

**任务**

- 创建加密且禁止公共访问的 S3 RAW/STAGING/MART 与 Athena Result 路径。
- 配置 Glue Data Catalog、Athena Workgroup 限额、查询结果位置及受限 IAM Role。
- 将 FastAPI 镜像发布到 ECR，并通过 ECS Express Mode/Fargate 部署，同时使用受限 Task Role 和 Infrastructure Role。
- 启用 AWS Budgets，记录资源清理及连接排障步骤。

**证据与退出条件**

- Data Engineer 只能写入约定 Prefix，并可查询开发 Workgroup。
- ECS Task 能读取正式数据入口，但不能修改 RAW、STAGING 或 MART。
- 留存一次权限拒绝测试和一次端到端连接成功证据。

## Phase 3 — Production-ready（生产就绪）

**任务**

- 使用经评审的 IaC 定义资源，并分离开发权限与正式读取权限。
- 配置 EventBridge、Step Functions、CloudWatch 日志／告警及必要的 Secrets Manager。
- 演练撤销权限、轮换凭证、恢复 S3 对象及重建环境。

**证据与退出条件**

- IaC、监控与告警、成本控制和恢复 Runbook 均已版本化。
- 另一名授权成员能重建非机密环境，并完成一次恢复演练。

## 输入与交付

- 输入：数据规模／格式、Pipeline 操作、看板查询契约、预算及保留要求。
- 输出：S3 Prefix、Glue Database、Athena Workgroup 与 IAM Role → Data Engineer；ECR／ECS Service 和只读 Task Role → API／UI 负责人；成本／安全状态 → Team Lead。

## 共同验收规则

- 线上服务全部位于 AWS；DuckDB 仅作为上线前本地测试依赖。
- S3 禁止公共访问并启用加密。
- 通过 Workgroup、Parquet 与分区限制 Athena 扫描成本。
- Phase 3 控制措施未经演练不得标记为完成。
