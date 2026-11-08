import ast
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
import sys

from src.pipeline.end_to_end import EndToEndPipeline, OpenAIRagAnswerer
from src.retrieval.project_retriever import ProjectBgeM3Retriever
from src.frontend.runtime_chat import RuntimeChatService


def test_chat_clients_and_projects_reuse_one_embedding_model(monkeypatch):
    created = []
    def load_model(name):
        model = SimpleNamespace(name=name)
        created.append(model)
        return model

    def cache_resource(fn=None, **kwargs):
        wrapper = lambda function: lru_cache(maxsize=kwargs.get("max_entries"))(function)
        return wrapper(fn) if fn else wrapper

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=load_model))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: object()))
    source = Path("app/streamlit_app.py").read_text()
    parsed = ast.parse(source)
    functions = [node for node in parsed.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"get_embedding_model", "get_chat_service"}]
    namespace = {
        "st": SimpleNamespace(cache_resource=cache_resource), "ROOT": Path("."),
        "ProjectBgeM3Retriever": ProjectBgeM3Retriever,
        "OpenAIRagAnswerer": OpenAIRagAnswerer, "EndToEndPipeline": EndToEndPipeline,
        "RuntimeChatService": RuntimeChatService, "FinalPipelineChatService": object,
        "get_project_chunk_ids": lambda: {"P1": {"C1"}, "P2": {"C2"}},
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), "factory-test", "exec"), namespace)
    first = namespace["get_chat_service"]("test-key-1", "P1", "Proyecto 1")
    second = namespace["get_chat_service"]("test-key-2", "P2", "Proyecto 2")
    ingestion_encoder = namespace["get_embedding_model"]()
    assert len(created) == 1
    assert first.pipeline.dependencies.retriever._encoder is ingestion_encoder
    assert second.pipeline.dependencies.retriever._encoder is ingestion_encoder
    assert first.pipeline.dependencies.retriever._scope_ids == {"C1"}
    assert second.pipeline.dependencies.retriever._scope_ids == {"C2"}
