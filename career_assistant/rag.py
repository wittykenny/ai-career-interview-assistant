from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm import DashScopeLLM, embedding_api_configured, embed_texts

try:
    from chromadb.errors import ChromaError
except ImportError:
    ChromaError = RuntimeError


COLLECTION_NAME = "interview_bank_v4"

CHROMA_RUNTIME_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    ChromaError,
)


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    content: str


@dataclass(frozen=True)
class RAGAnswer:
    content: str
    sources: list[KnowledgeDocument]
    mode_note: str = ""


class InterviewRAG:
    def __init__(self, persist_dir: str | Path = "chroma_db") -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._documents: list[KnowledgeDocument] = []
        self._client = None
        self._collection = None
        self._mode_note = ""
        self._polish_cache: dict[tuple[str, tuple[str, ...]], RAGAnswer] = {}
        self._setup_chroma()

    def index_documents(self, documents: list[dict[str, str] | KnowledgeDocument]) -> None:
        self._documents = [
            item if isinstance(item, KnowledgeDocument) else KnowledgeDocument(title=item["title"], content=item["content"])
            for item in documents
        ]
        if self._collection is None:
            return
        self._recreate_collection()
        if self._write_collection():
            return
        if self._recreate_collection() and self._write_collection():
            return
        self._collection = None
        self._mode_note = "ChromaDB 索引写入失败，已切换本地关键词检索模式。"

    def answer(self, question: str) -> RAGAnswer:
        sources = self.search(question, top_k=2)
        if not sources:
            return RAGAnswer(content="知识库暂未找到相关内容，请补充面试题库资料。", sources=[], mode_note=self._mode_note)
        return RAGAnswer(content=_compose_fast_answer(question, sources), sources=sources, mode_note=self._mode_note)

    def polish_answer(self, question: str) -> RAGAnswer:
        sources = self.search(question, top_k=2)
        if not sources:
            return RAGAnswer(content="知识库暂未找到相关内容，请补充面试题库资料。", sources=[], mode_note=self._mode_note)
        cache_key = (question.strip(), tuple(source.title for source in sources))
        if cache_key in self._polish_cache:
            return self._polish_cache[cache_key]
        context = "\n".join(f"【{doc.title}】{_clip_text(doc.content, 900)}" for doc in sources)
        prompt = f"请基于以下资料回答求职面试问题，并给出答题技巧。不要引用资料中无关章节。\n资料：{context}\n问题：{question}"
        llm_response = DashScopeLLM().generate(prompt)
        content = llm_response.content
        if llm_response.offline:
            content = (
                f"{_clip_text(sources[0].content, 900)}\n\n"
                "答题建议：使用 STAR 方法，先讲背景和任务，再讲行动与量化结果。"
            )
        answer = RAGAnswer(content=content, sources=sources, mode_note=_join_notes(self._mode_note, llm_response.notice))
        self._polish_cache[cache_key] = answer
        return answer

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeDocument]:
        keyword_ranked = self._keyword_search(query, max(top_k, 4))
        if keyword_ranked and _is_strong_keyword_match(query, keyword_ranked[0]):
            if self._collection is not None:
                self._mode_note = _join_notes(self._mode_note, "已优先使用本地关键词强匹配。")
            return keyword_ranked[:top_k]
        if self._collection is not None:
            try:
                n_results = min(len(self._documents) or top_k, max(top_k, 8))
                result = self._collection.query(query_texts=[query], n_results=n_results)
                documents = result.get("documents") or [[]]
                metadatas = result.get("metadatas") or [[]]
                docs = [
                    KnowledgeDocument(title=metadata.get("title", "未命名资料"), content=content)
                    for content, metadata in zip(documents[0], metadatas[0])
                ]
                if docs:
                    merged = _merge_documents(docs + keyword_ranked)
                    return _rank_by_keyword(query, merged)[:top_k]
            except CHROMA_RUNTIME_ERRORS:
                self._collection = None
                self._mode_note = "ChromaDB 查询失败，已切换本地关键词检索模式。"
        return keyword_ranked[:top_k]

    def _keyword_search(self, query: str, top_k: int) -> list[KnowledgeDocument]:
        scored = [(_keyword_score(query, doc), doc) for doc in self._documents]
        return [doc for score, doc in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k] if score > 0]

    def _setup_chroma(self) -> None:
        try:
            import chromadb
        except ImportError:
            self._collection = None
            self._mode_note = "未安装 ChromaDB，已切换本地关键词检索模式。"
            return

        if self._connect_chroma(chromadb, self.persist_dir):
            return

        fallback_dir = self.persist_dir.parent / ".runtime_chroma_db"
        if fallback_dir != self.persist_dir and self._connect_chroma(chromadb, fallback_dir):
            self.persist_dir = fallback_dir
            self._mode_note = _join_notes(
                "原 ChromaDB 目录不可写，已切换到新的运行时向量库目录。",
                self._mode_note,
            )
            return

        self._collection = None
        self._mode_note = "ChromaDB 初始化失败，已切换本地关键词检索模式。"

    def _connect_chroma(self, chromadb_module: Any, persist_dir: Path) -> bool:
        try:
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb_module.PersistentClient(path=str(persist_dir))
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=HashEmbeddingFunction(),
            )
            if not embedding_api_configured():
                self._mode_note = "未配置在线向量模型，RAG 已使用本地哈希向量检索；AI 润色会优先调用已配置的在线大模型。"
            return True
        except CHROMA_RUNTIME_ERRORS:
            self._client = None
            self._collection = None
            return False

    def _write_collection(self) -> bool:
        if self._collection is None:
            return False
        try:
            existing = self._collection.get()
            existing_ids = existing.get("ids") or []
            if existing_ids:
                self._collection.delete(ids=existing_ids)
            if not self._documents:
                return True
            self._collection.add(
                ids=[f"doc-{index}" for index in range(len(self._documents))],
                documents=[doc.content for doc in self._documents],
                metadatas=[{"title": doc.title} for doc in self._documents],
            )
            return True
        except CHROMA_RUNTIME_ERRORS:
            return False

    def _recreate_collection(self) -> bool:
        if self._client is None:
            return False
        try:
            try:
                self._client.delete_collection(COLLECTION_NAME)
            except CHROMA_RUNTIME_ERRORS:
                pass
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=HashEmbeddingFunction(),
            )
            return True
        except CHROMA_RUNTIME_ERRORS:
            self._collection = None
            return False


