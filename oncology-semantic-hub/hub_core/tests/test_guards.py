"""Unit tests for hub_core.guards (read-only enforcement). Run: python -m hub_core.tests.test_guards"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hub_core import guards  # noqa: E402
from hub_core.guards import ReadOnlyViolation  # noqa: E402


class TestCypherGuard(unittest.TestCase):
    def test_allows_read(self):
        for q in ["MATCH (n) RETURN count(n)",
                  "MATCH (g:gene_protein {name:'EGFR'})-[:drug_protein]-(d:drug) RETURN DISTINCT d",
                  "MATCH (d:disease {mondo:'MONDO:0018177'})--(g) RETURN count(DISTINCT g)"]:
            self.assertEqual(guards.reject_mutations(q), q)

    def test_rejects_writes(self):
        for q in ["CREATE (n:x)", "MATCH (n) DETACH DELETE n", "MATCH (n) SET n.x=1",
                  "MERGE (n:x {id:1})", "MATCH (n) REMOVE n.p", "DROP GRAPH"]:
            with self.assertRaises(ReadOnlyViolation):
                guards.reject_mutations(q)

    def test_empty(self):
        with self.assertRaises(ReadOnlyViolation):
            guards.reject_mutations("   ")


class TestSqlGuard(unittest.TestCase):
    def test_allows_read(self):
        for q in ["SELECT count(DISTINCT case_id) FROM tcga_mutations WHERE project_id='TCGA-GBM'",
                  "WITH x AS (SELECT 1) SELECT * FROM x",
                  "SHOW TABLES", "DESCRIBE tcga_mutations", "EXPLAIN SELECT 1",
                  "SELECT * FROM t WHERE col='deleted' AND update_time > 0",
                  # RODA join uses the SQL replace() function — must NOT be rejected (was a false positive)
                  ("SELECT g.clinical_significance, count(DISTINCT m.case_id) n "
                   "FROM oncology_semantic_hub.tcga_mutations m JOIN oncology_semantic_hub_roda.genoxus_clinvar g "
                   "ON replace(m.chromosome,'chr','')=g.chrom AND m.start_position=g.pos GROUP BY 1")]:
            self.assertEqual(guards.require_select(q), q)

    def test_rejects_writes_and_ddl(self):
        for q in ["INSERT INTO t VALUES (1)", "UPDATE t SET a=1", "DELETE FROM t",
                  "DROP TABLE t", "CREATE TABLE t (a int)", "ALTER TABLE t ADD COLUMN a int",
                  "MSCK REPAIR TABLE t", "GRANT SELECT ON t TO x"]:
            with self.assertRaises(ReadOnlyViolation):
                guards.require_select(q)

    def test_rejects_stacked_statements(self):
        with self.assertRaises(ReadOnlyViolation):
            guards.require_select("SELECT 1; DROP TABLE t")

    def test_trailing_semicolon_ok(self):
        self.assertEqual(guards.require_select("SELECT 1;"), "SELECT 1;")

    def test_comment_hiding_write_is_rejected(self):
        # a comment can't turn a write into a read; leading statement must still be SELECT-like
        with self.assertRaises(ReadOnlyViolation):
            guards.require_select("/* SELECT */ DELETE FROM t")


if __name__ == "__main__":
    unittest.main(verbosity=2)
