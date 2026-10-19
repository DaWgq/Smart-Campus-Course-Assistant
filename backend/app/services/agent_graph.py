"""LangGraph 课程助手智能体：意图路由 -> RAG 检索 -> 工具调用 -> LLM 生成。

对外暴露 run_stream() 生成器，事件类型：
  {"type": "step",   "content": "正在调用工具 get_today_schedule ..."}
  {"type": "plan",   "content": {...}}          # 生成的计划草稿
  {"type": "delta",  "content": "..."}           # LLM 流式增量
  {"type": "done",   "content": "最终完整回复"}
  {"type": "error",  "content": "错误信息"}
"""
from __future__ import annotations

import json
import re
from collections.abc import Generator

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing import Annotated, TypedDict

from app.core.config import settings
from app.services import rag_service
from app.services.llm import build_messages, get_llm
from app.services.mcp_server import build_tool_map

TOOLS = build_tool_map()
if not TOOLS:
    # 启动即失败优于运行时静默降级：工具表为空会让所有请求报「工具不存在」
    raise RuntimeError("FastMCP 工具注册表为空，agent 无法工作，请检查 mcp_server.py")

SYSTEM = """你是「校园课程智能助手」，一个面向大学生的课程服务 Agent。
你可以完成三类任务：
1. 查询课表（今天/本周，可指定用户）。
2. 检索课程资料与复习重点（基于 RAG 课程资料库）。
3. 制定预习或复习学习计划；用户回复「保存」时入库。
回答使用简体中文，条理清晰，可用 Markdown 列表；所有课表、课程、计划信息必须来自工具返回或检索结果，不要编造未检索到的信息。
重要：工具返回「查询成功但记录数为 0」表示该用户确实没有相关数据，这是正常结果，
必须如实告知用户，绝不能描述为「工具调用失败」「暂时无法获取」或编造内容。"""

PLAN_SYSTEM = """你是学习计划专家。基于用户请求和课程资料，输出一个学习计划。
严格输出 JSON，字段：{"title": str, "plan_type": "预习计划"|"复习计划", "items": [str, ...]}
items 为 3-6 条可执行的中文任务条目，每条包含阶段与预计时长。"""

SAVE_KEYWORDS = ("保存", "确认保存", "保存计划", "帮我保存", "存一下")

PLAN_KEYWORDS = ("计划", "预习", "复习", "安排")

# 查询已保存计划（只读列表），需排在生成计划之前判断
PLAN_LIST_KEYWORDS = ("有哪些计划", "有什么计划", "我的计划", "学习计划列表", "已保存的计划",
                      "看计划", "查看计划", "列出计划", "计划列表", "查计划", "有哪些学习计划")

# 生成计划的动词信号：只有出现这些才认为用户要「新建」计划
PLAN_GEN_VERBS = ("生成", "制定", "做一份", "写一份", "安排一份", "帮我生成", "整理一份",
                  "来一份", "规划", "设计")

SCHEDULE_KEYWORDS = ("课表", "课程表", "今天有什么课", "查下用户", "周课表", "今天上什么")
MATERIAL_KEYWORDS = ("资料", "讲义", "重点", "考纲", "考点", "教材", "复习重点", "实验")
COURSE_KEYWORDS = ("课程", "这门课", "什么课")


def _wants_plan_list(q: str) -> bool:
    if any(k in q for k in PLAN_LIST_KEYWORDS):
        return True
    # 「(我的|已保存的?)学习计划 + (有哪些|是什么|有哪些?)」这类疑问句
    return bool(re.search(r"(我的|已保存的?)?(学习)?计划.{0,4}(有哪些|有什么|有哪几|是什么|列一下|看一下|吗)", q))


def _wants_plan_generation(q: str) -> bool:
    if not any(k in q for k in PLAN_KEYWORDS):
        return False
    if _wants_plan_list(q):
        return False
    # 出现明确生成动词，或书名号指定课程 + 计划/预习/复习
    return any(v in q for v in PLAN_GEN_VERBS) or bool(re.search(r"[《【]", q))


class AgentState(TypedDict):
    username: str
    query: str
    history: list
    tool_name: str
    tool_args: dict
    tool_result: str
    plan_draft: dict
    pending_plan: dict | None
    answer: str
    is_admin: bool


def _target_user(query: str, fallback: str, is_admin: bool = False) -> str:
    """解析目标用户名。

    安全约束：普通用户的对话文本中即使出现「用户 xxx」也不允许切换查询对象，
    一律回落为已通过鉴权的 fallback；仅管理员可在文本中指定他人。
    """
    if not is_admin:
        return fallback
    m = re.search(r"用户\s*([A-Za-z0-9_]+)", query)
    return m.group(1) if m else fallback


