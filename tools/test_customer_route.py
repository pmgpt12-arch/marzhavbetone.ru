"""Contracts and negative controls for route fixes; no writes or API calls."""
import collections, hashlib, json, re, tempfile, unittest, zipfile
from pathlib import Path
import docx_text, build_preview, sync_customer_route
ROOT=Path(__file__).resolve().parent.parent

class RouteContracts(unittest.TestCase):
    def test_bankruptcy_route_requires_evidence_and_claim_type(self):
        text=(ROOT/'diagnostika.html').read_text()
        scenarios=json.loads(re.search(r'const SCENARIOS = (\[.*?\]);',text,re.S)[1])
        def match(answers):
            return next((s for s in scenarios if all(answers.get(q)==v for q,v in s['when'].items())),None)
        self.assertIsNone(match({'bankrot':True}))
        risk=match({'bankrot':True,'procedure':'none'})
        self.assertIn('признаки риска',risk['verdict'])
        self.assertNotIn('здесь не работает',risk['means'])
        for nature in ['registry','current']:
            answers={'bankrot':True,'procedure':'observation','publication':True,'claim':nature}
            result=match(answers);self.assertIsNotNone(result)
            if nature=='current':self.assertIn('не включаются в реестр',result['means'])
            answers.pop('publication');self.assertIsNone(match(answers))
        self.assertIn('Требуется уточнить',match({'bankrot':True,'procedure':'unknown'})['verdict'])

    def test_docx_exact_namespaced_text_only(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.docx'
            xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:pPr><w:pBdr><w:top w:val="single"/></w:pBdr></w:pPr><w:r><w:t>Акт &amp; &lt;образец&gt;</w:t></w:r><w:r><w:t> второй фрагмент</w:t></w:r></w:p></w:body></w:document>'
            with zipfile.ZipFile(path,'w') as z:z.writestr('word/document.xml',xml)
            self.assertEqual(docx_text.paragraphs(path),['Акт & <образец> второй фрагмент'])
            # The historical regex really swallowed the w:top properties.
            block=docx_text.PARA.findall(xml)[0]
            self.assertIn('w:pPr',''.join(docx_text.TEXT.findall(block)))

    def test_p11_rebuild_is_stable_and_no_markup(self):
        path=ROOT/'products/p11-raschet-metrami.html';text=path.read_text()
        self.assertNotRegex(text,r'&lt;/?w:|</?w:|w:pPr')
        new,reason=build_preview.render(path,build_preview.catalog())
        self.assertEqual((new,reason),(text,''))
        self.assertNotIn('платить деньгами нечем',text)

    def test_free_pages_active_offer_and_form_contract(self):
        for topic,sku in [('dengi','p1'),('bankrotstvo','p9'),('avans','p8')]:
            text=(ROOT/f'materialy/{topic}.html').read_text()
            self.assertNotRegex(text,r'/t[145]-|990 ₽|в спорной ситуации не применяются')
            self.assertIn('/'+sku+'-',text)
            self.assertIn(sync_customer_route.projection()[sku]['name'],text)
        for path in (ROOT/'materialy').glob('*.html'):
            text=path.read_text()
            if 'id="lead-form"' not in text:continue
            self.assertRegex(text,r'name="contact" type="email"[^>]+required')
            self.assertNotRegex(text,r'name="additional_contact"[^>]+required')
        server=(ROOT/'lead.php').read_text()
        self.assertIn("$_POST['contact']",server)
        self.assertIn("$consent!=='yes'",server)

    def test_catalog_projection_and_retired_skus(self):
        products=sync_customer_route.projection();self.assertEqual(len(products),13)
        self.assertTrue({'t1','t4','t5'}.isdisjoint(products))
        text=(ROOT/'app.js').read_text();self.assertEqual(text,sync_customer_route.render_cart(text))
        self.assertEqual(products['p8']['price'],2490000)
        self.assertIn("localStorage.getItem('marzhavbetone-cart')",text)

    def test_server_still_owns_price_and_rejects_retired(self):
        payment=(ROOT/'payment.php').read_text();config=(ROOT/'products-config.php').read_text()
        self.assertIn('mvb_resolve_product((array)$item)',payment)
        self.assertIn("$total += $product['price']",payment)
        for sku in ['t1','t4','t5']:self.assertIn(f"if ($sku === '{sku}') return null;",config)

    def test_p3_inventory_matches_copy_and_source_unchanged(self):
        folder=ROOT/'products-storage/05-ks-bez-vozvrata'
        counts=collections.Counter(p.suffix for p in folder.iterdir() if p.suffix in ['.docx','.xlsx','.pdf','.txt'])
        self.assertEqual(dict(counts),{'.docx':6,'.xlsx':2,'.pdf':2,'.txt':1})
        text=(ROOT/'products/p3-shablony-ks2-ks3.html').read_text()
        self.assertIn('6 файлов DOCX, 2 таблицы XLSX, 2 файла PDF',text)
        self.assertIn('КС-6а',text)

    def test_success_does_not_claim_order(self):
        text=(ROOT/'success.html').read_text()
        self.assertNotIn('ваш заказ сохранён',text)
        self.assertIn('if (!orderId || !statusKey)',text)
        self.assertIn("if (order.status === 'paid')",text)

if __name__=='__main__':unittest.main()
