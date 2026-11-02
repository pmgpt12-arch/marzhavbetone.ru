# FREE-11 production acceptance — 2026-11-02

Status: PRODUCTION_FILES_SHA_11_OF_11_PASS.

- Release GitHub Actions run: 41436909793, free11_release SUCCESS.
- Independent production SHA audit run: 41437209046, free11_readonly SUCCESS.
- 11/11 production-hosting SHA-256 equal to accepted FREE_11_FINAL_READONLY_MATRIX.json.
- Public HEAD: 11/11 HTTP 200, 10 application/zip, 1 application/pdf.
- Accepted QA files are unchanged; 11 prior files backed up by release mechanism.
- Buyer-facing POST lead.php not re-executed; no fake consent or customer lead created.
- Public GET file contents not fetched in this check; public HEAD + production-host SHA are independent gates.
- No paid orders, payment settings, main merge, or product QA changed.

Production SHA artifact digest: f4af55b5efeb8387db6a5900f70fb3995cf06fa0a24d4ca5a0ae6ffaff4d98d2

## Files

- checklist: `checklist-zakrytiya-rabot.pdf` — `bd50ad14084fbf91f2c575718e9d5f66c533ee5d1fd5dfc34eeaae2c34455394` PASS
- dengi: `dengi.zip` — `024fe485d70bf2e55775ad3d1aae45bccc2ebd94502a26f4f938366e551d9ff1` PASS
- dop-raboty: `dop-raboty.zip` — `e09176633507ec8c148547c89bcb278525d0df1d26274a385c6fc6751fd7a43e` PASS
- vozvrat-ks: `vozvrat-ks.zip` — `f0ffd8d55a4468f1542bd59d0a02cf87d49027f43d141f1c23197953fea9fcbe` PASS
- uderzhaniya: `uderzhaniya.zip` — `77ef9381b960176e152bee757e3d497e9c8bcaecc20bbeb96ed6b1f5de99e1e0` PASS
- dogovor: `dogovor.zip` — `b9a3fd2bb0e9477aef799c0a44e555a77aac281a6176d422a2f38bcc1d181f30` PASS
- bankrotstvo: `bankrotstvo.zip` — `68a1d82c16fb3c141dfa4778fc96ac03f2a058eafea5fd287103c0103903b393` PASS
- avans: `avans.zip` — `06d8e851d8bc736fa56165dd73ef8cbd54bcc0702bd23525a6952575d3278a52` PASS
- raschet-metrami: `raschet-metrami.zip` — `bacf5f6cfacbfaa5c16a90814fdc7e1ab59b1b0fa5d404c875bf44cb0dd74e74` PASS
- ispolnitelnaya-dokumentaciya: `ispolnitelnaya-dokumentaciya.zip` — `10c811a26bf0d45f3bd22fa338c03844a61d3f5495642e990421525020ecadac` PASS
- akt-skrytyh-rabot: `akt-skrytyh-rabot.zip` — `85836ca18e58c34e5008bd55e297ff98cbb710b67ffb2728820e434d08caab60` PASS
