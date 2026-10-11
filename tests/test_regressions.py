import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'voice-clone' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import minimax_client as mc
import voices_store as store
import delete_voice
import synthesize
import synthesize_long

class RegressionTests(unittest.TestCase):
    def test_registry_listing_and_default_does_not_claim_paid(self):
        with tempfile.TemporaryDirectory() as d, patch.object(store, 'STORE_PATH', Path(d)/'voices.json'):
            store.add_voice('test', 'TestVoice123')
            store.set_default('test')
            self.assertEqual(store.list_voices()['test']['status'], 'pending')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                delete_voice.list_voices()
            self.assertIn('TestVoice123', out.getvalue())

    def test_pronunciation_reaches_request_and_hex_audio_decodes(self):
        with patch.object(mc, '_http_post_json', return_value={'data': {'audio': '494433'}, 'base_resp': {'status_code': 0}}) as post:
            audio = mc.synthesize('TestVoice123', '重', pronunciation_dict={'tone':['重/(zhong4)']})
            self.assertEqual(audio, b'ID3')
            self.assertEqual(post.call_args.args[1]['pronunciation_dict'], {'tone':['重/(zhong4)']})

    def test_cli_pronunciation_format_and_nested_output(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)/'nested'/'voice.mp3'
            with patch.object(sys, 'argv', ['synthesize.py', '--voice-id', 'TestVoice123', '--text', '重', '--pronunciation', '重:(zhong4)', '--out', str(dest)]), patch.object(mc, 'synthesize', return_value=b'ID3') as call, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(synthesize.main(), 0)
            self.assertEqual(dest.read_bytes(), b'ID3')
            self.assertEqual(call.call_args.kwargs['pronunciation_dict'], {'tone':['重/(zhong4)']})

    def test_async_query_uses_get_and_accepts_lowercase(self):
        with patch.object(mc, '_http_get_json', return_value={'status':'success','file_id':123}) as get, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(synthesize_long.poll_task('123')['file_id'],123)
            self.assertIn('task_id=123',get.call_args.args[0])

    def test_no_key_fails_without_network(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(RuntimeError):
            mc._headers()

if __name__ == '__main__':
    unittest.main()
