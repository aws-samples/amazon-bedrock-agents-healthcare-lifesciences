"""Unit tests for hub_core.schema — live schema discovery, fully mocked (no AWS).

Run:  python -m hub_core.tests.test_schema      (from oncology_semantic_hub/)
  or: python hub_core/tests/test_schema.py
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root (oncology_semantic_hub/)
from hub_core import schema  # noqa: E402


# ── fakes ────────────────────────────────────────────────────────────────────
class _FakePaginator:
    def __init__(self, pages_by_db):
        self._pages_by_db = pages_by_db

    def paginate(self, DatabaseName):  # noqa: N803 (boto3 kwarg name)
        if DatabaseName not in self._pages_by_db:
            raise Exception(f"EntityNotFoundException: {DatabaseName}")
        return self._pages_by_db[DatabaseName]


class _FakeGlue:
    def __init__(self, pages_by_db):
        self._pages_by_db = pages_by_db

    def get_paginator(self, name):
        assert name == "get_tables"
        return _FakePaginator(self._pages_by_db)


class _FakeNeptune:
    def __init__(self, summary=None, raise_exc=None):
        self._summary = summary or {}
        self._raise = raise_exc

    def get_graph_summary(self, graphIdentifier, mode):  # noqa: N803
        if self._raise:
            raise self._raise
        assert mode == "DETAILED"
        return {"graphSummary": self._summary}


def _table(name, cols, parts=None):
    return {"Name": name,
            "StorageDescriptor": {"Columns": [{"Name": n, "Type": t} for n, t in cols]},
            "PartitionKeys": [{"Name": n, "Type": t} for n, t in (parts or [])]}


# ── tests ─────────────────────────────────────────────────────────────────────
class TestLakeSchema(unittest.TestCase):
    def setUp(self):
        os.environ["SEMHUB_SCHEMA_DBS"] = "core_db,roda_db"

    def tearDown(self):
        os.environ.pop("SEMHUB_SCHEMA_DBS", None)

    def test_lists_tables_columns_and_partitions(self):
        glue = _FakeGlue({
            "core_db": [{"TableList": [_table("tcga_mutations", [("hugo_symbol", "string")], [("project_id", "string")])]}],
            "roda_db": [{"TableList": [_table("civic_evidence", [("gene", "string")])]}],
        })
        out = schema._lake_schema(glue=glue)
        self.assertIn("Athena database `core_db`", out)
        self.assertIn("tcga_mutations(hugo_symbol:string)", out)
        self.assertIn("partitions: project_id:string", out)   # partition keys surfaced
        self.assertIn("civic_evidence(gene:string)", out)

    def test_onboarded_staging_table_surfaces(self):
        glue = _FakeGlue({
            "core_db": [{"TableList": []}],
            "roda_db": [{"TableList": [_table("tcga_staging", [("gene", "string"), ("copy_number", "double")])]}],
        })
        out = schema._lake_schema(glue=glue)
        self.assertIn("tcga_staging(gene:string, copy_number:double)", out)  # new dataset auto-discovered

    def test_missing_db_is_skipped_not_fatal(self):
        glue = _FakeGlue({"core_db": [{"TableList": [_table("t", [("a", "int")])]}]})  # roda_db absent -> raises
        out = schema._lake_schema(glue=glue)
        self.assertIn("core_db", out)
        self.assertIn("roda_db`: unavailable", out)  # degraded, not crashed


class TestGraphSchema(unittest.TestCase):
    def test_formats_labels_and_property_names(self):
        schema.GRAPH_ID = "g-test"
        nep = _FakeNeptune(summary={
            "numNodes": 100, "numEdges": 200,
            "nodeLabels": ["gene_protein", "disease"],
            "edgeLabels": ["drug_protein", "disease_protein"],
            "nodeProperties": [{"name": 100}, {"cosmic_tier": 74}, {"mondo": 9}],
            "edgeProperties": [{"evidence_level": 5}, {"pmid": 5}],
        })
        out = schema._graph_schema(neptune=nep)
        self.assertIn("100 nodes, 200 edges", out)
        self.assertIn("gene_protein", out)
        self.assertIn("drug_protein", out)
        self.assertIn("cosmic_tier", out)   # property names extracted from {name: count} dicts
        self.assertIn("mondo", out)

    def test_no_graph_id_configured(self):
        schema.GRAPH_ID = ""
        self.assertIn("not configured", schema._graph_schema(neptune=_FakeNeptune()))

    def test_neptune_error_is_degraded(self):
        schema.GRAPH_ID = "g-test"
        out = schema._graph_schema(neptune=_FakeNeptune(raise_exc=RuntimeError("AccessDenied")))
        self.assertIn("Neptune schema unavailable", out)


class TestAssembly(unittest.TestCase):
    def test_get_hub_schema_combines_graph_lake_and_hints(self):
        orig_g, orig_l = schema._graph_schema, schema._lake_schema
        try:
            schema._graph_schema = lambda: "GRAPH_SECTION"
            schema._lake_schema = lambda: "LAKE_SECTION"
            out = schema.get_hub_schema()
        finally:
            schema._graph_schema, schema._lake_schema = orig_g, orig_l
        self.assertIn("GRAPH_SECTION", out)
        self.assertIn("LAKE_SECTION", out)
        self.assertIn("Query hints (curated)", out)   # curated preamble present
        self.assertIn("MONDO", out)

    def test_databases_env_override(self):
        os.environ["SEMHUB_SCHEMA_DBS"] = "a, b ,c"
        try:
            self.assertEqual(schema._databases(), ["a", "b", "c"])
        finally:
            os.environ.pop("SEMHUB_SCHEMA_DBS", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
