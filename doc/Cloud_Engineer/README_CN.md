# 云工程师 — 职责与分级交付要求

[English](README.md) · [简体中文](README_CN.md) · [项目总览](../../README_CN.md)

> **项目:** Datathon 用例 4 — AI 辅助传统系统迁移  
> **技术栈：** Python + SQL + Amazon S3 + Snowflake + Streamlit（无强制 Java／Spring Boot／独立 API）。  
> **状态：** 以下是任务与验收标准，不代表功能已实现。

## 1. 角色职责与边界

**核心职责：** 提供数据管道实际可用、安全且成本可控的 S3 与 Snowflake 开发环境。

**职责边界：** 负责云资源、权限与连接交接；不负责定义 KPI、判断业务 SQL 正确性或开发 Streamlit 界面；无需单独的后端服务器。

## 2. 技能等级与任务规则

**Minimum** 为本角色的 MVP 必交项，适合在指导下完成明确任务的成员；**Standard** 包含 Minimum，适合能独立实施与测试的成员；**Advanced** 包含前两级，适合承担复杂故障、自动化与架构增强的成员。能力等级用于分配任务，不是人员评价。

### 最低交付（Minimum Delivery）

**适配经验：** 能在指导下使用 AWS 与 Snowflake 控制台配置基础云资源。

**本项目任务：**

- 创建项目 S3 Bucket／Prefix 及 Snowflake DEV 数据库与 Warehouse；先确认比赛与账户限制。
- 配置受限 IAM、Snowflake Storage Integration 与可读取指定 RAW 路径的 External Stage。
- 按需授予团队成员最小权限，确保密码、密钥与患者／客户数据不提交到 GitHub。

**具体交付物：**

- `infra/setup.md`：资源名称、安全配置步骤和权限交接（不含密钥）。
- 授权测试文件能经 Snowflake External Stage 读取的证据。

**验收标准：**

- Data Engineer 使用分配的权限能访问约定 S3 路径与 Snowflake Stage。
- 环境正常运行，且没有将凭证公开到仓库。

### 标准交付（Standard Delivery）

**适配经验：** 能独立管理权限、环境一致性和基本云环境可运维性。

**本项目任务：**

- 条件允许时隔离 DEV 与正式数据权限，为 Streamlit 配置仅限正式 MART 查询入口的只读身份。
- 设置 AWS 预算告警、合理的 Snowflake Warehouse 和自动暂停，并规定成本检查负责人／频率。
- 记录权限撤销、对象保留／版本化选项、连接排障及安全的环境重建方法。
- 收集访问／导入错误与服务可用性证据，使管道负责人能区分临时故障和权限错误。

**具体交付物：**

- `infra/access-matrix.md`、成本控制说明及可重复的 DEV 环境配置步骤。
- 只读 Dashboard 身份及一次拒绝越权访问的测试记录。

**验收标准：**

- Dashboard 凭证不能写入 RAW、STAGING 或 MART，且只能读取已批准的正式对象。
- 其他成员无需共享个人管理员凭证即可按文档重建环境。

### 进阶交付（Advanced Delivery）

**适配经验：** 能交付可复现云基础设施及运维恢复措施。

**本项目任务：**

- 使用 Terraform 或等效经审核的 IaC 描述约定资源，避免未经批准的破坏性修改。
- 对导入失败、未授权访问和重大云成本变化配置针对性的监控／告警。
- 演练凭证轮换、源对象恢复与权限恢复，并分别解释 S3 版本化和数据仓库恢复的限制。

**具体交付物：**

- 经审核的 IaC、监控与恢复操作手册。
- 故障／恢复演练记录及成本、安全风险评估。

**验收标准：**

- 授权成员可重建非机密配置并验证 S3 至 Snowflake 的连接。
- 相关告警及恢复流程有实际演练证据，而非仅列为计划。

## 3. 跨角色输入与交接

**需要从其他角色获取：**

- 拟议数据流、数据量估计、云预算和团队权限需求。
- Data Engineer 提供的源文件格式与 Snowflake RAW 导入计划。

**需要向其他角色交付：**

- Bucket／Prefix、Storage Integration、External Stage 及受限访问说明 → Data Engineer。
- 正式 MART 的只读访问配置 → Streamlit 负责人；资源／成本状态 → Team Lead。

## 4. 全团队共同遵守的验收约束

- 原始数据、运行批次及转换过程必须可追溯；不允许无记录地删除异常行。
- 仅候选 MART 通过独立对账与关键质量检查后，才允许更新正式查询入口；失败批次不能替换上一成功版本。
- AI 生成的 SQL 必须经人工审核并在 DEV／候选数据测试；验证基准不得仅由同一 AI 生成。
- Streamlit 只读已发布数据；如果尚无成功版本，应明确显示“暂无已验证数据”。
- 不得将计划、未执行的测试或可选 Advanced 功能标注为已完成。
