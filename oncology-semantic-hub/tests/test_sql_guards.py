"""Unit tests for evaluation.sql_guards — the identifier-shape validators that close the
Bandit/Slingshot B608 ("possible SQL injection vector through string-based query construction")
findings in evaluation/generate_questions.py.

Pure logic, no AWS/network. Table-driven: valid identifiers must pass through unchanged; anything
that could break out of an f-string's quoted slot (quotes, semicolons, comment markers, whitespace
tricks) must be rejected.
"""
import unittest

from evaluation.sql_guards import (
    InvalidIdentifier,
    validate_gene_symbol,
    validate_project_id,
    validate_search_term,
)


class TestValidateProjectId(unittest.TestCase):

    def test_accepts_known_good_project_ids(self):
        for pid in ["TCGA-GBM", "TCGA-BRCA", "TCGA-LUAD", "TCGA-COAD", "TCGA-SKCM", "TCGA-PRAD"]:
            with self.subTest(project=pid):
                self.assertEqual(validate_project_id(pid), pid)

    def test_rejects_sql_injection_attempt(self):
        for bad in ["TCGA-GBM' OR '1'='1", "TCGA-GBM'; DROP TABLE tcga_mutations; --",
                    "TCGA-GBM' UNION SELECT * FROM tcga_mutations --"]:
            with self.subTest(project=bad):
                with self.assertRaises(InvalidIdentifier):
                    validate_project_id(bad)

    def test_rejects_wrong_shape(self):
        for bad in ["", "gbm", "tcga-gbm", "TCGA_GBM", "TCGA-GBM-EXTRA-LONG-SUFFIX", 123, None]:
            with self.subTest(project=bad):
                with self.assertRaises(InvalidIdentifier):
                    validate_project_id(bad)


class TestValidateGeneSymbol(unittest.TestCase):

    def test_accepts_known_good_gene_symbols(self):
        for gene in ["EGFR", "TP53", "PTEN", "PIK3CA", "HLA-A", "C9orf72", "IDH1"]:
            with self.subTest(gene=gene):
                self.assertEqual(validate_gene_symbol(gene), gene)

    def test_rejects_sql_injection_attempt(self):
        for bad in ["EGFR' OR '1'='1", "EGFR'); DROP TABLE x; --", "EGFR\" RETURN 1 //"]:
            with self.subTest(gene=bad):
                with self.assertRaises(InvalidIdentifier):
                    validate_gene_symbol(bad)

    def test_rejects_cypher_breakout_attempt(self):
        """The real call site interpolates into {{name:'{gene}'}} — a closing quote/brace is the
        exact bypass this guard exists to catch."""
        for bad in ["EGFR'}) DETACH DELETE g //", "x'}}) MATCH (n) DETACH DELETE n RETURN '"]:
            with self.subTest(gene=bad):
                with self.assertRaises(InvalidIdentifier):
                    validate_gene_symbol(bad)

    def test_rejects_wrong_shape(self):
        for bad in ["", "a" * 21, "EGFR GENE", 42, None]:
            with self.subTest(gene=bad):
                with self.assertRaises(InvalidIdentifier):
                    validate_gene_symbol(bad)


class TestValidateSearchTerm(unittest.TestCase):

    def test_accepts_known_good_terms(self):
        for term in ["pi3k", "wnt", "egfr", "wnt signaling", "notch-1"]:
            with self.subTest(term=term):
                self.assertEqual(validate_search_term(term), term)

    def test_rejects_quote_breakout_attempt(self):
        """The real call site interpolates into CONTAINS '{sub}' — a closing quote is the exact
        bypass this guard exists to catch."""
        for bad in ["pi3k' OR '1'='1", "x' RETURN 1 //", "x'}) DETACH DELETE n RETURN '"]:
            with self.subTest(term=bad):
                with self.assertRaises(InvalidIdentifier):
                    validate_search_term(bad)

    def test_rejects_wrong_shape(self):
        for bad in ["", "a" * 81, 7, None]:
            with self.subTest(term=bad):
                with self.assertRaises(InvalidIdentifier):
                    validate_search_term(bad)


class TestGenerateQuestionsRejectsBeforeQuerying(unittest.TestCase):
    """Integration check: generate_questions.py's parameterized query helpers must call the guard
    BEFORE building/running any query — a malicious gene/project value should never reach
    run_sql/run_cypher. Mocks the AWS-backed helpers so this runs with no network/credentials."""

    def test_top_genes_rejects_before_calling_run_sql(self):
        from unittest import mock

        from evaluation import generate_questions as gq

        with mock.patch.object(gq, "run_sql") as m:
            with self.assertRaises(InvalidIdentifier):
                gq.top_genes("TCGA-GBM'; DROP TABLE tcga_mutations; --")
        m.assert_not_called()

    def test_drug_count_rejects_before_calling_run_cypher(self):
        from unittest import mock

        from evaluation import generate_questions as gq

        with mock.patch.object(gq, "run_cypher") as m:
            with self.assertRaises(InvalidIdentifier):
                gq.drug_count("EGFR'}) DETACH DELETE g //")
        m.assert_not_called()

    def test_top_genes_calls_run_sql_for_a_valid_project(self):
        from unittest import mock

        from evaluation import generate_questions as gq

        with mock.patch.object(gq, "run_sql", return_value=[["header"], ["EGFR", "5"]]) as m:
            result = gq.top_genes("TCGA-GBM", limit=5)
        m.assert_called_once()
        self.assertIn("TCGA-GBM", m.call_args[0][0])
        self.assertEqual(result, [("EGFR", 5)])


if __name__ == "__main__":
    unittest.main()
