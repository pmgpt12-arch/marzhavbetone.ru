Canonical S1 generator preserves owner Excel layouts without stale calculations.

{
  "result": "SOURCE_CANDIDATE_VERIFIED",
  "base": "ccc6b5c3b0a799b67d5a87e9108555a99e0c60a7",
  "two_builds": {
    "status": "VERIFIED",
    "records": [
      {
        "file": "02-proverka-i-kontrol-otveta.xlsx",
        "sha256": "0a5c75b2816b93b6da4c0cfa395a5d9e5989ad6a2c44ce1edd70c8b3a7376fcc",
        "two_builds_byte_equal": true,
        "owner_byte_equal": true,
        "08_only_row13_source_height_restored": false
      },
      {
        "file": "04-uchet-raschetov-i-otpravok.xlsx",
        "sha256": "f735e85286952a2780d413aea7debbe7a7ceda24edf717d79b631a4aad8945d9",
        "two_builds_byte_equal": true,
        "owner_byte_equal": true,
        "08_only_row13_source_height_restored": false
      },
      {
        "file": "08-raschet-procentov-395.xlsx",
        "sha256": "9c2b69043ce6c09924236abfb0808659d0b739347e22aa9796b400440def3d92",
        "two_builds_byte_equal": true,
        "owner_byte_equal": false,
        "08_only_row13_source_height_restored": true
      }
    ],
    "tests_exit": 0
  },
  "tests": "67 PASS, zero skipped",
  "other_files_unchanged": [
    "MANIFEST.md",
    "05-peregovory-i-perenos-sroka.docx",
    "06-uvedomlenie-o-prosrochke.docx",
    "07-otpravka-i-dokazatelstvo.docx",
    "10-obrashchenie-v-sud.docx",
    "01-karta-situacii-i-granic.docx",
    "09-pretenziya.docx",
    "03-algoritm-dejstviy.docx",
    "00-START-HERE.txt"
  ],
  "guards": [
    "template hash",
    "expanded cell semantics including shared formulas",
    "native normal/x14 validations target equality",
    "defined names",
    "write after gates only"
  ],
  "source_delta": "save uses accepted native templates after semantic verification; P1_08 M19 label accent normalized to owner text",
  "print": {
    "status": "ACTUAL_CALC_PDF_LONG_WARNING_COMPLETE",
    "pdf_sha256": "1b8f903efa21aaa1caad26a8eb3a963cd66bef018ea61a9b6b0bbbbdbae6e6cf",
    "warning_start_and_end_present": true,
    "row13_height": 63,
    "source_template_unchanged": true,
    "native_Excel_owner_review": "pending only updated08"
  },
  "owner_acceptance": "02 and04 exact accepted bytes;08 except row13 restored28.8->63; no new formula or other layout changes",
  "native08": "pending updated height check",
  "not_done": [
    "independent acceptance",
    "whole P1",
    "legal currentness",
    "release"
  ],
  "cost_usd": 0
}
