# API 接口文档

## 概述

所有接口前缀 `/api`，Base URL 为 `http://host:8000`。Content-Type 为 `application/json`（文件上传除外）。无认证。

## 账号管理 — `/api/accounts`

### GET /api/accounts — 获取账号列表

| 查询参数 | 类型 | 默认值 | 说明 |
|----------|------|--------|------|
| `search` | string | `""` | 模糊匹配 account_name 和 phone（ILIKE） |
| `server` | string | `""` | 精确匹配 |
| `region` | string | `""` | 精确匹配 |
| `email` | string | `""` | 模糊匹配（ILIKE） |
| `class_name` | string | `""` | 模糊匹配（ILIKE） |
| `cloud_device` | string | `""` | 模糊匹配（ILIKE） |

响应：`AccountResponse[]`，按 `created_at` 降序。

### GET /api/accounts/filters — 获取筛选选项

响应：`{ "servers": ["区服1", ...], "regions": ["大区1", ...] }`，去重且非空，按字母升序。

### POST /api/accounts — 新增账号

请求体：`AccountCreate`
- `account_name`、`phone`、`cloud_device` 必填（空字符串或仅空白返回 422）
- phone 已存在返回 409

响应：`AccountResponse`，状态码 201。

### POST /api/accounts/import-excel — Excel 批量导入

请求：`multipart/form-data`，字段 `file`（.xlsx/.xls）

行为：第一行为表头（中文名映射），后续行按 `phone` upsert：
- phone 为空 → 跳过该行
- phone 已存在 → 覆盖更新
- phone 不存在 → 新增

响应：`AccountResponse[]`，状态码 201。

中文表头映射：`账号名/账号`→account_name、`手机号/手机`→phone、`云机名称/云机`→cloud_device、`区服`→server、`大区`→region、`职业`→class_name、`邮箱`→email、`地点`→location、`验证码/验证码URL/验证码 URL`→verify_code_url、`PIN码/PIN 码`→pin_code、`修复码`→recovery_code

### PUT /api/accounts/{id} — 编辑账号

路径参数：`id: int`，请求体：`AccountUpdate`（仅更新提交的字段，`exclude_unset=True`）
- 不存在 → 404
- phone 冲突 → 409

### DELETE /api/accounts/{id} — 删除账号

级联删除关联的 diamond_records、diamond_snapshots、diamond_sales。状态码 204。

### POST /api/accounts/batch-delete — 批量删除

请求体：`{ "ids": [1, 2, 3] }`。逐个 ORM delete 以触发级联。状态码 204。

---

## 收益记录 — `/api/records`

### GET /api/records — 查询收益记录

| 查询参数 | 类型 | 说明 |
|----------|------|------|
| `date` | date | 精确匹配录入日期 |
| `account_id` | int | |
| `location` | string | 模糊匹配（ILIKE） |

响应：`DiamondRecordResponse[]`，按 `recorded_at DESC, id DESC`。

### POST /api/records — 批量录入

请求体：`{ "records": [{ "account_id": 1, "amount": 120, "location": "副本", "recorded_at": "2026-05-17" }] }`
- account_id 不存在 → 400
- **自动同步钻石趋势**：创建记录后自动创建/更新 DiamondSnapshot 并运行间隙均分

响应：`DiamondRecordResponse[]`，状态码 201。

### POST /api/records/import-excel — Excel 导入收益

| 参数 | 类型 | 说明 |
|------|------|------|
| `recorded_at` | date (query) | **必填**，录入日期 |
| `location` | string (query) | 缺省地点，Excel 中地点为空时使用 |
| `file` | file | .xlsx/.xls |

Excel 格式：列1=云机名称，列2=收益，列3=地点（可选）。按 cloud_device 匹配账户，未匹配跳过。**自动同步钻石趋势**。状态码 201。

### DELETE /api/records/{id} — 删除记录

状态码 204。

### GET /api/records/dates — 获取录入日期列表

响应：`["2026-05-17", "2026-05-15", ...]`（ISO 格式字符串，降序）。

---

## 钻石管理 — `/api/diamonds`

### POST /api/diamonds/sync — 同步钻石

请求体：
```json
{
  "updates": [
    { "cloud_device": "云机-01", "diamonds": 120 },
    { "cloud_device": "云机-02", "diamonds": 85 }
  ]
}
```

