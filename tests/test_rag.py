import warnings
from pathlib import Path

from career_assistant.llm import DashScopeLLM
from career_assistant.rag import InterviewRAG, KnowledgeDocument, parse_interview_bank_markdown


def test_chroma_embedding_function_is_not_legacy(tmp_path):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        InterviewRAG(persist_dir=tmp_path / "chroma")

    messages = [str(item.message) for item in caught]
    assert not any("legacy embedding function config" in message for message in messages)


def test_rag_returns_answer_with_sources(tmp_path):
    rag = InterviewRAG(persist_dir=tmp_path / "chroma")
    rag.index_documents(
        [
            {
                "title": "产品经理行为面试",
                "content": "产品经理面试常问用户需求分析、优先级排序和跨部门沟通，可以使用STAR方法回答。",
            },
            {
                "title": "数据分析师SQL面试",
                "content": "数据分析师常考SQL JOIN、窗口函数、指标口径和异常分析。",
            },
        ]
    )

    answer = rag.answer("产品经理如何回答用户需求分析题？")

    assert "STAR" in answer.content or "需求" in answer.content
    assert answer.sources
    assert answer.sources[0].title == "产品经理行为面试"


def test_rag_reindex_removes_stale_documents(tmp_path):
    rag = InterviewRAG(persist_dir=tmp_path / "chroma")
    rag.index_documents(
        [
            {"title": "旧数据分析题", "content": "旧资料包含SQL和窗口函数。"},
            {"title": "旧金融题", "content": "旧资料包含估值和风险。"},
        ]
    )
    rag.index_documents([{"title": "新AI题", "content": "新资料包含RAG和工具调用。"}])

    sources = rag.search("金融估值风险", top_k=5)

    assert "旧金融题" not in [source.title for source in sources]


def test_rag_fast_answer_does_not_call_llm_by_default(tmp_path, monkeypatch):
    class FailingLLM:
        def generate(self, prompt: str, system: str = ""):
            raise AssertionError("default RAG answer should not call LLM")

    monkeypatch.setattr("career_assistant.rag.DashScopeLLM", lambda: FailingLLM())
    rag = InterviewRAG(persist_dir=tmp_path / "chroma")
    rag.index_documents(
        [
            {
                "title": "AI应用开发面试",
                "content": "AI应用开发常问RAG、Embedding、Prompt、工具调用和部署监控。",
            }
        ]
    )

    answer = rag.answer("AI应用开发面试会问什么？")

    assert "AI应用开发" in answer.content
    assert "答题框架" in answer.content
    assert answer.sources


def test_dashscope_llm_uses_qwen_37_plus_by_default():
    assert DashScopeLLM().model == "qwen3.7-plus"


def test_dashscope_llm_reports_offline_notice_without_api_key(monkeypatch):
    monkeypatch.delenv("VOLCENGINE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    response = DashScopeLLM().generate("请给出一个简短的面试建议")

    assert response.offline
    assert response.notice
    assert "离线" in response.notice or "切换" in response.notice


def test_rag_answer_exposes_local_retrieval_notice_without_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("VOLCENGINE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    rag = InterviewRAG(persist_dir=tmp_path / "chroma")
    rag.index_documents([{"title": "数据分析师SQL面试", "content": "数据分析师常考SQL、JOIN、窗口函数和指标口径。"}])

    answer = rag.answer("数据分析师SQL面试会问什么？")

    assert answer.sources
    assert answer.mode_note
    assert "本地" in answer.mode_note or "离线" in answer.mode_note


def test_rag_query_failure_reports_keyword_fallback_notice(tmp_path):
    class BrokenCollection:
        def query(self, query_texts, n_results):
            raise RuntimeError("forced query failure")

    rag = InterviewRAG(persist_dir=tmp_path / "chroma")
    rag._documents = [KnowledgeDocument(title="数据分析师SQL面试", content="数据分析师常考SQL、JOIN、窗口函数和指标口径。")]
    rag._collection = BrokenCollection()

    answer = rag.answer("SQL 面试")

    assert answer.sources
    assert "关键词" in answer.mode_note


def test_interview_bank_expands_common_interview_coverage():
    content = Path("data/interview_bank.md").read_text(encoding="utf-8")

    for keyword in ["AI应用开发", "自我介绍", "压力面", "岗位动机", "行为面试", "SQL", "金融分析"]:
        assert keyword in content


def test_interview_bank_parser_splits_h1_and_h2_sections():
    content = Path("data/interview_bank.md").read_text(encoding="utf-8")

    sections = parse_interview_bank_markdown(content)
    titles = [section["title"] for section in sections]

    assert any("六、数据分析师与 SQL 面试" in title for title in titles)
    prompt_follow_up = next(section for section in sections if "5.4 面试官追问" in section["title"])
    assert "六、数据分析师与 SQL 面试" not in prompt_follow_up["content"]


def test_rag_prefers_sql_section_over_generic_follow_up_for_sql_query(tmp_path):
    content = Path("data/interview_bank.md").read_text(encoding="utf-8")
    rag = InterviewRAG(persist_dir=tmp_path / "chroma")
    rag.index_documents(parse_interview_bank_markdown(content))

    sources = rag.search("数据分析师 SQL 面试会问什么？", top_k=2)
    titles = [source.title for source in sources]

    assert any("数据分析师与 SQL 面试" in title or "SQL 基础题" in title for title in titles)
    assert not any("可以问面试官的问题" in title for title in titles)
