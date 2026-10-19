"""Chroma 向量库 + LangChain RAG 检索服务。"""
from __future__ import annotations

import threading

import chromadb
from langchain_core.documents import Document
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings

_lock = threading.Lock()
_client = None
_collection = None


class _EmbeddingAdapter:
    """DeepSeek 未提供 embedding，使用轻量本地确定性 hash embedding（离线可用）。

    生产环境可替换为 BGE / OpenAI embedding，只需替换本类实现。
    """

    def __init__(self) -> None:
        self.dim = 512

    def __call__(self, text: str) -> list[float]:
        import hashlib
        import math
        import re

        vec = [0.0] * self.dim
        tokens: list[str] = []
        for word in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", str(text)):
            tokens.append(word)
        chars = [t for t in tokens if len(t) == 1 and ord(t) >= 0x4E00]
        for i in range(len(chars) - 1):
            tokens.append(chars[i] + chars[i + 1])
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self(text)


embedding = _EmbeddingAdapter()


def _get_collection():
    global _client, _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                _client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
                _collection = _client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION,
                    metadata={"hnsw:space": "cosine"},
                )
    return _collection


def build_documents(db: Session) -> list[Document]:
    from app.models.entities import CourseMaterial

    mats = db.scalars(select(CourseMaterial)).all()
    docs: list[Document] = []
    for m in mats:
        docs.append(
            Document(
                page_content=f"课程《{m.course}》课程代码 {m.code}。教材与实验资料：{m.docs}",
                metadata={"course": m.course, "code": m.code, "field": "docs"},
            )
        )
        docs.append(
            Document(
                page_content=f"课程《{m.course}》（{m.code}）核心考点与复习重点：{m.focus}",
                metadata={"course": m.course, "code": m.code, "field": "focus"},
            )
        )
    return docs


def sync_index(db: Session) -> int:
    """将 MySQL 中的课程资料全量同步进 Chroma。"""
    global _sig_cache
    coll = _get_collection()
    docs = build_documents(db)
    if not docs:
        return 0
    try:
        existing_ids = coll.get(limit=10000).get("ids") or []
        if existing_ids:
            coll.delete(ids=existing_ids)
    except Exception:
        global _collection
        try:
            _client.delete_collection(settings.CHROMA_COLLECTION)
        except Exception:
            pass
        _collection = None
        coll = _get_collection()
    coll.upsert(
        ids=[f"{d.metadata['course']}::{d.metadata['field']}" for d in docs],
        documents=[d.page_content for d in docs],
        embeddings=[embedding(d.page_content) for d in docs],
        metadatas=[d.metadata for d in docs],
    )
    _sig_cache = None  # 失效缓存，下次 search 会重新计算签名
    return len(docs)


def _index_signature() -> str:
    """库中资料内容的指纹，用于判断向量索引是否过期。"""
    import hashlib

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        docs = build_documents(db)
    finally:
        db.close()
    blob = "\n".join(f"{d.metadata['course']}::{d.metadata['field']}::{d.page_content}" for d in docs)
    return f"{len(docs)}:{hashlib.md5(blob.encode('utf-8')).hexdigest()}"


_sig_cache: str | None = None


def ensure_fresh() -> bool:
    """确保向量索引与数据库一致；不一致时自动重建。

    避免用户在 Navicat 手动导入/修改课程资料后，助手检索到过期或空结果。
    """
    global _sig_cache
    from app.core.database import SessionLocal

    coll = _get_collection()
    try:
        sig = _index_signature()
    except Exception:
        return False
    if sig == _sig_cache and coll.count() > 0:
        return False
    db = SessionLocal()
    try:
        n = sync_index(db)
    finally:
        db.close()
    _sig_cache = sig
    if n:
        print(f"rag: 检测到资料变更，已自动重建索引（{n} 条）")
    return True


def search(query: str, top_k: int = 4) -> list[dict]:
    ensure_fresh()
    coll = _get_collection()
    if coll.count() == 0:
        return []
    res = coll.query(
        query_embeddings=[embedding(query)],
        n_results=min(top_k, coll.count()),
        include=["documents", "metadatas"],
    )
    out = []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    for text, meta in zip(docs, metas):
        out.append({"content": text, "metadata": meta})
    return out


def format_context(chunks: list[dict]) -> str:
    return "\n\n".join(f"[资料{i+1}] {c['content']}" for i, c in enumerate(chunks))
