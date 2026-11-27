"""Unit test for agentcore/l3_prime.py's --inventory argparse constraint.

Historical note: this constraint was originally added to close a semgrep
dangerous-subprocess-use-tainted-env-args finding, when `a.inventory` flowed into a
`subprocess.run([..., "--inventory", a.inventory], ...)` call. That subprocess call has since been
removed entirely (l3_prime.py now imports score_provenance() directly via importlib — see
test_l3_prime_score_provenance_import.py) — there is no subprocess left to flag. The `choices=`
constraint is kept regardless: it is still real, valuable defense-in-depth, now protecting
score_provenance() from being called with a nonsensical inventory value rather than protecting a
subprocess argv.

Pure argparse logic; does not import l3_prime.py itself (which pulls in strands/mcp/boto3 at
import time) — instead it rebuilds the exact same parser definition so the test has no heavy deps
and can't be broken by unrelated import failures elsewhere in that module.
"""
import argparse
import unittest


def _build_parser():
    """Mirrors agentcore/l3_prime.py's main() argparse setup exactly (--inventory choices)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--inventory", default="quick", choices=["quick", "L0", "L0-web", "L1", "L2", "L3"])
    ap.add_argument("--kb-url", default="")
    return ap


class TestL3PrimeInventoryChoicesConstraint(unittest.TestCase):

    def test_default_inventory_is_quick(self):
        a = _build_parser().parse_args(["--question", "x"])
        self.assertEqual(a.inventory, "quick")

    def test_accepts_every_known_good_value(self):
        for val in ["quick", "L0", "L0-web", "L1", "L2", "L3"]:
            with self.subTest(inventory=val):
                a = _build_parser().parse_args(["--question", "x", "--inventory", val])
                self.assertEqual(a.inventory, val)

    def test_rejects_shell_metacharacter_payload(self):
        """Defense-in-depth: a value with shell/path metacharacters must still be rejected,
        even though it no longer reaches a subprocess — score_provenance() should only ever
        see a known-good inventory name."""
        for payload in ["; rm -rf /", "$(whoami)", "`id`", "L3; cat /etc/passwd", "../../etc/passwd"]:
            with self.subTest(payload=payload):
                with self.assertRaises(SystemExit):
                    _build_parser().parse_args(["--question", "x", "--inventory", payload])

    def test_rejects_arbitrary_unknown_value(self):
        with self.assertRaises(SystemExit):
            _build_parser().parse_args(["--question", "x", "--inventory", "not-a-real-layer"])


if __name__ == "__main__":
    unittest.main()
