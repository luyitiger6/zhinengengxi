# 智能数据库查询系统 - NL2SQL

## ⚙️ 配置区域 (可自行修改)

```yaml
project:
  name: "智能数据库查询系统"
  team: "Xiaxia_luyibaba"
  repo: "luyitiger6/zhinengengxi"
linear:
  in_progress_state_id: "da82104f-eb12-4d2a-bec8-9c4704e8c648"
  done_state_id: "56078fbe-bae1-4200-b50e-5ab1beadcc44"
git:
  remote_url: "git@github.com:luyitiger6/zhinengengxi.git"  # SSH方式
```

## 项目概述
基于大模型的智能数据库查询系统，自然语言转SQL + 可视化图表。

## 技术栈
- 前端: React + ECharts + SSE Client
- 后端: FastAPI + LangChain + LangChain SQLDatabase
- LLM: MiniMax-M2.7-highspeed (via oneapi)
- 数据库: SQLite + Qdrant (向量库)

## 自然语言任务管理

### 状态更新规则（自动触发）
当你提到**任何任务相关**的语义时，自动更新 Linear 状态：

| 你的语义 | Linear 操作 | 说明 |
|----------|-------------|------|
| "开始做T1" / "做xxx功能" / "搞xxx" | 状态 → **In Progress** | 任何表达"开始"的意图 |
| "完成了" / "搞定了" / "搞完了" | 状态 → **Done** | 任何表达"完成"的意图 |
| "领个任务" / "下一个" | 领取下一个 Todo 任务 | 更新为 In Progress |

### 关键规则
- **开始任何任务时**：必须自动更新 Linear 状态为 In Progress
- **完成任何任务时**：必须自动更新 Linear 状态为 Done
- commit message 包含 [PHASE{X}-T{Y}] 标签时，GitHub Actions 自动标 Done

### 任务标识识别
- 显式: T1-T26, [PHASE1-T1], XIA-32
- 语义: "登录功能" → 匹配相关任务 "实现登录"

### 分支命名
`feature/P{phase}-T{task}-{简短描述}`

### Commit 格式
```
[PHASE{X}-T{Y}] <简短描述>
```

## 任务工作流

### Linear 任务管理
- 26个任务分布在 4 个 PHASE
- 每次开发前先从 Linear 领取任务
- 完成后通过 GitHub Actions 自动同步状态

### Commit Message 格式
```
[PHASE{X}-T{Y}] <简短描述>

<可选的详细说明>
```
- X = 1~4 (PHASE编号)
- Y = 任务编号
- 示例: `[PHASE1-T1] 初始化前后端项目结构`

### 任务与Linear ID对应
| PHASE | 任务范围 | Linear ID |
|-------|----------|-----------|
| PHASE 1 | T1-T4 | XIA-32 ~ XIA-35 |
| PHASE 2 | T5-T10 | XIA-36 ~ XIA-41 |
| PHASE 3 | T11-T19 | XIA-42 ~ XIA-50 |
| PHASE 4 | T20-T26 | XIA-51 ~ XIA-57 |

## 代码规范

### 目录结构
```
zhinengengxi/
├── frontend/          # React前端
│   ├── src/
│   └── package.json
├── backend/           # FastAPI后端
│   ├── app/
│   └── requirements.txt
└── CLAUDE.md          # 本文件
```

### 后端规范
- 使用 FastAPI 路由分离业务逻辑
- LangChain chain 用于 NL2SQL 核心逻辑
- SQLDatabase 抽象数据库连接
- 危险SQL必须拦截（DELETE、DROP、TRUNCATE等）

### 前端规范
- 组件化开发
- 三栏布局: 左侧(聊天管理) / 中间(问答) / 右侧(图表)
- SSE 流式响应优先，体验流畅

### API 设计原则
- RESTful 风格
- JSON 格式交互
- 错误信息清晰，返回标准 HTTP 状态码

## 安全要求
- 所有用户输入必须校验
- SQL 查询必须参数化，防止注入
- LLM 输出不可直接执行SQL，需二次校验

## Git 工作流
1. 从 main 创建功能分支: `git checkout -b feature/xxx`
2. 开发完成后 commit (带 [PHASE{X}-T{Y}] 标签)
3. 推送到远程: `git push origin feature/xxx`
4. 合并非直接推送到 main

## 项目仓库
- GitHub: https://github.com/luyitiger6/zhinengengxi
- Linear Team: Xiaxia_luyibaba
