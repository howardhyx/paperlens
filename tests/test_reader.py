"""Meaningful renderer checks using the project's original synthetic fixture."""
from pathlib import Path
import copy,importlib.util,json,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('paperlens_renderer',ROOT/'scripts/render_reader.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'examples/minimal.json').read_text(encoding='utf8'))

    def test_renders_source_order_and_embeds_assets(self):
        output,report=reader.render(self.data,ROOT/'examples')
        self.assertEqual(report['ordered_ids'],['P01','P02','F1','P03'])
        self.assertEqual(report['aligned_highlights'],5)
        self.assertLess(output.index('id="P02"'),output.index('id="F1"'))
        self.assertLess(output.index('id="F1"'),output.index('id="P03"'))
        self.assertIn('data:image/svg+xml;base64,',output)
        self.assertIn('data:font/ttf;base64,',output)
        self.assertIn('SIL OPEN FONT LICENSE',output)
        self.assertNotIn('<script src=',output)
        self.assertNotIn('@@CONTENT@@',output)

    def test_requires_translation_alignment(self):
        next(x for x in self.data['items'] if x['id']=='P01')['highlight_pairs']=[]
        with self.assertRaisesRegex(AssertionError,'matching Chinese alignment'):reader.validate(self.data)

    def test_rejects_wrong_translated_phrase(self):
        row=next(x for x in self.data['items'] if x['id']=='P01')
        row['highlight_pairs'][0]['zh']=['译文中不存在的短语']
        with self.assertRaisesRegex(AssertionError,'Chinese highlight not in translation'):reader.validate(self.data)

    def test_rejects_source_order_regression(self):
        next(x for x in self.data['items'] if x['id']=='P02')['order_page']=2
        with self.assertRaisesRegex(AssertionError,'Source order regressed'):reader.validate(self.data)

    def test_rejects_remote_image_dependency(self):
        with self.assertRaisesRegex(ValueError,'no remote image dependency'):
            reader.embed_image('https://example.com/remote.png',ROOT)

if __name__=='__main__':unittest.main()
