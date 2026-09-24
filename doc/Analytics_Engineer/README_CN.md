# 分析工程师

[简体中文](README_CN.md) · [English](README.md) · [项目总览](../../README_CN.md) · [架构图](../aws-python-architecture.html)

> **技术栈：** 本地使用 Python + DuckDB；线上使用 Amazon ECS Fargate 运行容器化 Python/FastAPI，并以 Amazon S3、AWS Glue Data Catalog 和 Amazon Athena 构建 AWS 数据链路。

## 职责

负责从 RAW、STAGING 到候选 MART 的可审核转换及 AI 辅助转换记录。不得自行重新定义业务 KPI，也不能把自己的输出当作独立基准。

## Phase 1 — Local Prototype（本地原型）

**任务**

- 保留一项真实旧 SQL／报表定义，使用 AI 起草等价 Python／SQL 转换。
- 人工检查关联、NULL、日期、币种、退货、分组和破坏性操作。
- 使用有文档的源到目标映射建立 DuckDB STAGING 和候选 MART。
- 增加粒度、唯一性、必填、重复处理及所选 KPI 的本地测试。

**证据与退出条件**

- 保存原始逻辑、Prompt／Model、AI 输出、人工修改、审核人及测试结果。
- DuckDB 候选 MART 与独立 KPI 基准一致，或解释所有差异。

## Phase 2 — AWS MVP

**任务**

- 将已批准模型迁移至 Athena；优先使用可移植 SQL，必要时添加小型且有文档的方言适配。
- 生成或暴露隔离的候选数据，不直接修改正式 View。
- 使用相同 Fixture／快照比较 DuckDB 与 Athena 的 Schema、行数和月份 × 地区 KPI。
- 只有验证获批后，才通过受控 View／版本切换发布。

**证据与退出条件**

- 版本化 Athena SQL、映射文档及本地／云端契约测试结果。
- 候选失败不会改变正式查询结果。

## Phase 3 — Production-ready（生产就绪）

**任务**

- 增加可复用模型规范、血缘、分区策略及 Athena 扫描成本优化。
- 测试 Schema Evolution、迟到数据及模型 Replay。
- AI 生成的测试思路只能作为经审核草稿，并保留确定性预期结果。

**证据与退出条件**

- 持续维护模型文档、血缘、性能／成本证据及恢复测试。
- 模型变更可评审、测试、部署和回滚，且不会破坏正式结果。

## 输入与交付

- 输入：RAW/STAGING Schema 与血缘 → Data Engineer；KPI 定义和独立基准 → Data Analyst。
- 输出：候选 MART、SQL／Python 文件、映射及 AI 转换记录 → Data Scientist 和 Architect。

## 共同验收规则

- DuckDB 与 Athena 可使用少量语法适配，但数据契约和业务结果必须一致。
- AI 输出必须经过人工审核和测试。
- 候选数据和正式数据保持隔离。
- 先确保正确性，再开展 Phase 3 优化。
