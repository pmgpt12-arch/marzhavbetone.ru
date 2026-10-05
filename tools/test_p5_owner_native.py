"""P5 accepted formulas + owner native bytes; no owner openpyxl save."""
from functools import lru_cache
import importlib.util
from pathlib import Path
import runpy
import hashlib

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName
import pytest

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / 'products-storage/07-uderzhaniya-shtrafy-zachety'


@lru_cache(maxsize=1)
def builder():
    # Existing isolated author helper supplies reportlab stub for PDF only.
    helper = runpy.run_path(str(ROOT / 'tools/candidates/evidence/MB001_P5_FIX2/rebuild_04_05_340.py'))
    helper['_заглушка_reportlab']()
    spec = importlib.util.spec_from_file_location('p5_native_builder', ROOT / 'products-storage/build_paid_07.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('filename', ['04-raschet-ubytkov.xlsx', '05-reestr-uderzhaniy.xlsx'])
def test_canonical_and_template_are_exact_owner_bytes(filename):
    module = builder()
    native = (module.P5_OWNER_TEMPLATES / filename).read_bytes()
    assert hashlib.sha256(native).hexdigest() == module.P5_OWNER_SHA256[filename]
    assert (PACK / filename).read_bytes() == native


def test_actual_generator_matches_accepted_source_semantics_and_owner_bytes(tmp_path, monkeypatch):
    module = builder()
    before = {n: (module.P5_OWNER_TEMPLATES / n).read_bytes() for n in module.P5_OWNER_SHA256}
    monkeypatch.setattr(module, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(module, 'create_pdf_simple', lambda *args, **kwargs: None)
    (tmp_path / '07-uderzhaniya-shtrafy-zachety').mkdir()
    module.build_paid_07()
    for name, native in before.items():
        assert (tmp_path / '07-uderzhaniya-shtrafy-zachety' / name).read_bytes() == native
        assert (module.P5_OWNER_TEMPLATES / name).read_bytes() == native


def workbook():
    module = builder()
    name = '04-raschet-ubytkov.xlsx'
    return module, name, openpyxl.load_workbook(module.P5_OWNER_TEMPLATES / name)


@pytest.mark.parametrize('change,expected', [
    ('formula', 'semantic mismatch'),
    ('validation', 'validation mismatch'),
    ('name', 'defined-name mismatch'),
    ('merged', 'merged-cell mismatch'),
])
def test_semantic_divergence_blocks_before_existing_output_mutation(tmp_path, change, expected):
    module, filename, generated = workbook()
    if change == 'formula':
        generated.active['G18'] = '=1'
    elif change == 'validation':
        rule = DataValidation(type='decimal', operator='between', formula1='0', formula2='100')
        generated.active.add_data_validation(rule)
        rule.add('F18')
    elif change == 'name':
        generated.defined_names.add(DefinedName('unexpected', attr_text="'Расчёт требования'!$F$18"))
    else:
        generated.active.unmerge_cells('A2:H2')
    output = tmp_path / filename
    output.write_bytes(b'previous accepted output')
    with pytest.raises(ValueError, match=expected):
        module.write_owner_p5_workbook(generated, output)
    assert output.read_bytes() == b'previous accepted output'
    assert not list(tmp_path.glob('*.tmp'))


def test_template_corruption_blocks_before_existing_output_mutation(tmp_path, monkeypatch):
    module, filename, generated = workbook()
    templates = tmp_path / 'templates'
    templates.mkdir()
    (templates / filename).write_bytes(b'corrupt')
    monkeypatch.setattr(module, 'P5_OWNER_TEMPLATES', templates)
    output = tmp_path / filename
    output.write_bytes(b'previous accepted output')
    with pytest.raises(ValueError, match='hash mismatch'):
        module.write_owner_p5_workbook(generated, output)
    assert output.read_bytes() == b'previous accepted output'
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('code,expected', [
    ('DD.MM.YYYY', True),
    (r'dd\.mm\.yyyy', True),
    ('DD.MM.YY', False),
    ('General', False),
    ('MM/DD/YYYY', False),
])
def test_full_date_accepts_exact_native_literal_equivalent_only(code, expected):
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    from test_p5_calc_results import _полный_формат_даты
    assert _полный_формат_даты(code) is expected
