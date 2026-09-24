# Analytics Engineer：运行与交接

这一版完成单份旧报表的本地迁移、对账、失败隔离，并生成 Athena 交接 SQL。范围是 `2026-1.xlsx` 的第一个工作表。地区映射尚未提供，所以结果是“月份 × 门店”，不是已经完成的地区报表。

## 五分钟运行

在仓库根目录执行，Python 3.13 已验证：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analytics.txt
.venv/bin/python -m unittest discover -s tests -p 'test_analytics.py' -v
.venv/bin/python -m analytics.demo
```

Windows 将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。不需要 AWS 凭证。不要使用仓库旧版 `start.sh` 来启动这个模块。

最后应出现 `DEMO PASS`。其中一次 `FAIL` 是故意展示脏数据被阻止，不能把它改成 PASS。

| 场景 | 原始行 | 明细行 | 订单字段合计 | 数量合计 | 金额合计 | 状态 |
|---|---:|---:|---:|---:|---:|---|
| 原 Excel | 366 | 362 | 542 | 2395 | 89312.44 | PASS |
| 脏 CSV，去除 7 条相同重复后 | 373 | 362 | 528 | 2346 | 89312.44 | FAIL |

脏数据有 10 个缺失订单值、7 个非法数量值、7 个重复来源行。其中一个缺失值在总计行，因此对全部数值行检查，而不是只检查商品明细。金额相同也不能放行。

`orders` 的含义是旧报表 Order 列合计，不能声称是重新计算的唯一交易数。数据没有交易 ID，币种和税口径也没有确认。

## 产物在哪里

每次运行生成 `artifacts/analytics/runs/<run_id>/`：

- `raw.csv`：保留来源行和原始字段。
- `migration.duckdb`：STAGING、MART 和独立基准表。
- `staging_sales.parquet`：整理后的 362 行明细。
- `mart_monthly_store.parquet` / `.csv`：一个月份、一个门店的候选结果。
- `baseline.parquet`：直接读取旧 Excel 已有 Total 的对照值。
- `validation.json`：检查结果、异常、输入输出 SHA-256 和运行状态。

`artifacts/analytics/published.json` 只指向成功的本地演示版本。失败候选保留证据，不能改变这个指针。这是本地门禁，不等于已经在 AWS 发布。不要手动改 JSON 状态来绕过检查。

Git 内的 `docs/evidence/` 保存一次实际运行的结果；重新执行 demo 会更新证据时间和 run_id。测试和运行产物不混入原始数据。

## 交给 Cloud Engineer 的步骤

1. 从成功运行的输出找到 clean run 目录。由云负责人提供实际 Glue Database 和 S3 Prefix，数据库必须已经存在。
2. 生成交接包。下面两个云端名称是示例，须替换，不能直接当成团队资源：

```bash
.venv/bin/python -m analytics.athena \
  --run-dir artifacts/analytics/runs/实际成功的run_id \
  --database 团队实际数据库名 \
  --s3-prefix s3://团队实际bucket/analytics
```

3. 在 `athena/` 中检查 `upload.sh`，使用既有 AWS 身份运行。三个表分别上传到独立子目录，不能把不同 schema 的 Parquet 混在一个表目录。脚本包含生成时的本机绝对路径，换机器须先本地重跑并重新生成。
4. 在 Athena Engine 3、团队指定 Workgroup 中，按语句逐条执行 `01_tables.sql`，再执行 `02_candidate.sql`。表和候选 View 使用 run_id 命名，旧版本不被改写。
5. 执行 `03_validate.sql`，必须返回 `failures = 0`。检查包括云端聚合与本地 MART、旧报表基准双向比较，明细行数、空值、重复和结果组数。
6. 保存 QueryExecutionId、结果、运行 ID 和审核人。负责人审核后，才执行 `04_publish_after_review.sql`。

当前 AWS 没有在此交付中执行或验证。生成器不会连接 AWS，也不会自动发布。云端门禁需要负责人按上述步骤执行，尚未做成 IAM 强制的自动发布服务。

参考 AWS 官方 [CREATE TABLE](https://docs.aws.amazon.com/athena/latest/ug/create-table.html) 与 [Parquet SerDe](https://docs.aws.amazon.com/athena/latest/ug/parquet-serde.html)。候选查询和对账 SQL 已用同一 Parquet 在 DuckDB 执行，但这不替代 Athena 实机验证。

## 交给 API 和验证负责人的信息

API 负责人：云端验证通过后读取 `published_monthly_store`。列为 `month, store, region, batch_id, detail_rows, orders, quantity, sales_amount`。`region` 目前为 NULL，界面应显示“未映射”。本地演示可读取 published 指针所指目录的 MART，不应随便读取最新失败目录。

验证负责人：请直接在旧 Excel 核对门店行和 Total 行的 542、2395、89312.44，独立运行测试，审查折扣、运费和钱包条目是否符合团队业务口径。

数据工程师：现有 `scripts/ingest.py` 和 RAW Schema 不需改动。此模块可直接接收同 Schema 的本地 CSV。文件必须是一份报表，来源行编号从 1 连续增长；重复副本可以带新的 ingest_row_id。

## 限制与下一步

- 当前只承诺 1 月、一个门店、七列报表布局。其他月份及 `p` 文件未纳入本次验收，不应直接合并。
- 折扣、赠品、运费、钱包行都按旧报表原值参与对账。这是复现旧报表的临时口径，不是新会计政策。
- 不猜测地区，不用干净答案修补缺失值，不把 NULL 转成零。
- 金额按每条明细保留两位小数，ROUND_HALF_UP。与旧报表不能对齐则失败；数据源改币种精度时要改契约。
- 订单和数量允许负整数以保留旧逻辑；如业务禁止，需另加规则。
- 人工审核、云端执行、地区映射与最终业务签核仍需团队完成。不要在提交材料中标成已完成。
