import asyncio
import json
from datetime import datetime
from queue import Queue

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user, resolve_access_user
from app.models.entities import ChatSession, User
from app.schemas import ChatSend
from app.services import agent_graph

router = APIRouter(prefix="/chat", tags=["课程助手"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(
    payload: ChatSend,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session: ChatSession | None = None
    if payload.session_id:
        session = db.get(ChatSession, payload.session_id)
    if session is None or session.user_id != me.id:
        session = ChatSession(user_id=me.id, title=payload.message[:24] or "新的对话")
        db.add(session)
        db.commit()
        db.refresh(session)

    history = list(session.history or [])
    history.append({"role": "user", "content": payload.message})
    pending = None
    for m in reversed(history):
        if m.get("role") == "assistant" and isinstance(m.get("pending_plan"), dict):
            pending = m["pending_plan"]
            break

    # 越权防护：普通用户只能以自己身份查询他人数据将被拒绝
    target = resolve_access_user(db, me, payload.username).username

    async def gen():
        yield _sse({"type": "session", "content": session.id})
        q: Queue = Queue()

        def worker():
            try:
                for ev in agent_graph.run_stream(
                    payload.message, target, history, pending, is_admin=(me.role == "admin")
                ):
                    q.put(ev)
            except Exception as exc:  # noqa: BLE001
                q.put({"type": "error", "content": str(exc)})
            finally:
                q.put(None)

        import threading

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        full: list[str] = []
        new_pending = None
        loops = 0
        while loops < 2000:
            loops += 1
            await asyncio.sleep(0)
            try:
                ev = q.get_nowait()
            except Exception:
                await asyncio.sleep(0.05)
                continue
            if ev is None:
                break
            if ev["type"] == "delta":
                full.append(ev["content"])
            if ev["type"] == "done":
                new_pending = ev.get("pending_plan")
            yield _sse(ev)
        answer = "".join(full) if full else ""
        if answer or new_pending:
            db2: Session = SessionLocal()
            try:
                s2 = db2.get(ChatSession, session.id)
                h = list(s2.history or [])
                h.append({"role": "user", "content": payload.message})
                h.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "pending_plan": new_pending,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                s2.history = h[-40:]
                db2.commit()
            finally:
                db2.close()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    rows = db.scalars(select(ChatSession).where(ChatSession.user_id == me.id).order_by(ChatSession.id.desc()))
    return [
        {"id": r.id, "title": r.title, "created_at": str(r.created_at), "count": len(r.history or [])}
        for r in rows
    ]


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    s = db.get(ChatSession, session_id)
    if not s or s.user_id != me.id:
        return {"id": 0, "title": "", "history": []}
    return {"id": s.id, "title": s.title, "history": s.history}


@router.post("/sessions")
def new_session(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    s = ChatSession(user_id=me.id, title="新的对话", history=[])
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "title": s.title}


@router.delete("/sessions/{session_id}")
def del_session(session_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    s = db.get(ChatSession, session_id)
    if s and s.user_id == me.id:
        db.delete(s)
        db.commit()
        return {"ok": True}
    return {"ok": False}
