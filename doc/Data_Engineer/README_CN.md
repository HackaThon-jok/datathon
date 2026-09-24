# 数据工程师

[简体中文](README_CN.md) · [English](README.md) · [项目总览](../../README_CN.md) · [架构图](../aws-python-architecture.html)

> **技术栈：** 本地使用 Python + DuckDB；线上使用 Amazon ECS Fargate 运行容器化 Python/FastAPI，并以 Amazon S3、AWS Glue Data Catalog 和 Amazon Athena 构建 AWS 数据链路。

## 职责

负责源数据检查、提取、文件格式、manifest、批次血缘和安全导入。必须保留源数据异常，不能为了通过对账而修改 KPI 逻辑。

## Phase 1 — Local Prototype（本地原型）

**任务**

- 检查真实工作表／数据表，记录字段、推断类型、行数和异常。
- 编写 Python 提取与导入命令，将不变的源快照载入 DuckDB RAW。
- 生成 batch_id、run_id、SHA-256，以及包含预期行数和来源标识的 manifest。
- 生成本地 RAW/STAGING Parquet Fixture，不写死机器路径或凭证。

**证据与退出条件**

- 可重复的 Python 命令、manifest 及源到 DuckDB 行数报告。
- 同一批次重跑不会使本地业务结果翻倍。

## Phase 2 — AWS MVP

**任务**

- 将同一套 Python 包容器化，向 ECR 发布不可变镜像，并在 ECS Fargate 上验证健康检查接口。
- 将不可变源文件和 manifest 上传至约定的 S3 RAW Prefix。
- 将带批次／运行元数据的类型化压缩 Parquet 写入 STAGING/MART 候选路径。
- 注册或更新 Glue Catalog 元数据，并验证 Athena 可查询候选数据。
- 区分格式错误和临时 AWS 故障；仅对临时故障进行有限重试。

**证据与退出条件**

- 源 → S3 → Glue → Athena 血缘、行数和拒绝记录证据可复现。
- 相同批次重跑不会重复；格式错误文件标记为 FAILED，而不是静默通过。

## Phase 3 — Production-ready（生产就绪）

**任务**

- 维护版本化容器入口和经过测试的镜像回滚路径。
- 增加 EventBridge／Step Functions 调度、检查点和中断恢复。
- 只有存在稳定源 Key／Watermark 时才实现 Schema Evolution、Replay 和增量导入。
- 输出结构化 CloudWatch 指标与告警，不记录敏感原始数据。

**证据与退出条件**

- 留存定时运行、Replay、部分失败恢复和 Schema 变更测试。
- 恢复过程不会覆盖或重复上一次正式数据集。

## 输入与交付

- 输入：已验证数据源和字段 → Data Analyst／Architect；S3、Glue、Athena 与 IAM 配置 → Cloud Engineer。
- 输出：Schema、Parquet 路径、批次／运行 ID、行数及错误 → Analytics Engineer／Data Scientist；重跑证据 → Architect。

## 共同验收规则

- 使用 Python 提供可重复的 Pipeline 入口，使用 DuckDB 做本地验证。
- RAW 保持不可变，并记录到候选输出的全部转换。
- RAW 导入成功不等于 PUBLISHED；发布由独立 Validation Gate 决定。
- Phase 2 数据路径跑通前不引入 Phase 3 复杂度。
