"""The long-context benchmark must use each extracted tokenizer's format and metadata."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import strata_tokenizer as st
from arya_context_bench import tokenizer


class BenchmarkTokenizer(unittest.TestCase):
    def test_json_merges_and_gemma_preprocessor(self):
        space=st.SPACE
        tokens=['<pad>','<eos>','<bos>','\n','\n\n',space,'a','b','c','ab',space+'ab',space+'c']+['<0x%02X>'%b for b in range(256)]
        types=[3,3,3]+[1]*9+[6]*256
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'vocab.json').write_text(json.dumps({s:i for i,s in enumerate(tokens)}),encoding='utf-8')
            (path/'merges.json').write_text(json.dumps(['a b',space+' ab',space+' c','\n \n']),encoding='utf-8')
            (path/'token_type.json').write_text(json.dumps(types),encoding='utf-8')
            (path/'tokenizer.json').write_text(json.dumps({'pre':'gemma4','special_ids':{'tokenizer.ggml.eos_token_id':1}}),encoding='utf-8')
            loaded=tokenizer(path)
            self.assertEqual([tokens[i] for i in loaded.encode('ab ab c')],['ab',space+'ab',space+'c'])
            text='ab\n\ncafé'
            self.assertEqual(loaded.decode(loaded.encode(text)),text)
            self.assertEqual(loaded.special_ids['tokenizer.ggml.eos_token_id'],1)

    def test_text_merges_remain_compatible(self):
        tokens=list(st.bytes_to_unicode().values())+['ab','<|im_end|>']
        types=[1]*257+[3]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'vocab.json').write_text(json.dumps({s:i for i,s in enumerate(tokens)}),encoding='utf-8')
            (path/'merges.txt').write_text('a b',encoding='utf-8')
            (path/'token_type.json').write_text(json.dumps(types),encoding='utf-8')
            (path/'tokenizer.json').write_text(json.dumps({'pre':'qwen35','special_ids':{'tokenizer.ggml.eos_token_id':257}}),encoding='utf-8')
            loaded=tokenizer(path)
            legacy=st.Tokenizer(tokens,['a b'],types)
            for text in ['ab','ab\n café','def f(x):\n    return x + 1']:
                self.assertEqual(loaded.encode(text),legacy.encode(text))
                self.assertEqual(loaded.decode(loaded.encode(text)),text)


if __name__=='__main__':unittest.main()
