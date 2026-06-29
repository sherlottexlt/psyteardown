import os

import pytest

requires_e2e = pytest.mark.skipif(
    os.environ.get("PSYTEARDOWN_E2E") != "1",
    reason="需要 PSYTEARDOWN_E2E=1(会下载/加载本地嵌入模型)",
)


@requires_e2e
def test_local_embedding_real_model(tmp_path):
    from psyteardown.embed.local import LocalEmbeddingProvider
    from psyteardown.memory.store import CaseStore
    from psyteardown.memory.models import Case
    from psyteardown.memory.retrieval import search_similar
    from psyteardown.pipeline.schemas import (
        ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
    )

    def _case(desc, name):
        result = TeardownResult(
            product=ProductProfile(name=name, product_type="App",
                                   one_liner=name, features=[], touchpoints=[]),
            frameworks_used=["hook-model"], mappings=[],
            assessment=ExperienceAssessment(), executive_summary="s",
            meta=TeardownMeta(model="x", generated_at="t"),
        )
        return Case.from_result(result, description=desc, created_at="t")

    emb = LocalEmbeddingProvider()
    store = CaseStore(tmp_path / "c.db")
    for desc, name in [("每日签到打卡养成习惯", "签到App"),
                       ("股票基金理财投资", "理财App")]:
        store.save(_case(desc, name), emb.embed([desc])[0])

    hits = search_similar(store, emb, "打卡签到习惯养成", top_k=1)
    assert hits[0][0].product_name == "签到App"
