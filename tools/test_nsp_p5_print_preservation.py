#!/usr/bin/env python3
from pathlib import Path
import copy,json
from check_xlsx_print_contract import snapshot,compare
R=Path(__file__).resolve().parents[1]
b=json.loads((R/'tools/nsp-product-audit-fixes-20261021/p5-print-baseline.json').read_text())
actual=snapshot(R/b['path']);errors=compare(b['print_contract'],actual)
assert not errors,json.dumps(errors,ensure_ascii=False)
assert compare(actual,actual)==[]
mutant=copy.deepcopy(actual);mutant['print_names']={}
assert compare(actual,mutant),'Gate failed to detect lost print area'
mutant=copy.deepcopy(actual)
for settings in mutant['sheet_print_metadata'].values():settings['pageSetup']=None
assert compare(actual,mutant),'Gate failed to detect lost page setup'
print('P5_PRINT_CONTRACT_PASS; two negative controls detected; calculation acceptance separate')
