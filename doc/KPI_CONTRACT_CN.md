# KPI 契约：按月份、地区汇总的净销售额

[简体中文](KPI_CONTRACT_CN.md) · [English](KPI_CONTRACT.md) · [项目总览](../README_CN.md)

> **状态：** 已于 2026-09-24 批准用于 Phase 1 本地原型。

## 目的

为本地 Python 与 DuckDB 开发定义一项确定性业务结果。后续 AWS 结果也将使用同一契约对账，但 AWS 部署不属于 Phase 1。

## 指标

| 字段 | 定义 |
|---|---|
| 名称 | 按月份、地区汇总的净销售额 |
| 粒度 | 每个日历月、每个地区一行 |
| 度量 | 有效明细行 `Total Price` 之和 |
| 币种 | NZD |
| 舍入 | 使用完整精度求和，再将月度结果保留两位小数 |
| 月份 | 从报表期间标题读取，例如 `January 2026` |
| 地区 | 读取地点标题最后一个 ` - ` 后的内容，例如从 `Kea Wellness - Central` 提取 `Central` |

## Phase 1 权威输入

- 正向干净 Fixture：`data/grouth_truth/2026-1.xlsx` 至 `2026-4.xlsx`。
- 负向质量 Fixture：`data/legacy_dirty/sales_dirty.csv`。
- 注入错误证据：`data/corruption_manifest/corruption_log.csv`。
- 运行元数据：`data/validation/run_metadata.csv`。

Phase 1 保留现有目录名 `grouth_truth`，避免无关文件移动。后续可在同时更新所有引用时修正名称。

## 源数据解释

| 源字段 | 含义 | Phase 1 用途 |
|---|---|---|
| A 列／`raw_col_1` | 地点标题、产品、折扣、运费或总计标签 | 判断行类型并提取地区 |
| B 列／`raw_col_2` | 订单数 | 保留用于审计，不参与 KPI 计算 |
| C 列／`raw_col_3` | 商品数量 | 保留用于审计，并在适用时验证数值 |
| D 列／`raw_col_4` | Total Price | 权威 KPI 金额 |
| E–G 列／`raw_col_5`–`raw_col_7` | 重复报表总计 | 不参与 KPI 计算 |
| `source_row_id` | 源快照中的稳定行标识 | 去重和血缘 |
| `ingest_row_id` | 导入记录标识 | 仅用于导入审计 |

## 行处理规则

1. 排除报表标题和指标标题行。
2. 使用地点汇总行获取业务／地点及地区，但绝不将其金额加入 KPI。
3. 包含地点汇总行与最终 `Total` 行之间的有效明细行。
4. 包含产品、折扣、电子钱包调整、赠品调整和运费行。源数据中的负数和零均为有效值。
5. 最终 `Total` 行不参与聚合，只作为对账控制值。
6. 只使用 D 列／`raw_col_4`，不得累加 E–G 列中的重复总计。
7. `source_row_id` 重复时，接受第一条其他字段有效的记录，将后续记录作为重复行拒绝。
8. KPI 金额缺失或不是数值的明细行必须拒绝。不得静默改为零或推断替代值。
9. 拒绝记录必须保留 `run_id`、行标识及明确拒绝原因。

## 验证场景

### 干净基准必须通过

| 月份 | 地区 | 明细行数 | 预期净销售额（NZD） |
|---|---|---:|---:|
| January 2026 | Central | 362 | 89,312.44 |
| February 2026 | Central | 153 | 51,778.37 |
| March 2026 | Central | 201 | 79,635.52 |
| April 2026 | Central | 194 | 81,426.50 |
| **总计** | | **910** | **302,152.83** |

对于每个干净工作簿，明细行 D 列之和必须同时等于地点汇总和最终报表总计，允许误差为 NZD 0.01。

### 脏数据 Fixture 必须安全失败

现有 Corruption Manifest 包含 24 项注入问题：

- 10 项缺失值。
- 7 项无效数值。
- 7 条重复行。

本地验证命令必须检测并报告这些问题类别。失败候选可以用于检查，但不得标记为已验证，也不得替换之前已验证的 MART 结果。

## 必需 DuckDB 输出

| 对象 | 最少内容 |
|---|---|
| `raw.sales_raw` | 源字段、`source_row_id`、`ingest_row_id`、`run_id` 及源名称 |
| `staging.sales_clean` | 已解析月份、业务／地点、地区、明细标签、数值金额及血缘字段 |
| `staging.sales_rejected` | 被拒绝行、拒绝原因及血缘字段 |
| `mart.monthly_sales_by_region` | `month`、`region`、`total_sales`、`source_row_count`、`run_id` 及验证状态 |
| `validation.run_results` | 检查名称、预期值、实际值、状态及 Run ID |

## Phase 1 验收条件

- 一条本地命令可从受控 Fixture 重建 DuckDB 数据库。
- 四个干净基准全部符合本契约。
- 脏数据 Fixture 能暴露已记录问题，并返回验证失败状态。
- 自动化测试覆盖行分类、数值解析、去重、拒绝、聚合及对账。
- FastAPI 可公开最新本地 KPI 和验证状态，且不需要 AWS 凭证。
- README 记录准确的本地重跑和测试命令。

## Phase 1 不包含

- Docker、ECR 和 ECS 部署。
- S3、Glue 和 Athena 集成。
- Streamlit 和生产身份验证。
- 调度、基础设施即代码、监控和恢复自动化。