class HashEmbeddingFunction:
    def __init__(self, size: int = 256) -> None:
        self.size = size

    def __call__(self, input: list[str]) -> list[list[float]]:
        online_vectors = embed_texts(input)
        if online_vectors:
            return online_vectors
        return [_hash_embedding(text, self.size) for text in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self.__call__(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self.__call__(input)

    @staticmethod
    def name() -> str:
        return "hash_embedding_fallback_v2"

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "HashEmbeddingFunction":
        return HashEmbeddingFunction(size=int(config.get("size", 64)))

    def get_config(self) -> dict[str, Any]:
        return {"size": self.size}

    def is_legacy(self) -> bool:
        return False

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]

    @staticmethod
    def validate_config(config: dict[str, Any]) -> None:
        size = int(config.get("size", 64))
        if size <= 0:
            raise ValueError("Embedding size must be positive.")


def _hash_embedding(text: str, size: int = 64) -> list[float]:
    vector = [0.0] * size
    for token in _terms(text):
        vector[hash(token) % size] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def parse_interview_bank_markdown(content: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_h1 = ""
    current_title = "面试题库"
    current_lines: list[str] = []

    def flush() -> None:
        text = "\n".join(line for line in current_lines if line.strip()).strip()
        if text:
            sections.append({"title": current_title, "content": text})

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            flush()
            title = line[2:].strip()
            current_h1 = "" if title.startswith("AI求职") else title
            current_title = current_h1 or "面试题库"
            current_lines = []
            continue
        if line.startswith("## "):
            flush()
            subtitle = line[3:].strip()
            current_title = f"{current_h1} / {subtitle}" if current_h1 else subtitle
            current_lines = []
            continue
        current_lines.append(line)

    flush()
    return sections


def _terms(text: str) -> set[str]:
    normalized = text.lower()
    for mark in ["，", "。", "、", "；", "：", ",", ".", ";", ":", "?", "？", "\n", "\t"]:
        normalized = normalized.replace(mark, " ")
    words = {word for word in normalized.split() if word}
    chars = {char for char in normalized if "\u4e00" <= char <= "\u9fff"}
    chinese = "".join(char for char in normalized if "\u4e00" <= char <= "\u9fff")
    bigrams = {chinese[index : index + 2] for index in range(max(0, len(chinese) - 1))}
    trigrams = {chinese[index : index + 3] for index in range(max(0, len(chinese) - 2))}
    return words | chars | bigrams | trigrams


def _keyword_score(query: str, doc: KnowledgeDocument) -> float:
    query_terms = _terms(query)
    doc_text = doc.title + " " + doc.content
    doc_terms = _terms(doc_text)
    overlap = len(query_terms & doc_terms)
    char_overlap = sum(1 for char in set(query) if char.strip() and char in doc_text)
    title_bonus = 6 if any(term and term in doc.title for term in query_terms if len(term) >= 2) else 0
    phrase_bonus = _phrase_match_bonus(query, doc)
    generic_penalty = _generic_section_penalty(query, doc)
    return overlap * 3 + math.sqrt(char_overlap) + title_bonus + phrase_bonus - generic_penalty


def _rank_by_keyword(query: str, docs: list[KnowledgeDocument]) -> list[KnowledgeDocument]:
    scored = [(_keyword_score(query, doc), index, doc) for index, doc in enumerate(docs)]
    return [doc for score, _, doc in sorted(scored, key=lambda item: (item[0], -item[1]), reverse=True)]


def _is_strong_keyword_match(query: str, doc: KnowledgeDocument) -> bool:
    important = _important_phrases(query)
    if not important:
        return False
    doc_text = (doc.title + " " + doc.content).lower()
    matched = sum(1 for phrase in important if phrase.lower() in doc_text)
    return matched >= min(2, len(important)) or (len(important) == 1 and matched == 1)


def _important_phrases(query: str) -> list[str]:
    lowered = query.lower()
    phrases = []
    candidates = [
        "sql",
        "数据分析师",
        "数据分析",
        "产品经理",
        "ai应用开发",
        "rag",
        "prompt",
        "后端开发",
        "金融分析",
        "风控",
        "法务",
        "会计",
        "审计",
        "运营",
        "市场",
    ]
    for phrase in candidates:
        if phrase.lower() in lowered:
            phrases.append(phrase)
    return phrases


def _phrase_match_bonus(query: str, doc: KnowledgeDocument) -> float:
    title = doc.title.lower()
    content = doc.content.lower()
    lowered_query = query.lower()
    bonus = 0.0
    if "sql" in lowered_query and "sql" in title:
        bonus += 80
    if "sql" in lowered_query and "sql 基础题" in title:
        bonus += 70
    if "sql" in lowered_query and "业务题" in doc.title:
        bonus -= 70
    for phrase in _important_phrases(query):
        lowered = phrase.lower()
        if lowered in title:
            bonus += 28
        elif lowered in content:
            bonus += 8
    return bonus


def _generic_section_penalty(query: str, doc: KnowledgeDocument) -> float:
    title = doc.title
    if "追问" in query or "反问" in query:
        return 0
    generic_titles = ["面试官追问", "可以问面试官的问题", "资料来源", "使用说明", "入库建议"]
    return 18 if any(text in title for text in generic_titles) else 0


def _merge_documents(docs: list[KnowledgeDocument]) -> list[KnowledgeDocument]:
    merged: list[KnowledgeDocument] = []
    seen: set[tuple[str, str]] = set()
    for doc in docs:
        key = (doc.title, doc.content)
        if key not in seen:
            seen.add(key)
            merged.append(doc)
    return merged


def _compose_fast_answer(question: str, sources: list[KnowledgeDocument]) -> str:
    primary = sources[0]
    source_lines = "\n".join(f"- {source.title}：{_clip_text(source.content, 240)}" for source in sources)
    return (
        f"问题：{question}\n\n"
        f"快速回答：{_clip_text(primary.content, 900)}\n\n"
        "答题框架：\n"
        "1. 先用一句话给出结论，说明你会如何处理这类问题。\n"
        "2. 再结合一个项目或实习案例，按 STAR 方法说明背景、任务、行动和结果。\n"
        "3. 最后补充工具、指标或复盘动作，让回答更像真实工作经历。\n\n"
        f"参考资料：\n{source_lines}"
    )


def _join_notes(*notes: str) -> str:
    return " ".join(dict.fromkeys(note for note in notes if note))


def _clip_text(text: str, max_length: int) -> str:
    compact = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip("，。；、 \n") + "…"