def _cross_user_request(query: str, me: str, is_admin: bool) -> str | None:
    """检测越权查询意图：普通用户在对话中点名他人时返回被点名者，否则 None。"""
    if is_admin:
        return None
    m = re.search(r"用户\s*([A-Za-z0-9_]+)", query)
    if not m:
        return None
    name = m.group(1)
    return name if name != me else None


def _clean_course(query: str) -> str:
    """提取检索用的课程关键词：优先取书名号内容，其次取查询主干。"""
    m = re.search(r"[《【]([^》】]+)[》】]", query)
    if m:
        return m.group(1)
    cleaned = re.sub(r"帮我|请|一下|的|课程|资料|讲义|重点|考点|复习|预习|计划|生成|整理|查询|查一下|查下|看看", "", query)
    return (cleaned.strip() or query)[:20]


def _describe_tool_result(name: str, raw: str) -> str:
    """把工具返回的 JSON 转成明确的中文描述。

    关键点：区分「查询成功但结果为空」与「工具调用失败」，
    避免大模型把正常的空结果误判为调用异常。
    """
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        return f"工具 `{name}` 返回原始内容：\n{raw}"

    if not isinstance(data, dict):
        return f"工具 `{name}` 返回：\n{raw}"

    if data.get("ok") is False:
        return f"工具 `{name}` 执行失败：{data.get('message', '未知错误')}。请如实告知用户失败原因。"

    lines = []

    if name in ("get_today_schedule", "get_weekly_schedule"):
        user = data.get("username", "")
        scope = "今天" if name == "get_today_schedule" else "本周"
        courses = data.get("courses", [])
        if not courses:
            lines.append(f"查询成功（工具正常工作）。用户 `{user}` 的{scope}课表查询结果为 0 条记录。")
            lines.append(f"数据库中该用户在{scope}确实没有任何课程安排。这是真实的空数据，不是查询失败。")
            lines.append(f"请如实告诉用户：用户 {user} 当前没有已录入的课程，请他先在课表中导入或确认账号是否正确；不要编造课程，也不要说工具调用失败。")
        else:
            title = "今日课程" if name == "get_today_schedule" else "本周课表"
            lines.append(f"查询成功。用户 `{user}` 的{scope}共有 {len(courses)} 门课程：")
            for c in courses:
                if name == "get_today_schedule":
                    lines.append(
                        f"- 第{c['slot']}节 {c['time']} 《{c['name']}》 任课教师 {c['teacher']}，地点 {c['room']}，{c['weeks']}"
                    )
                else:
                    lines.append(
                        f"- {c['weekday']} 第{c['slot']}节 {c['time']} 《{c['name']}》 教师 {c['teacher']}，地点 {c['room']}"
                    )
            lines.append("请基于以上真实记录回答用户。")

    elif name == "list_study_plans":
        plans = data.get("plans", [])
        if not plans:
            lines.append("查询成功（工具正常工作）。该用户的学习计划列表为 0 条，属于真实的空数据。")
            lines.append("请如实告知用户暂无已保存的学习计划，并提示可以让我生成一份。不要说工具调用失败。")
        else:
            lines.append(f"查询成功，共 {len(plans)} 份学习计划：")
            for p in plans:
                lines.append(f"- 《{p['title']}》 [{p['plan_type']}] {p['status']}，共 {len(p['items'])} 个条目")
            lines.append("请基于以上真实记录回答用户。")

    elif name == "search_course_materials":
        chunks = data.get("chunks", [])
        avail = data.get("available_courses", [])
        if data.get("matched") is False:
            lines.append(
                f"查询成功。资料库中未找到名为《{data.get('requested', '')}》的课程，"
                "属于课程名不匹配（不是工具调用失败）。"
            )
            if avail:
                lines.append("资料库当前可用的课程有：")
                lines.append("、".join(f"《{c}》" for c in avail))
            lines.append("请如实告知用户该课程尚未接入资料库，并列出上述可选课程供其确认，不要编造该课程的资料内容。")
        else:
            lines.append(
                f"查询成功。课程《{data.get('course', '')}》（{data.get('code', '')}）检索到 {len(chunks)} 条相关资料片段。"
            )
            if data.get("docs"):
                lines.append(f"教材与实验资料：{data['docs']}")
            if data.get("focus"):
                lines.append(f"核心考点：{data['focus']}")
            if chunks:
                lines.append("检索片段：")
                for i, ch in enumerate(chunks[:4], 1):
                    lines.append(f"  [{i}] {ch['content']}")
            lines.append("请严格基于以上检索结果回答，不要补充未检索到的信息。")

    elif name == "list_course_materials":
        courses = data.get("courses", [])
        lines.append(f"查询成功，资料库共 {len(courses)} 门课程：")
        for c in courses:
            lines.append(f"- 《{c['course']}》（{c['code']}）")
        lines.append("请基于以上真实列表回答。")

    elif name == "list_users":
        users = data.get("users", [])
        lines.append(f"查询成功，系统内共有 {len(users)} 个账号：")
        for u in users:
            lines.append(f"- {u['username']}（{u['nickname']}，{u.get('major') or '未填写专业'}）")
        lines.append("请基于以上真实列表回答。")

    else:
        lines.append(f"工具 `{name}` 返回：{raw}")

    return "\n".join(lines)