行为：
- 按 `cloud_device` 匹配账户，未匹配静默跳过
- 更新 `current_diamonds` 为传入值
- **间隙均分**：若与上次快照有间隔天数，总变化量（含间隔内卖出量）按天均分，余数靠后
- **同日再同步**：累积 change（不覆盖，加增量）
- **首次/连续天**：直接记录当日变化

响应：`{ "updated_count": 2, "snapshot_count": 2 }`

### POST /api/diamonds/sell — 卖出钻石

请求体：`{ "account_ids": [1, 2, 3] }`

行为：
- 跳过 current_diamonds ≤ 0 的账户
- 创建 DiamondSale 记录（diamonds_sold = current_diamonds）
- current_diamonds 清零
- 更新当日快照（diamonds=0, change = -上次快照diamonds）

响应：`{ "sold_count": 2, "total_diamonds_sold": 350 }`

### GET /api/diamonds/sales — 卖出记录列表

| 查询参数 | 类型 | 说明 |
|----------|------|------|
| `start_date` | date | 卖出日期起始 |
| `end_date` | date | 卖出日期截止 |
| `account_id` | int | |

响应：`DiamondSaleResponse[]`（含 account_name、cloud_device、phone），按 `created_at` 降序。

### GET /api/accounts/{id}/diamond-snapshots — 单账户快照历史

响应：`DiamondSnapshotResponse[]`（date、diamonds、change），按 date 降序。

---

## 分析查询 — `/api/analytics`

### 概览

| 路径 | 说明 |
|------|------|
| `GET /analytics/overview` | total_diamonds、total_records、entry_count、top_location |
| `GET /analytics/overview/comparison` | 最近两次录入批次的环比对比 |
| `GET /analytics/overview/yoy` | 当年当月 vs 去年同月同比对比 |

### 趋势

| 路径 | 参数 | 说明 |
|------|------|------|
| `GET /analytics/daily-trend` | — | 每日收益趋势（来自 diamond_records），含 change_rate |
| `GET /analytics/diamond-trend` | — | **钻石日变化趋势**（聚合 snapshot.change），收益看板趋势图数据源 |
| `GET /analytics/weekly-trend` | — | 按 ISO 周聚合 |
| `GET /analytics/accounts/{id}/trend` | — | 单账户每日趋势，含 change_rate |
| `GET /analytics/accounts/{id}/trend-compare` | — | 单账户 vs 每日全体均值对比 |
| `GET /analytics/by-location/{location}/trend` | — | 某地点每日趋势 |

### 分组与排行

| 路径 | 参数 | 说明 |
|------|------|------|
| `GET /analytics/by-location` | — | 按地点分布 |
| `GET /analytics/by-server` | `recorded_at?` | 按区服分布 |
| `GET /analytics/by-class` | `recorded_at?` | 按职业分布 |
| `GET /analytics/by-region` | — | 按大区分布 |
| `GET /analytics/account-ranking` | `limit?=20`, `start_date?`, `end_date?` | 账号收益排行 |
| `GET /analytics/server-region-cross` | — | 区服×大区交叉统计 |

### 其他

| 路径 | 参数 | 说明 |
|------|------|------|
| `GET /analytics/calendar` | `year?` | 日历热力图数据，默认当年 |
| `GET /analytics/low-performers` | `recorded_at?`, `threshold?=0.5` | 低收益账户（低于均值×阈值） |
| `GET /analytics/records` | `start_date?`, `end_date?`, `account_id?`, `location?` | 多维度收益记录筛选 |

---

## 通用 Schema

### TrendPoint
```json
{ "date": "2026-05-17", "amount": 150, "change_rate": 12.5 }
```
change_rate 为 null 时表示上期为零无法计算。

### AccountResponse
```json
{
  "id": 1, "account_name": "账号1", "phone": "138...", "cloud_device": "云机-01",
  "current_diamonds": 150, "location": "副本", "server": "安卓1区", "region": "电信",
  "class": "战士", "email": "...", "created_at": "2026-05-01T12:00:00"
}
```

### DiamondRecordResponse
```json
{ "id": 1, "account_id": 1, "amount": 120, "location": "深渊副本", "recorded_at": "2026-05-17", "account": {...} }
```
