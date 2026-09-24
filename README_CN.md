# Datathon Use Case 4｜AI 辅助传统系统迁移

[简体中文](README_CN.md) · [English](README.md) · [最小任务看板](KANBAN_CN.md) · [交互式架构图](doc/aws-python-architecture.html)

> **项目状态：** Phase 1 本地 API 已可运行；Phase 2 AWS 部署正在进行。只有具备验收证据的事项才算完成。
>
> **技术方向：** Python 作为统一开发基础，使用 DuckDB 做本地验证，容器化 Python 服务全部在线运行于 AWS。
>
> **核心技术栈：** Python + DuckDB（本地）+ FastAPI + Docker + Amazon ECR + Amazon ECS Express Mode/Fargate + Amazon S3。首个线上容器验证完成后，在 Phase 2 内继续接入 AWS Glue Data Catalog 和 Amazon Athena。

## 1. 目标与范围

项目目标是完成可验证的医疗用品销售数据与报表迁移，包含一项 AI 辅助转换示例及独立对账。MVP 使用一份已确认的数据源生成“按月份、地区汇总的销售额”。

项目和所有角色统一采用以下三个阶段：

| 阶段 | 目标 | 退出条件 |
|---|---|---|
| **Phase 1 — Local Prototype（本地原型）** | 构建最小 Python API，并使用 DuckDB 在本地验证数据 | `/health`、`/data-profile` 和 `/sample` 可针对受控数据集在本地运行 |
| **Phase 2 — AWS MVP** | 构建 Docker 镜像、推送至 ECR、部署到 ECS Fargate，随后接入已验证的 S3／Glue／Athena 流程 | AWS 公网接口通过健康检查，并且无需本地凭证即可返回已验证数据 |
| **Phase 3 — Production-ready（生产就绪）** | 增加自动化、可观测性、恢复、安全及基础设施即代码 | 已演练监控、受控部署和故障恢复 |

Phase 1 和 Phase 2 是 Datathon MVP 必交范围。Phase 3 是扩展目标，不应阻碍端到端 MVP 按时完成。

## 2. 架构

可打开[交互式架构图](doc/aws-python-architecture.html)切换主题、搜索、追踪连线和导出；可编辑源文件为 [doc/aws-python-architecture.json](doc/aws-python-architecture.json)。

主要数据路径：

    旧数据库 / Excel
      → Python 数据提取、转换、manifest 与验证
      → DuckDB 本地测试
      → Amazon S3 RAW / STAGING / MART Parquet
      → AWS Glue Data Catalog
      → Amazon Athena 候选 MART
      → DuckDB 与 Athena Validation Gate
      → 已发布 Athena View
      → Amazon ECS Fargate 上的 FastAPI
      → 同一 AWS 容器平台上的可选 Streamlit UI

Phase 3 在这条路径外围增加 EventBridge、Step Functions、CloudWatch、IAM、Secrets Manager 与 IaC。

### 组件边界

| 组件 | 职责 | 边界 |
|---|---|---|
| Python 包 | 数据提取、转换、manifest、验证和编排入口 | 业务逻辑不能只存在于 Streamlit 内 |
| DuckDB | 快速执行本地 SQL 和上线前契约测试 | 不作为线上生产查询服务 |
| Amazon S3 | 保存不可变源快照和版本化 RAW/STAGING/MART Parquet | 不覆盖历史源数据证据 |
| AWS Glue Data Catalog | 管理表、Schema 与分区元数据 | 不负责业务转换或结果验证 |
| Amazon Athena | 提供线上候选与正式查询入口 | 验证前不得将候选结果发布 |
| ECS Fargate 上的 FastAPI | 最小线上 API、健康状态及只读数据访问 | 使用 ECS Task Role，绝不保存 AWS Access Key |
| ECS Fargate 上的可选 Streamlit | API 跑通后的看板及迁移状态 | 只读取正式 API 或 Athena 数据入口 |
| AWS 运维服务 | 调度、工作流状态、日志、密钥和基础设施定义 | Phase 2 跑通后在 Phase 3 引入 |

## 3. 本地到 AWS 的开发契约

仓库使用同一套 Python 包和明确的配置 Profile，避免维护彼此独立的本地版与云端版：

- **local：** 本地 Fixture 或获批快照、DuckDB 及本地输出路径。
- **aws-dev：** S3、Glue 和 Athena 候选表；凭证由 AWS SDK 标准凭证链提供。
- **aws-prod：** 正式资源与看板只读权限；仅在 Phase 3 控制措施完备后启用。

转换逻辑应尽量采用可移植 SQL 子集。如果 DuckDB 与 Athena 必须使用不同语法，则只保留小型引擎适配 SQL，并针对相同输入、Schema、行数和 KPI 契约进行测试。无需保证查询文本完全一致，但必须保证约定结果一致。

AWS Access Key、Secret、连接信息及个人／健康数据不得提交到 Git。本地使用环境配置，线上使用 IAM Role 与 AWS Secrets Manager。

## 4. 数据分层、血缘与发布

建议的 S3 路径：

    s3://<project-bucket>/raw/<dataset>/<batch_id>/source.<csv|parquet>
    s3://<project-bucket>/raw/<dataset>/<batch_id>/manifest.json
    s3://<project-bucket>/staging/<dataset>/batch_id=<batch_id>/*.parquet
    s3://<project-bucket>/mart/<dataset>/candidate/run_id=<run_id>/*.parquet
    s3://<project-bucket>/mart/<dataset>/published/version=<version>/*.parquet
    s3://<project-bucket>/athena-results/

