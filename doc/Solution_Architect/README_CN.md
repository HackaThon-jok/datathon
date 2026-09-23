# 解决方案架构师／团队负责人

[简体中文](README_CN.md) · [English](README.md) · [项目总览](../../README_CN.md) · [架构图](../aws-python-architecture.html)

> **技术栈：** 本地使用 Python + DuckDB；线上使用 Amazon S3 + AWS Glue Data Catalog + Amazon Athena + AWS 上的 Streamlit。

## 职责

负责范围、架构、具名分工、跨角色契约及基于证据的发布决策。协调完整迁移，但不默认承担所有实现。Data Analyst 负责业务口径，Data Scientist 负责独立验证，并指定一名具备 Python 能力的成员负责 Streamlit。

## Phase 1 — Local Prototype（本地原型）

**任务**

- 确认数据源、旧报表逻辑、月度地区销售额口径和 MVP 边界。
- 定义 Python 包边界、DuckDB 本地流程、数据分层、运行状态和角色交接。
- 要求统一的本地命令、配置规范和独立 Validation Gate。
- 为 AWS、导入、建模、验证、Streamlit 和发布批准指定负责人。

**证据与退出条件**

- 经评审的本地架构、职责矩阵及验收清单。
- DuckDB 可从受控快照生成候选 KPI 和验证报告。

## Phase 2 — AWS MVP

**任务**

- 批准 S3 → Glue Catalog → Athena → Validation Gate → 正式 View → App Runner 数据流。
- 定义 Schema、行数、KPI、batch_id、run_id 和查询输出的本地／AWS 契约。
- 组织端到端集成测试；关键检查失败时阻止发布。
- 确认看板角色只能读取已发布 Athena 数据入口。

**证据与退出条件**

- 已评审 AWS 架构、集成证据和发布决策记录。
- DuckDB 与 Athena 对账一致；候选失败时仍保留上次已验证版本。

## Phase 3 — Production-ready（生产就绪）

**任务**

- 批准 EventBridge／Step Functions 编排、CloudWatch、Secrets Manager 和 IaC 边界。
- 定义回滚、恢复时间、数据保留、变更批准及事故负责人。
- 演练运行失败、凭证轮换和正式版本恢复。

**证据与退出条件**

- 版本化架构决策、恢复 Runbook 及已完成的故障／恢复演练。
- 团队能重建受控环境，并说明剩余风险与成本。

## 输入与交付

- 输入：数据源／KPI 定义、数据规模、AWS 限制、团队能力及验证证据。
- 输出：已批准的契约与负责人 → 全体角色；正式 View 契约 → Streamlit 负责人；发布决策 → 团队。

## 共同验收规则

- Python 是统一实现基础；DuckDB 用于本地验证，不是线上数仓。
- Athena 候选数据只有通过独立检查并明确批准后才能发布。
- AI 输出必须人工审核，且不能作为自己的独立 Ground Truth。
- Phase 1 和 Phase 2 构成 MVP；Phase 3 不得延误可运行演示。
