# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 一键启动前后端
./start.sh

# 单独启动后端
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 单独启动前端  
cd frontend && npm run dev

# 前端构建（类型检查 + Vite 打包）
cd frontend && npm run build

# 仅类型检查
cd frontend && npx tsc -b
```

## 架构概览

前后端分离的单人游戏账号管理系统。Python FastAPI 后端 + React TypeScript 前端，SQLite 数据库。

### 后端 (`backend/`)

- **main.py**：FastAPI 入口，CORS 全开，`Base.metadata.create_all()` 建表 + `init_db()` 处理已有表的 ALTER TABLE 迁移
- **database.py**：SQLite 连接（`check_same_thread=False`），`PRAGMA foreign_keys = ON` 通过 event listener 启用
- **models.py**：4 个 SQLAlchemy 模型 — `Account`、`DiamondRecord`、`DiamondSnapshot`、`DiamondSale`
  - Account 的 `class_name` 在 DB 列名为 `"class"`（Python 关键字回避）
  - DiamondSnapshot 有 `UniqueConstraint(account_id, date)`
  - 所有关系设置了 `cascade="all, delete-orphan"`，但批量操作必须用 ORM `session.delete()` 循环，`query.delete()` 不触发级联
- **schemas.py**：Pydantic 模型，`class_name` 使用 `Field(alias="class")`，AccountResponse 有 `populate_by_name=True`
- **routers/accounts.py**：手机号作为业务唯一标识，Excel 导入按 phone upsert。注意路由顺序：`/accounts/import-excel` 等精确路径必须在 `/accounts/{account_id}` 之前注册
- **routers/records.py**：批量录入收益，Excel 导入按 cloud_device 匹配账户
- **routers/analytics.py**：15+ 查询端点，聚合来自 DiamondRecord 和 DiamondSnapshot 的数据
- **routers/diamonds.py**：钻石同步（按 cloud_device 匹配）、卖出（清零 current_diamonds）、流水查询

### 前端 (`frontend/`)

- **无路由库**：`App.tsx` 通过 `useState('accounts')` 切换页面，Layout 组件接收 `active` + `onNavigate`
- **UI 组件**：基于 `@base-ui/react`（非 Radix），封装在 `src/components/ui/`。Select 的 `onValueChange` 签名是 `(value: string | null) => void`，不能直接传 state setter
- **无 Drawer/Checkbox 组件**：抽屉是手工的 `fixed top-0 right-0` 面板 + `bg-black/30` 遮罩；复选框是原生 `<input type="checkbox">`
- **样式**：Tailwind CSS v4 + `cn()` 工具函数（clsx + tailwind-merge）
- **图表**：recharts
- **Excel**：前端用 xlsx 库解析/生成，后端用 openpyxl
- **Vite 代理**：`/api` → `http://127.0.0.1:8000`，`allowedHosts` 配置了生产域名

### 数据流

1. 外部系统通过 `POST /api/diamonds/sync`（cloud_device + diamonds）同步每日钻石
2. 同步时自动计算 change（当日 diamonds - 昨日快照），upsert 到 diamond_snapshots
3. 用户在账号管理页选中账户 → "卖出钻石" → current_diamonds 清0 → 记录 DiamondSale
4. 收益看板的"钻石日变化趋势"聚合 diamond_snapshots.change 按日期展示

## 重要细节

- `main` 区域的 `overflow-auto` 会裁剪表格内绝对定位的下拉框
- 月度趋势使用 `fromisocalendar` 将 ISO 周字符串转为日期，因为 `"2026-W18"` 不能被 Pydantic `date` 类型解析
- React hooks 不能在 `array.map()` 回调内直接使用 `useState`，需改为外部 `Record<number, State>` 模式

## 匹配规则

| 操作 | 匹配字段 |
|------|----------|
| 账号 Excel 导入 upsert | `phone` |
| 收益 Excel 导入 | `cloud_device` |
| 钻石同步 API | `cloud_device` |
| 账号新增唯一校验 | `phone` |

## 文档目录

| 文件 | 何时查阅 |
|------|----------|
| `docs/database-models.md` | 了解/修改 4 张数据表的字段、类型、约束、关系 |
| `docs/api-reference.md` | 查找 API 端点（路径、参数、请求体、响应格式） |
| `docs/frontend-features.md` | 了解前端 5 个页面的功能布局、组件结构、数据流 |

