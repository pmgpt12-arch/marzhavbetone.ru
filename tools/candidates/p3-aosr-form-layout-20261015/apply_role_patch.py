from pathlib import Path
p=Path("/home/denis/projects/marzhavbetone.ru/.worktrees/codex-p3-aosr-form-layout-20261015/tools/candidates/p3-aosr-form-layout-20261015/build_form.py")
s=p.read_text()
needle="for k in range(5):\n a=raw[16+53*k:16+53*(k+1)]\n"
assert s.count(needle)==1
fn="""def relabel_act(a,k):
    idx=k+1
    whole='\\\\n'.join(a)
    old_extended='Представитель лица, осуществляющего строительство, реконструкцию, капитальный ремонт, по вопросам строительного контроля'
    new_extended='Представитель Исполнителя по вопросам строительного контроля (лица, осуществляющего строительство, реконструкцию, капитальный ремонт)'
    old_regular='Представитель лица, осуществляющего строительство, реконструкцию, капитальный ремонт'
    new_regular='Представитель Исполнителя (лица, осуществляющего строительство, реконструкцию, капитальный ремонт)'
    old_party='Лицо, осуществляющее строительство, реконструкцию, капитальный ремонт'
    new_party='Исполнитель (лицо, осуществляющее строительство, реконструкцию, капитальный ремонт)'
    assert whole.count(old_extended)==2 and whole.count(old_regular)-whole.count(old_extended)==2 and whole.count(old_party)==1
    changes=[
       (f'{{{{A{idx}_ПРЕДСТАВИТЕЛЬ_ИСПОЛНИТЕЛЯ}}}}',f'{{{{A{idx}_ПРЕДСТАВИТЕЛЬ_ИСПОЛНИТЕЛЯ_РАБОТ}}}}'),
       (f'{{{{A{idx}_СТРОИТЕЛЬ}}}}',f'{{{{A{idx}_ИСПОЛНИТЕЛЬ}}}}'),
       (f'{{{{A{idx}_ПРЕДСТАВИТЕЛЬ_СТРОИТЕЛЯ}}}}',f'{{{{A{idx}_ПРЕДСТАВИТЕЛЬ_ИСПОЛНИТЕЛЯ}}}}'),
       (f'{{{{A{idx}_СТРОЙКОНТРОЛЬ_СТРОИТЕЛЯ}}}}',f'{{{{A{idx}_СТРОЙКОНТРОЛЬ_ИСПОЛНИТЕЛЯ}}}}'),
       (old_extended,new_extended),(old_regular,new_regular),(old_party,new_party)
    ]
    for old,new in changes:
        expected=2 if old in (old_extended,old_regular) else 1
        assert whole.count(old)==expected, (idx,old,whole.count(old),expected)
        whole=whole.replace(old,new)
    result=whole.split('\\\\n')
    assert len(result)==len(a)
    assert not re.search(r'(?iu)\\\\bстроитель\\\\b',whole)
    return result

"""
# Use real newline in joining, not literal backslash n in resulting script
fn=fn.replace("'\\\\n'","'\\n'") if False else fn
# Apply code snippet; textual backslashes in inserted Python source stay escaped correctly.
s=s.replace(needle,fn+needle.replace(" a=raw[16+53*k:16+53*(k+1)]"," a=relabel_act(raw[16+53*k:16+53*(k+1)],k)"))
old="assert src==dst, {'missing':list((src-dst).elements()),'extra':list((dst-src).elements())}"
assert s.count(old)==1
new="""expected=tokens('\\\\n'.join(piece for k in range(5) for piece in relabel_act(raw[16+53*k:16+53*(k+1)],k)))
assert expected==dst, {'missing':list((expected-dst).elements()),'extra':list((dst-expected).elements())}
assert sum(src.values())==sum(dst.values())==135
assert len(dst)==135
assert sum(1 for token in dst if '_СТРОИТЕЛЬ' in token or '_СТРОИТЕЛЯ' in token)==0"""
s=s.replace(old,new)
s=s.replace("'all_placeholder_identities_preserved':True","'all_135_field_slots_preserved_with_20_role_alias_renames':True")
assert "def relabel_act" in s
p.write_text(s)
print('PATCH_APPLIED',p)
