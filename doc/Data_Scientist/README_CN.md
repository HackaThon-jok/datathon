# 数据科学家／独立验证负责人

[简体中文](README_CN.md) · [English](README.md) · [项目总览](../../README_CN.md) · [架构图](../aws-python-architecture.html)

> **技术栈：** 本地使用 Python + DuckDB；线上使用 Amazon ECS Fargate 运行容器化 Python/FastAPI，并以 Amazon S3、AWS Glue Data Catalog 和 Amazon Athena 构建 AWS 数据链路。

## 职责

负责独立数据质量、对账和异常证据。不得重复使用被测转换作为唯一验证器，也不得批准无法解释的关键差异。

## Phase 1 — Local Prototype（本地原型）

**任务**

- 编写 Python 测试，检查 Schema、必填、唯一性、日期／金额有效性及源到 RAW 总量。
- 使用业务负责人批准的容差，将 DuckDB 月份 × 地区 KPI 与 Data Analyst 基准比较。
- 将差异归类为源数据问题、定义不一致、转换缺陷或预期舍入。
- 验证代码和预期结果必须独立于 AI 生成的迁移逻辑。

**证据与退出条件**

- 本地质量报告、分组对账及有说明的异常清单。
- 开始 AWS 发布前，不存在无法解释的关键差异。

## Phase 2 — AWS MVP

**任务**

- 使用同一快照和契约，对 Athena 候选数据执行等价检查。
- 比较 DuckDB 与 Athena 的 Schema、行数、空值／重复指标及月份 × 地区 KPI。
- 输出签署的发布建议：PASS、PASS WITH ACCEPTED EXCEPTIONS 或 FAIL。
- 验证候选失败不会改变正式 Athena View。

**证据与退出条件**

- 可重复的 DuckDB／Athena 对账报告及发布建议。
- 每项已接受差异都有负责人、说明与批准；FAIL 必须阻止发布。

## Phase 3 — Production-ready（生产就绪）

**任务**

- 针对重要字段增加数据质量趋势、漂移检查和异常分流。
- 将验证状态与指标接入 Step Functions／CloudWatch。
- 在小范围经审核样本上评估 AI 转换质量；只有支持明确迁移决策时才增加 ML。

**证据与退出条件**

- 告警阈值、分流 Runbook、误报复核及漂移／异常测试证据。
- 监控能发现注入的质量故障，并将其发送给具名负责人。

## 输入与交付

- 输入：独立 KPI 基准 → Data Analyst；RAW／候选数据及血缘 → Data Engineer／Analytics Engineer。
- 输出：质量报告、异常及发布建议 → Architect；可展示的验证状态 → API／UI 负责人。

## 共同验收规则

- 验证必须独立于 AI 生成的转换逻辑。
- 本地和 AWS 检查使用同一份有文档的业务契约。
- 关键失败阻止发布，但保留证据和上一正式版本。
- 确定性验证跑通后，Phase 3 异常／ML 才作为可选增强。
