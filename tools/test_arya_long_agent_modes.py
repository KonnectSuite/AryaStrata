"""Offline checks for text-only benchmark payloads and resume compatibility."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arya_long_agent_bench as bench


class Modes(unittest.TestCase):
    def exercise(self, text_only):
        payloads = []
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'fixture.png'
            image.write_bytes(b'fixture-image')
            tok = mock.Mock()
            tok.encode.side_effect = lambda text: list(text.encode())
            tok.decode.side_effect = lambda ids: bytes(ids).decode(errors='replace')

            def response(request, **kwargs):
                payloads.append(json.loads(request.data))
                return io.BytesIO(b'{"choices": []}')

            def session(base, case, run, think, model):
                self.assertEqual(think, 'low' if text_only else 'none')
                bench.agent.request(base, [{'role': 'system', 'content': 'instructions'},
                                           {'role': 'user', 'content': 'task'}], think, model)
                return {'case': case['name'], 'run': run, 'passed': True,
                        'trace': [{'response': {'content': 'ARYA-5907'}}]}

            args = ['bench', '--model', 'fixture', '--tokenizer', 'unused', '--out', folder,
                    '--tokens', '64', '--context', '131072'] + (['--text-only', '--think', 'low'] if text_only else [])
            with mock.patch.object(sys, 'argv', args), mock.patch.object(bench, 'tokenizer', return_value=tok), \
                 mock.patch.object(bench, 'fixtures', return_value=[('fixture', [image])]*3), \
                 mock.patch.object(bench.agent, 'session', side_effect=session), \
                 mock.patch.object(bench.agent, 'request'), \
                 mock.patch.object(bench.urllib.request, 'urlopen', side_effect=response):
                self.assertEqual(bench.main(), 0)
                report = json.loads((Path(folder)/'long-context-coding-vision.json').read_text())
                self.assertEqual(report['context_limit'], 131072)
                self.assertEqual(report['vision_enabled'], not text_only)
                for payload in payloads:
                    types = [part['type'] for part in payload['messages'][1]['content']]
                    self.assertEqual('image_url' in types, not text_only)
                    self.assertEqual('attached image' in payload['messages'][0]['content'], not text_only)
                # Changing modality must not silently reuse previous measurements.
                opposite = [arg for arg in args if arg != '--text-only'] + ['--resume']
                if not text_only:
                    opposite.append('--text-only')
                with mock.patch.object(sys, 'argv', opposite):
                    with self.assertRaisesRegex(ValueError, 'vision mode'):
                        bench.main()
                different_think = args + ['--resume', '--think', 'none' if text_only else 'low']
                with mock.patch.object(sys, 'argv', different_think):
                    with self.assertRaisesRegex(ValueError, 'reasoning mode'):
                        bench.main()

    def test_text_only(self):
        self.exercise(True)

    def test_vision(self):
        self.exercise(False)


if __name__ == '__main__':
    unittest.main()
