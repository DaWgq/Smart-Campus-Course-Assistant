# 校园课程智能助手（Campus Course Assistant）

根据 `prototype.html` 原型 1:1 还原的完整项目。

## 技术栈

| 端 | 技术 |
|---|---|
| 前端 | Vue 3 + naive-ui + Pinia + Vue Router + Vite + axios + SSE |
| 后端 | Python · FastAPI · SQLAlchemy · JWT · MySQL |
| Agent | FastMCP（工具服务）· LangChain · LangGraph（意图路由→工具调用→生成）· Chroma（RAG）· SSE 流式输出 |
| 模型 | DeepSeek（`deepseek-chat`，OpenAI 兼容接口） |

## 功能（对应原型 4 个视图）

1. **系统首页**：统计卡片（绑定账号 / 今日课程 / 学习计划数 / RAG 资料库）、今日课程 + 资料库速查
2. **我的课表**：按用户（aaa / bbb）切换的周课表网格，点击课程跳转助手查资料
3. **学习计划**：助手里说「保存」后落库的预习/复习计划，支持删除
4. **课程助手**：SSE 流式对话，支持查课表 / 查课程资料（RAG）/ 生成学习计划 / 说「保存」入库

## 目录结构

```
DawgAgent/
├── prototype.html              # 原型图（需求来源）
├── start-backend.bat           # 一键启动后端
├── start-frontend.bat          # 一键启动前端
├── backend/
│   ├── requirements.txt
│   ├── .env.example            # 环境变量模板（复制为 .env 后填写）
│   ├── run_seed.py             # 初始化种子数据 + Chroma 索引
│   └── app/
│       ├── main.py             # FastAPI 入口（CORS / 路由注册 / 自动建库）
│       ├── core/               # config / database / security(JWT) / deps
│       ├── models/entities.py  # users / schedule_items / course_materials / study_plans / chat_sessions
│       ├── schemas.py          # Pydantic 模型
│       ├── routers/            # auth / academic / plans / chat(SSE)
│       └── services/
│           ├── llm.py          # DeepSeek 封装
│           ├── rag_service.py  # Chroma 向量库 + RAG 检索
│           ├── mcp_server.py   # FastMCP 工具（课表/资料/计划/用户）
│           └── agent_graph.py  # LangGraph：route → tool → generate，流式事件
└── frontend/
    ├── package.json / vite.config.ts / tsconfig.json / index.html
    └── src/
        ├── main.ts / App.vue / styles/global.css
        ├── router/             # /login + 布局内 home/schedule/plan/assistant，登录守卫
        ├── api/                # axios 封装 + streamChat(SSE)
        ├── stores/user.ts      # 登录态 + 查询用户 queryUser
        └── views/              # Login / Layout / Home / Schedule / Plan / Assistant
```

## 使用步骤

### 1. 后端

```bat
cd backend
copy .env.example .env
:: 编辑 .env：填写 DEEPSEEK_API_KEY、MySQL 账号密码、SECRET_KEY
python run_seed.py        :: 建库建表 + 写入演示数据 + 同步 Chroma 索引
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- 接口文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health
- 演示账号：`aaa / 123456`（小黑）、`bbb / 123456`（小林）
- FastMCP 工具服务以 in-process 方式被 LangGraph 直接调用（`mcp_server.build_tool_map`），无需单独启动 MCP Server；如需独立暴露可另起 `mcp.run()`。

### 2. 前端

```bat
cd frontend
npm run dev      :: http://localhost:5173
```

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`，前后端联调零跨域。

### 3. 核心链路

```
用户输入 → POST /api/chat/stream (SSE)
        → LangGraph route(意图: 课表/资料/计划/保存/闲聊)
        → tool( FastMCP 工具: 查 MySQL / 检索 Chroma RAG / 生成计划 )
        → generate( DeepSeek 生成自然语言回复, 流式 delta )
        → 前端逐字渲染 Markdown；计划草稿随 plan 事件下发，说「保存」即入库
```

## 说明

- **版本对齐**：`fastapi>=0.144`（匹配 starlette 1.x；旧版 0.115 会报 `Router.__init__() got an unexpected keyword argument 'on_startup'`）、`fastmcp>=2.0`（3.x/4.x 走公开 `list_tools()`，2.x 走 `_tool_manager` 兜底）、`bcrypt>=4.1`（弃用 passlib）。
- RAG embedding 默认使用离线确定性 hash embedding（无需联网即可跑通全链路）；生产环境可将 `rag_service._EmbeddingAdapter` 替换为 BGE/OpenAI embedding。
- DeepSeek 未配置 key 时，对话接口会返回错误事件，前端会显示提示；课表/计划/资料等 REST 接口不受影响。
- MySQL 需提前启动并允许 root 建库（`ensure_database` 会自动 `CREATE DATABASE IF NOT EXISTS`）。
- 启动方式：`uvicorn app.main:app --reload`、`fastapi dev`、`python -m uvicorn ...` 均可。