每次运行分配唯一 run_id；每份源快照保存 batch_id、稳定来源标识或 SHA-256、行数、提取时间与 S3 Key。所有文档统一使用以下状态：

    PENDING → INGESTING → TRANSFORMING → VALIDATING → PUBLISHED
                   ↘ FAILED ←───────────────────↙

重跑必须创建新运行记录，不得删除失败证据。只有关键检查通过并由负责人批准后，才能切换正式 View 或版本指针。失败候选结果不得替换上一次已验证版本。

## 5. AI 辅助转换与验证

1. 保留未修改的旧 SQL 或经业务确认的旧报表定义、源 Schema 与业务规则。
2. 使用 AI 起草 Python／SQL 转换及源到目标映射。
3. 人工检查关联、NULL、日期、币种、退货、分组、权限及破坏性操作。
4. 先使用受控数据在本地 DuckDB 中执行草稿。
5. 将审核后的 AWS 版本运行于隔离的 Athena 候选数据集。
6. 比较源数据行数、必填字段、月份／地区 KPI 和已约定质量规则。
7. 记录 Prompt／Model、生成结果、人工修改、测试证据及审核人。

AI 生成的迁移逻辑不能同时作为唯一 Ground Truth。独立基准必须来自旧系统报表，或由另一套方法计算并经业务负责人确认。

## 6. 角色与阶段职责

以下每个角色都有独立的中英文 README，并使用完全相同的三个阶段。

| 角色 | Phase 1 — Local Prototype | Phase 2 — AWS MVP | Phase 3 — Production-ready |
|---|---|---|---|
| [Solution Architect](doc/Solution_Architect/README_CN.md) | 范围、契约及本地架构 | AWS 集成与发布关卡 | 自动化治理与恢复 |
| [Cloud Engineer](doc/Cloud_Engineer/README_CN.md) | AWS 账户、命名与权限方案 | S3、Glue、Athena、ECR/ECS Fargate 与 IAM | IaC、监控、Secrets 与恢复 |
| [Data Engineer](doc/Data_Engineer/README_CN.md) | Python 提取、DuckDB 导入及 manifest | S3 Parquet 导入与 Catalog 注册 | 定时、幂等及可恢复导入 |
| [Analytics Engineer](doc/Analytics_Engineer/README_CN.md) | AI 转换审核与本地 MART | Athena 候选／正式模型及一致性测试 | 可复用模型、血缘与优化 |
| [Data Analyst](doc/Data_analyst/README_CN.md) | KPI 定义、独立基准及看板契约 | Streamlit 实现与业务签核 | 运营与决策支持展示 |
| [Data Scientist](doc/Data_Scientist/README_CN.md) | 本地质量及对账测试 | DuckDB/Athena 独立验证 | 漂移、异常及验证监控 |

### 角色交接

    Cloud Engineer → Data Engineer：S3 Prefix、Glue Database、Athena Workgroup 与 IAM Role
    Data Engineer → Analytics Engineer：RAW/STAGING Schema、批次／运行元数据及行数
    Data Analyst → Analytics Engineer / Data Scientist：KPI 定义与独立基准
    Analytics Engineer → Data Scientist：候选 MART、转换记录及查询文件
    Data Scientist → Solution Architect：验证报告、异常及发布建议
    Solution Architect → Streamlit 负责人：已批准的正式 View 与展示契约

## 7. MVP 验收清单

- [ ] 确认一份可用数据源、月度地区销售额口径及源／旧系统独立基准。
- [ ] 使用一条干净的本地 Python 命令生成 DuckDB RAW/STAGING/MART 结果。
- [ ] 本地测试覆盖 Schema、必填字段、行数及已约定 KPI。
- [ ] 在 S3 保存源快照和 manifest，并发布带批次／运行血缘的 Parquet 数据。
- [ ] 在 Glue Data Catalog 注册 AWS 表，并使用 Athena 查询候选 MART。
- [ ] 对账 DuckDB 与 Athena 的 Schema、行数及月份 × 地区 KPI。
- [ ] 保留至少一项真实 AI 转换示例、人工审核及测试证据。
- [ ] 只发布验证通过的 Athena View；失败时保留上一次正式版本。
- [ ] FastAPI 运行在 ECS Fargate，`/health` 成功，并通过 IAM Role 而不是已保存的 Access Key 获取权限。
- [ ] 若团队将其纳入 MVP，Streamlit 运行在 ECS Fargate，并且只读取已验证的 API 或 Athena 数据入口。
- [ ] 提供本地重跑、AWS 重跑、已知限制及端到端演示说明。

## 8. 推荐目录

    datathon/
    ├── README.md / README_CN.md
    ├── doc/
    │   ├── aws-python-architecture.{html,json}
    │   └── <Role>/{README.md,README_CN.md}
    ├── data/fixtures/
    ├── src/{extract,transform,ingest,pipeline,validate}.py
    ├── sql/{common,duckdb,athena}/
    ├── tests/{unit,contract,integration}/
    ├── dashboard/app.py
    ├── docs/{data-dictionary,source-to-target,ai-conversion-log,validation-report}.md
    └── infra/

## 9. 成本与安全边界

- 使用最小权限 IAM Role，分离写入与只读路径，启用 S3 加密并阻止公共访问。
- 使用 Athena Workgroup 限额、压缩分区 Parquet 及生命周期策略控制扫描和存储成本。
- 创建线上资源前配置 AWS Budgets。
- 除非具备明确授权与隐私控制，否则只使用合成或脱敏数据。
- ECS、Athena 及 Pipeline 日志可能包含敏感信息，不得记录原始记录或 Secret。

**仍需确认：** 真实源 Schema、旧 SQL／报表定义是否可用、AWS 账户与服务配额、预算、团队分工及比赛期限。
