# 数据分析师

[简体中文](README_CN.md) · [English](README.md) · [项目总览](../../README_CN.md) · [架构图](../aws-python-architecture.html)

> **技术栈：** 本地使用 Python + DuckDB；线上使用 Amazon ECS Fargate 运行容器化 Python/FastAPI，并以 Amazon S3、AWS Glue Data Catalog 和 Amazon Athena 构建 AWS 数据链路。

## 职责

负责 KPI 业务语义、独立业务基准、API／UI 要求及业务签核。如果 MVP 纳入可选 Streamlit UI，必须交付可运行的 Python 代码；只有 Wireframe 不算完成看板。

## Phase 1 — Local Prototype（本地原型）

**任务**

- 定义“按月、地区销售额”的日期字段、币种、退货、排除规则、聚合粒度和舍入。
- 与 Data Engineer 检查真实数据源，记录数据字典与业务异常。
- 独立于候选转换计算并冻结源／旧系统基准。
- 定义 API／UI 字段、筛选、更新时间、验证状态及无数据／错误行为。

**证据与退出条件**

- 已批准 KPI 定义、样例计算、基准文件及看板验收标准。
- 已将 DuckDB 结果与基准对账，解决或说明所有重要差异。

## Phase 2 — AWS MVP

**任务**

- 确认 Athena 候选及正式结果保留已约定业务含义。
- 验证 FastAPI 响应契约；若团队将其纳入 MVP，则编写或协助实现 ECS Fargate 上带月份／地区筛选的 Python Streamlit UI。
- 展示正式批次／版本、数据更新时间和最新验证状态。
- 执行业务 UAT；若看板读取候选或未验证数据，则拒绝签核。

**证据与退出条件**

- 正式 Athena View 的 UAT 记录与业务签核。
- AWS 看板使用只读权限展示已约定 KPI、筛选、更新时间和验证状态。

## Phase 3 — Production-ready（生产就绪）

**任务**

- 只有在支持明确决策时，才增加趋势、异常和迁移就绪度展示。
- 定义阈值负责人、通知对象，以及数据过期／失败时的业务响应。
- 数据源变化时定期复核指标定义和看板价值。

**证据与退出条件**

- 决策与可视化映射、已评审阈值及业务响应指南。
- KPI 语义变更必须经过版本化批准和回归证据。

## 输入与交付

- 输入：源字段／异常 → Data Engineer；候选／正式查询入口 → Analytics Engineer／Architect。
- 输出：KPI 定义及独立基准 → Analytics Engineer／Data Scientist；UAT／签核 → Architect；展示契约 → Streamlit 负责人。

## 共同验收规则

- 独立基准不能由被测试的同一 AI 转换生成。
- 看板必须清楚区分已验证、失败和不可用数据。
- FastAPI 和可选 Streamlit UI 只负责服务／展示，不隐藏大批量转换逻辑。
- 可选 Phase 3 可视化不得延误 Phase 2 MVP。
