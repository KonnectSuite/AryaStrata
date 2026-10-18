"""Fixture validation must accept normal pure-Python solutions and reject I/O."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arya_agent_bench as bench


class Validation(unittest.TestCase):
    def test_container_solution(self):
        source = '''def merge_tool_results(calls, results):
    seen = set()
    for call in calls:
        if call['id'] in seen:
            raise ValueError('duplicate')
        seen.add(call['id'])
    latest = {}
    for result in results:
        latest[result['id']] = result.get('content', '')
    return [dict(id=call['id'], status='done', content=latest[call['id']])
            if call['id'] in latest else dict(id=call['id'], status='pending') for call in calls]
'''
        case = next(c for c in bench.APP_CASES if c['name'] == 'merge_tool_results')
        self.assertTrue(bench.check(source, case['tests'])['passed'])

    def test_usage_with_values_and_setdefault(self):
        source = '''def summarize_usage(events):
    grouped = {}
    for event in events:
        i, o = event.get('input', 0), event.get('output', 0)
        if i < 0 or o < 0:
            raise ValueError('negative')
        row = grouped.setdefault(event['request_id'], {'input': 0, 'output': 0})
        row.update(input=max(row['input'], i), output=max(row['output'], o))
    return {'input': sum(row['input'] for row in grouped.values()),
            'output': sum(row['output'] for row in grouped.values())}
'''
        case = next(c for c in bench.APP_CASES if c['name'] == 'summarize_usage')
        self.assertTrue(bench.check(source, case['tests'])['passed'])

    def test_restrictions_remain(self):
        for source in ["import os", "def f():\n return open('private')",
                       "def f(x):\n return x.__class__", "def f():\n return eval('1')",
                       "def f(x):\n return x.read_text()"]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                bench.validate(source)


if __name__ == '__main__':
    unittest.main()
