#!/usr/bin/env python3
"""Regression test for scan() msg.id deduplication.

Claude Code can re-log the same Anthropic API response multiple times
within a single JSONL (seen on session resume / continue — 40-60% of
rows in long sessions are duplicates). Before the fix, scan() summed
every row blindly, inflating cost by ~44% on real machines.

This test builds a deterministic fixture with known duplicates and
asserts that scan() counts each msg.id exactly once. Run with:

    python3 tests/test_scan_dedup.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "cc-token-stats.5m.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location("cc_token_stats", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cc_token_stats"] = mod
    spec.loader.exec_module(mod)
    return mod


def make_row(msg_id, model="claude-sonnet-4-5", inp=1000, out=500, cw=0, cr=0, ts="2026-04-15T10:00:00Z"):
    return json.dumps({
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "id": msg_id,
            "model": model,
            "usage": {
                "input_tokens": inp, "output_tokens": out,
                "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr,
            },
        },
    })


class ScanDedupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cc-dedup-test-")
        self.projects = os.path.join(self.tmp, "projects")
        os.makedirs(os.path.join(self.projects, "fakeproj"))
        self.jsonl = os.path.join(self.projects, "fakeproj", "session.jsonl")

        self.mod = load_plugin()
        # Redirect plugin to fixture tree + disable cache reuse
        self.mod.CLAUDE_DIR = self.tmp
        self.mod.SCAN_CACHE_FILE = Path(self.tmp) / ".scan-cache.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, rows):
        with open(self.jsonl, "w") as f:
            for r in rows:
                f.write(r + "\n")

    def test_unique_ids_counted_once(self):
        self._write([
            make_row("msg_a", inp=1000, out=500),
            make_row("msg_b", inp=2000, out=1000),
            make_row("msg_c", inp=500,  out=200),
        ])
        s = self.mod.scan()
        self.assertEqual(s["inp"], 3500, "input_tokens should sum across 3 unique msgs")
        self.assertEqual(s["out"], 1700)

    def test_duplicate_ids_counted_once(self):
        # msg_a appears 3 times (resume scenario), msg_b appears 2 times
        self._write([
            make_row("msg_a", inp=1000, out=500),
            make_row("msg_a", inp=1000, out=500),  # dup from resume
            make_row("msg_b", inp=2000, out=1000),
            make_row("msg_a", inp=1000, out=500),  # dup again
            make_row("msg_b", inp=2000, out=1000),  # dup
        ])
        s = self.mod.scan()
        # Expect only first occurrence of each id counted:
        # msg_a: 1000 + 500 = 1500 tokens (input+output)
        # msg_b: 2000 + 1000 = 3000 tokens
        self.assertEqual(s["inp"], 3000, f"input should be 1000+2000, got {s['inp']}")
        self.assertEqual(s["out"], 1500, f"output should be 500+1000, got {s['out']}")

    def test_duplicates_across_files_counted_once(self):
        # Less common in practice (cross-file dup was 0 on real machine)
        # but msg.id is globally unique per Anthropic API so dedup must be global.
        os.makedirs(os.path.join(self.projects, "otherproj"))
        other = os.path.join(self.projects, "otherproj", "session.jsonl")
        self._write([make_row("shared_id", inp=1000, out=500)])
        with open(other, "w") as f:
            f.write(make_row("shared_id", inp=1000, out=500) + "\n")
            f.write(make_row("unique_id", inp=500, out=200) + "\n")
        s = self.mod.scan()
        # shared_id once + unique_id once
        self.assertEqual(s["inp"], 1500)
        self.assertEqual(s["out"], 700)

    def test_no_usage_rows_skipped(self):
        # Rows without message.usage must not throw and must not be counted
        self._write([
            make_row("msg_a", inp=1000, out=500),
            json.dumps({"type": "user", "timestamp": "2026-04-15T10:00:00Z", "message": {"content": "hi"}}),
            json.dumps({"type": "assistant", "timestamp": "2026-04-15T10:00:00Z", "message": {"id": "msg_b"}}),  # no usage
        ])
        s = self.mod.scan()
        self.assertEqual(s["inp"], 1000)
        self.assertEqual(s["out"], 500)

    def test_session_cost_matches_dedup_total(self):
        # The per-session sess_cost accumulator must use the same dedup —
        # otherwise daily.sessions count and session-level breakdowns drift.
        self._write([
            make_row("m1", inp=1000, out=500),
            make_row("m1", inp=1000, out=500),  # dup within session
            make_row("m2", inp=2000, out=1000),
        ])
        s = self.mod.scan()
        # Session cost should equal total cost (single-session fixture, all dedup)
        daily = dict(s["daily"])
        total_daily_cost = sum(v["cost"] for v in daily.values())
        self.assertAlmostEqual(total_daily_cost, s["cost"], places=4,
            msg="daily cost must match total cost — both go through the same dedup path")


if __name__ == "__main__":
    unittest.main(verbosity=2)
