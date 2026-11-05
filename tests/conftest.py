import pytest
@pytest.fixture(autouse=True)
def isolate_mock_provider_quota(request,monkeypatch,tmp_path):
 if request.node.path.name.startswith('test_llm_'):monkeypatch.setenv('API_BUDGET_PATH',str(tmp_path/'mock-api-budget.sqlite3'))
