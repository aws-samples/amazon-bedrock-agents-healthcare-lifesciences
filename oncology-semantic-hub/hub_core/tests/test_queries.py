"""Unit tests for hub_core.queries — Neptune/Athena executors, fully mocked (no AWS).

Run:  python -m hub_core.tests.test_queries   (from oncology_semantic_hub/)
"""
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hub_core import queries  # noqa: E402


class _Payload:
    def __init__(self, obj):
        self._b = json.dumps(obj).encode()

    def read(self):
        return self._b


class _FakeNeptune:
    def __init__(self, results):
        self._results = results
        self.last = None

    def execute_query(self, graphIdentifier, queryString, language):  # noqa: N803
        self.last = {"graph": graphIdentifier, "q": queryString, "lang": language}
        return {"payload": _Payload({"results": self._results})}


class _FakePaginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, QueryExecutionId):  # noqa: N803
        return self._pages


class _FakeAthena:
    def __init__(self, state="SUCCEEDED", rows=None, reason=""):
        self._state, self._rows, self._reason = state, rows or [], reason

    def start_query_execution(self, **kw):
        self.last = kw
        return {"QueryExecutionId": "q1"}

    def get_query_execution(self, QueryExecutionId):  # noqa: N803
        return {"QueryExecution": {"Status": {"State": self._state, "StateChangeReason": self._reason}}}

    def get_paginator(self, name):
        assert name == "get_query_results"
        return _FakePaginator([{"ResultSet": {"Rows": self._rows}}])


def _row(vals):
    return {"Data": [{"VarCharValue": v} for v in vals]}


class TestOpenCypher(unittest.TestCase):
    def test_returns_results_json(self):
        nep = _FakeNeptune([{"n": 174742}])
        out = queries.run_opencypher("MATCH (n) RETURN count(n)", graph_id="g-x", client=nep)
        self.assertIn("174742", out)
        self.assertEqual(nep.last["graph"], "g-x")
        self.assertEqual(nep.last["lang"], "OPEN_CYPHER")

    def test_truncates_large_output(self):
        big = [{"x": "y" * 100} for _ in range(500)]
        out = queries.run_opencypher("MATCH ...", graph_id="g", client=_FakeNeptune(big))
        self.assertTrue(out.endswith("... (truncated)"))
        self.assertLessEqual(len(out), 8000 + 40)


class TestAthena(unittest.TestCase):
    def test_success_returns_columns_and_rows(self):
        ath = _FakeAthena(rows=[_row(["hugo_symbol", "n"]), _row(["EGFR", "82"])])
        out = queries.run_athena_sql("SELECT ...", "oncology_semantic_hub", client=ath)
        parsed = json.loads(out)
        self.assertEqual(parsed["columns"], ["hugo_symbol", "n"])
        self.assertEqual(parsed["rows"], [["EGFR", "82"]])
        self.assertEqual(ath.last["QueryExecutionContext"], {"Database": "oncology_semantic_hub"})

    def test_failed_query_returns_reason(self):
        ath = _FakeAthena(state="FAILED", reason="Insufficient Lake Formation permission(s)")
        out = queries.run_athena_sql("SELECT ...", "db", client=ath)
        self.assertTrue(out.startswith("Query FAILED:"))
        self.assertIn("Lake Formation", out)

    def test_empty_result_set(self):
        ath = _FakeAthena(rows=[])
        self.assertEqual(queries.run_athena_sql("SELECT ...", "db", client=ath), "No results.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
