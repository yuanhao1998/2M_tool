# 数据库模型文档

## 概述

SQLite 数据库，文件位于 `data/game_accounts.db`。通过 SQLAlchemy ORM 管理，启动时自动建表，`init_db()` 处理已有表的 ALTER TABLE 迁移。启用 `PRAGMA foreign_keys = ON` 确保外键约束。

## 表结构

### accounts — 游戏账号

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `account_name` | TEXT(100) | NOT NULL | 账号名，必填 |
| `password` | TEXT(100) | NOT NULL, DEFAULT '' | |
| `email` | TEXT(200) | NOT NULL, DEFAULT '' | |
| `server` | TEXT(100) | NOT NULL, DEFAULT '' | 区服 |
| `region` | TEXT(100) | NOT NULL, DEFAULT '' | 大区 |
| `class` | TEXT(100) | NOT NULL, DEFAULT '' | 职业（DB 列名 `class`，Python 属性名 `class_name`） |
| `pin_code` | TEXT(50) | NOT NULL, DEFAULT '' | |
| `phone` | TEXT(50) | NOT NULL, DEFAULT '' | 手机号，业务唯一标识，Excel 导入 match key |
| `cloud_device` | TEXT(100) | NOT NULL, DEFAULT '' | 云机名称，必填，钻石同步 match key |
| `location` | TEXT(200) | NOT NULL, DEFAULT '' | 地点 |
| `current_diamonds` | INTEGER | NOT NULL, DEFAULT 0 | 当前钻石数量，同步更新，卖出清零 |
| `verify_code_url` | TEXT(500) | NOT NULL, DEFAULT '' | |
| `recovery_code` | TEXT(100) | NOT NULL, DEFAULT '' | |
| `created_at` | DATETIME | DEFAULT NOW | 自动设置 |

**关系**：一对多 → `diamond_records` / `diamond_snapshots` / `diamond_sales`，全部 `cascade="all, delete-orphan"`。

**业务约束**：phone 唯一（应用层校验），account_name / phone / cloud_device 创建时不可为空。

---

### diamond_records — 钻石收益记录

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `account_id` | INTEGER | FK → accounts.id, NOT NULL | 级联删除 |
| `amount` | INTEGER | NOT NULL | 钻石数量 |
| `location` | TEXT(200) | NOT NULL, DEFAULT '' | 收益地点 |
| `recorded_at` | DATE | NOT NULL | 录入日期 |

用途：手动录入或 Excel 导入的收益数据，用于分析看板的各维度统计。

---

### diamond_snapshots — 钻石每日快照

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `account_id` | INTEGER | FK → accounts.id, NOT NULL | 级联删除 |
| `date` | DATE | NOT NULL | 快照日期 |
| `diamonds` | INTEGER | NOT NULL | 当日钻石数量 |
| `change` | INTEGER | NOT NULL, DEFAULT 0 | 与昨日快照的变化量 |

**表约束**：`UNIQUE(account_id, date)` — 每日每账户仅一条，重复同步时 upsert 而非新增。

**change 计算规则**：

同步时用**间隙均分算法**：
1. **同日再同步**：累积 change（`existing.change += 新值 - 旧值`）
2. **有间隔天数**：总变化量 = 本次 diamonds - 上次快照 diamonds + 间隔内卖出总量；再按天数均分，余数分配给靠后日期
3. **首次同步/连续天**：直接记录当日变化

卖出时不创建快照，由后续同步时的间隙均分自然覆盖卖出日的产出。

收益录入时同步触发：`POST /api/records` 和 `/records/import-excel` 自动创建/更新快照并重跑间隙分布。

用途：`/analytics/diamond-trend` 聚合 change 按日展示趋势，精确到每天的生产增量。

---

### diamond_sales — 钻石卖出记录

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | |
| `account_id` | INTEGER | FK → accounts.id, NOT NULL | 级联删除 |
| `diamonds_sold` | INTEGER | NOT NULL | 卖出钻石数量 |
| `sale_date` | DATE | NOT NULL | 卖出日期 |
| `created_at` | DATETIME | DEFAULT NOW | 记录创建时间 |

用途：卖出操作时自动创建，在钻石流水页面展示卖出历史。

---

## ER 关系

```
Account (1) ──→ (*) DiamondRecord    (cascade delete)
Account (1) ──→ (*) DiamondSnapshot  (cascade delete, unique(account_id, date))
Account (1) ──→ (*) DiamondSale      (cascade delete)
```

## 迁移策略

`main.py` 中的 `init_db()` 检查 `accounts` 表是否已有 `current_diamonds` 列，若无则执行：
```sql
ALTER TABLE accounts ADD COLUMN current_diamonds INTEGER NOT NULL DEFAULT 0
```
新建表由 `Base.metadata.create_all()` 自动创建。

## 匹配规则

| 操作 | 匹配字段 |
|------|----------|
| 账号 Excel 导入 upsert | `phone` |
| 收益 Excel 导入 | `cloud_device` |
| 钻石同步 API | `cloud_device` |
| 账号新增唯一校验 | `phone` |