def _parse_plan_json(raw: str) -> dict | None:
    """从模型输出中提取计划 JSON，解析失败返回 None（不伪造任何数据）。"""
    text = (raw or "").strip()
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except Exception:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list) or not data["items"]:
        return None
    items = [str(x).strip() for x in data["items"] if str(x).strip()]
    if not items:
        return None
    title = str(data.get("title") or "").strip()
    if not title:
        return None
    plan_type = str(data.get("plan_type") or "").strip()
    if plan_type not in ("预习计划", "复习计划"):
        plan_type = "预习计划" if "预习" in title else "复习计划"
    return {"title": title, "plan_type": plan_type, "items": items}


def route_node(state: AgentState) -> AgentState:
    q = state["query"].strip()
    # username 由路由层传入（当前登录用户）；查询文本中若显式提到其他用户名则以文本为准
    state["username"] = _target_user(q, state.get("username") or "", bool(state.get("is_admin")))

    if any(k in q for k in SAVE_KEYWORDS) and state.get("pending_plan"):
        state["tool_name"] = "save_study_plan"
        state["plan_draft"] = state["pending_plan"]
        state["tool_args"] = {
            "username": state["username"],
            "title": state["pending_plan"].get("title", "学习计划"),
            "plan_type": state["pending_plan"].get("plan_type", "复习计划"),
            "items": state["pending_plan"].get("items", []),
        }
        return state

    if any(k in q for k in SCHEDULE_KEYWORDS):
        state["tool_name"] = "get_today_schedule" if "周" not in q else "get_weekly_schedule"
        state["tool_args"] = {"username": state["username"]}
        return state

    if _wants_plan_list(q):
        state["tool_name"] = "list_study_plans"
        state["tool_args"] = {"username": state["username"]}
        return state

    if any(k in q for k in MATERIAL_KEYWORDS):
        state["tool_name"] = "search_course_materials"
        state["tool_args"] = {"course": _clean_course(q), "question": q}
        return state

    if _wants_plan_generation(q):
        state["tool_name"] = "generate_plan"
        state["tool_args"] = {"query": q, "course": _clean_course(q)}
        return state

    state["tool_name"] = "answer"
    state["tool_args"] = {"query": q}
    return state


def tool_node(state: AgentState) -> AgentState:
    name = state["tool_name"]
    if name == "generate_plan":
        chunks = rag_service.search(f"{state['tool_args']['course']} 重点 考点", top_k=3)
        ctx = rag_service.format_context(chunks)
        llm = get_llm()
        msgs = build_messages(
            PLAN_SYSTEM + (f"\n\n可参考资料：\n{ctx}" if ctx else ""),
            [],
            state["query"],
        )
        raw = (llm.invoke(msgs).content or "").strip()
        data = _parse_plan_json(raw)
        if not data:
            retry = llm.invoke(
                build_messages(
                    PLAN_SYSTEM + "\n\n重要：只输出 JSON 对象本身，禁止解释文字与 markdown 代码块标记。",
                    [],
                    state["query"],
                )
            )
            data = _parse_plan_json((retry.content or "").strip())
        if not data:
            state["plan_draft"] = {}
            state["pending_plan"] = None
            state["tool_result"] = ""
            raise ValueError("模型未能返回合法计划 JSON，请稍后重试")
        state["plan_draft"] = data
        state["pending_plan"] = data
        state["tool_result"] = json.dumps(data, ensure_ascii=False)
        return state

    fn = TOOLS.get(name)
    if fn is None:
        state["tool_result"] = json.dumps({"ok": False, "message": "工具不存在"}, ensure_ascii=False)
        return state
    state["tool_result"] = fn(**state["tool_args"])
    return state


