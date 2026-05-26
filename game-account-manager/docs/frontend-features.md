# 前端功能文档

## 技术栈

React 19 + TypeScript + Vite 8 + Tailwind CSS v4 + recharts + SheetJS (xlsx)。UI 组件基于 `@base-ui/react`（非 Radix），封装在 `src/components/ui/`。

## 路由与导航

**无路由库**。`App.tsx` 通过 `useState('accounts')` 切换页面。`Layout` 组件提供左侧 56px 宽侧边栏，接收 `active` + `onNavigate` props。

导航项（5 项）：

| 序号 | key | 标签 | 图标 |
|------|-----|------|------|
| 1 | accounts | 账号管理 | Users |
| 2 | records | 收益录入 | FileText |
| 3 | analytics | 收益看板 | BarChart3 |
| 4 | diamond | 钻石流水 | Gem |
| 5 | analysis | 分析看板 | TrendingUp |

## 页面 1：账号管理 (AccountsPage)

**Tab 1 — 账号列表：**
- 搜索框（手机号/账号名模糊匹配） + "更多筛选"折叠面板（区服 Select、大区 Select、邮箱 Input、职业 Input、云机 Input）
- 工具栏按钮：`同步钻石`（打开 JSON 输入 Dialog）、`卖出钻石`（选中后确认即清0）、`批量删除`、`新增账号`
- 表格列：复选框、手机号（点击打开收益抽屉）、当前钻石、云机名、账户名、区服、职业、操作（编辑/删除）
- **收益记录抽屉**：右侧 96px 面板，展示日期/地点/数量 + 合计行
- **同步钻石 Dialog**（两步）：粘贴 JSON → 「校验并预览」→ 预览表格（云机名称、匹配账户、当前钻石、更新为、变化、提醒）→ 「确认同步」。数量低于当前钻石或超过 2000 时琥珀色警告提醒。

**Tab 2 — Excel 批量导入：**
- 文件上传区域 + 模板格式说明 + 下载模板按钮
- 预览表格标注新增（绿色）/覆盖更新（黄色）/无手机号（红色）
- 按 phone upsert

**表单 (AccountForm Dialog)：**
- 11 个字段：account_name、phone、cloud_device 必填（红色星号），其余选填
- 新增/编辑共用，通过 `editing` 状态区分

## 页面 2：收益录入 (RecordsPage)

**日期选择器**：页面顶部蓝色背景栏。

**Tab 1 — Excel 批量导入：**
- 文件上传 → 按云机名称匹配账户 → 预览表格（匹配/未匹配/收益/地点）
- 缺省地点输入框（Excel 中地点为空时使用）
- 下载模板（含所有账户的云机名称和地点）

**Tab 2 — 手动录入（两种模式切换）：**
- **单账户录入**：grid 布局行，每行独立搜索选择账户（下拉搜索：账户名/云机名/手机号模糊匹配）、地点 Input、收益 Input、删除按钮（多行时），"添加一条"追加新行
- **整体录入**：Table 列出全部账户，每行地点 + 收益 Input
- 提交收益按钮

## 页面 3：收益看板 (AnalyticsPage)

**5 个概览卡片**：总收益、环比变化（绿涨红跌）、同比变化、最高产出地、录入次数

**钻石日变化趋势**：`OverallTrend` 组件 → `/api/analytics/diamond-trend`，recharts LineChart。数据来源包括同步卖出型账户的 daily change 和直接录入收益型账户的间隙均分，精确到每天的生产增量。

**按地点收益分布**：PieChart，点击扇形下钻到该地点趋势（LineChart）

**每周收益趋势**：BarChart（紫色）

**收益日历热力图**：12 个月手工 CSS Grid，每天 3px 方块，蓝色透明度表示收益高低

**账号收益排行 Top 15**：Table + 批次 Select + "查看全部"按钮
- "查看全部"打开右侧抽屉，含升降序切换

**按区服/职业收益**：各一个 BarChart，独立批次 Select

## 页面 4：钻石流水 (DiamondPage)

- 日期范围筛选（开始/结束 date Input + 查询按钮）
- 卖出记录 Table：日期、账号名、云机、手机号、卖出数量（amber 色）、记录时间
- 底部统计：总记录数 + 合计卖出钻石数

## 页面 5：分析看板 (AnalysisPage)

**需关注账户**：收益低于均值 X% 的账户（批次 Select + 阈值 Select：10%~90%）
- Table：账号名（点击打开收益抽屉）、云机、收益、均值、占比
- 右侧抽屉展示该账户收益明细

**单账户 vs 全体均值**：
- 搜索框（模糊匹配账户名/云机/手机号，带下拉自动补全）
- 左：LineChart（账号收益蓝色实线 vs 全体均值琥珀色虚线）
- 右：收益明细表（日期、收益、均值、环比），按时间倒序

## 通用组件

| 组件 | 说明 |
|------|------|
| `Button` | 7 种 variant（default/outline/secondary/ghost/destructive/link）+ 6 种 size |
| `Dialog` | 弹窗，含 overlay + 标题 + 内容 + 页脚 |
| `Select` | 下拉选择，`onValueChange` 签名 `(value: string \| null) => void` |
| `Table` | 原生 `<table>`，含 header/body/row/head/cell |
| `Tabs` | 标签页，支持 horizontal/vertical 方向 |
| `Input` | 文本/数字/日期输入 |
| `Card` | 卡片容器，含 header/title/content/footer |

**无** Drawer 组件：抽屉为手工 `fixed top-0 right-0 h-full w-96` + `bg-black/30` 遮罩。
**无** Checkbox 组件：直接使用 `<input type="checkbox">`。

## 数据流

1. 所有 API 调用集中在 `api.ts`，页面通过 `useEffect` + `useState` 管理数据
2. 无全局状态管理库，状态通过 props 向下传递
3. 页面切换时组件销毁重建（非 keep-alive），每次切换重新请求数据
4. Excel 文件前端用 xlsx 库解析预览，后端用 openpyxl 最终处理导入

## 模式与约束

- Select `onValueChange` 不能直接传 `useState` setter（类型 `string | null` vs `string`），需包装：`(v) => setXxx(v ?? 'all')`
- `<main className="overflow-auto">` 会裁剪 table 内 `absolute` 定位的下拉框
- React hooks 不能在 `array.map()` 回调内使用，需外部 `Record<number, State>` 模式
- `@` 路径别名映射 `./src`，通过 Vite resolve.alias 配置