def generate_node(state: AgentState, stream: bool = False) -> Generator[AgentState | None, None, None]:
    name = state["tool_name"]
    llm: ChatOpenAI = get_llm()
    result = state.get("tool_result", "")

    if name == "save_study_plan":
        title = (state.get("plan_draft") or {}).get("title") or state["tool_args"].get("title") or "学习计划"
        try:
            res = json.loads(result) if result else {}
        except Exception:
            res = {}
        if res.get("ok") is False:
            yield {**state, "answer": f"❌ 保存失败：{res.get('message', '未知错误')}"}
            return
        disp = title if title.startswith(("《", "「", "\"")) else f"《{title}》"
        msg = (
            f"✅ 学习计划已成功保存！\n\n已将{disp}"
            f"写入用户 `{state['username']}` 的学习计划库。\n\n"
            "你可以前往「学习计划」页面查看，或继续让我生成新的计划。"
        )
        yield {**state, "answer": msg}
        return

    if name == "generate_plan":
        d = state["plan_draft"]
        items = "\n".join(f"{i}. {x}" for i, x in enumerate(d["items"], 1))
        prompt = (
            f"用户 {state['username']} 的请求：{state['query']}\n\n"
            f"已生成计划草稿：\n《{d['title']}》（{d['plan_type']}，适用用户：{state['username']}）\n{items}\n\n"
            "请用中文自然语言向用户介绍这份计划草稿，并提示其回复「保存」以入库。"
            "不要输出 JSON。"
        )
    elif name == "answer":
        prompt = state["tool_args"]["query"]
    else:
        prompt = (
            f"用户请求：{state['query']}\n\n"
            f"【工具 `{name}` 的查询结果】\n{_describe_tool_result(name, result)}\n\n"
            "请基于以上真实查询结果，用中文清晰作答。"
            "注意：查询结果为 0 条属于正常情况（表示该用户确实没有相关记录），"
            "请如实告知用户，绝不能把空结果描述为「工具调用失败」或编造不存在的数据。"
        )

    messages = build_messages(SYSTEM, state.get("history", []), prompt)
    if not stream:
        resp = llm.invoke(messages)
        text = (resp.content or "").strip()
        yield {**state, "answer": text}
        return

    buf = []
    for chunk in llm.stream(messages):
        piece = chunk.content or ""
        if piece:
            buf.append(piece)
            yield {"delta": piece}
    yield {**state, "answer": "".join(buf).strip()}


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("route", route_node)
    g.add_node("tool", tool_node)
    g.add_node("generate", generate_node)
    g.add_edge(START, "route")
    g.add_edge("route", "tool")
    g.add_edge("tool", "generate")
    g.add_edge("generate", END)
    return g.compile()


GRAPH = build_graph()


def run_stream(
    query: str,
    username: str,
    history: list,
    pending_plan: dict | None,
    is_admin: bool = False,
) -> Generator[dict, None, None]:
    state: AgentState = {
        "username": username,
        "query": query,
        "history": history or [],
        "tool_name": "",
        "tool_args": {},
        "tool_result": "",
        "plan_draft": {},
        "pending_plan": pending_plan,
        "answer": "",
        "is_admin": is_admin,
    }

    # 越权防护：普通用户在对话中点名他人时，直接拒绝，不调用任何工具
    blocked = _cross_user_request(query, username, is_admin)
    if blocked:
        msg = (
            f"⛔ 无权访问：你不能查看其他用户的课表或学习计划。\n\n"
            f"你当前登录的账号是 `{username}`，无权查询用户 `{blocked}` 的数据。"
            "课程助手只会为你本人提供课表、资料与学习计划服务。"
        )
        yield {"type": "step", "content": "已拦截越权请求"}
        yield {"type": "done", "answer": msg, "pending_plan": None}
        return

    try:
        state = route_node(state)
        tool_name = state.get("tool_name")
        yield {"type": "step", "content": "正在理解您的请求..."}
        state = tool_node(state)
        if tool_name and tool_name != "answer":
            yield {"type": "step", "content": f"已调用工具 `{tool_name}`"}
        if state.get("plan_draft"):
            yield {"type": "plan", "content": state["plan_draft"]}
        full: list[str] = []
        for item in generate_node(state, stream=True):
            if isinstance(item, dict) and "delta" in item:
                full.append(item["delta"])
                yield {"type": "delta", "content": item["delta"]}
            elif isinstance(item, dict) and "answer" in item:
                state = item
        answer = state.get("answer") or "".join(full)
        yield {"type": "done", "content": answer, "pending_plan": state.get("pending_plan")}
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "content": f"智能体执行失败：{exc}"}


def is_save_intent(query: str) -> bool:
    return any(k in query for k in SAVE_KEYWORDS)


__all__ = ["run_stream", "is_save_intent", "SYSTEM", "settings"]
