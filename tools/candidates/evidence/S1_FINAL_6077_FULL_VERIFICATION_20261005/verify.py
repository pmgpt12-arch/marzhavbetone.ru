import ast, concurrent.futures, datetime, hashlib, json, re, subprocess, time
from pathlib import Path
BASE=Path("/home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical")
OUT=BASE/"s1-final-verification"
REPO="/home/denis/projects/marzhavbetone.ru"
SHA="6077a5d6cdba42cbef6f2452b799b5c118f8c5d2"
OVERLAY="d0d484b31945e39b93acc1fb6b4f5ac7333202ca"
EXPECTED_FUNCS={"f01":"3f22f63cbbd838d6b7cef1c01f2d8863f82dbaad","f03":"4f86bf1aa88aef4b2b085d96ed998bd3ed70ba45","f10":"c19c63ac56e9217c8c544ba9b1c68b5700a25324","f02":OVERLAY,"f08":OVERLAY}
TREES={"tests":BASE/"s1-final-tests","build-1":BASE/"s1-final-build-1","build-2":BASE/"s1-final-build-2"}
TESTS=json.loads((OUT/"passport.json").read_text())["tests"]
def git(args,cwd=REPO):
    return subprocess.run(["git","-C",str(cwd),*args],capture_output=True,check=True,timeout=15).stdout
def source(sha,path):
    return git(["show",sha+":"+path])
def digest(raw):return hashlib.sha256(raw).hexdigest()
def astnode(tree,name):
    return next(n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name==name) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)))
def astdump(node):return ast.dump(node,include_attributes=False)
result={"execution_pattern":"one_shot","primary_result":"final_actual_merged_S1_full_tests_and_two_complete_rebuilds","feedback_loop_required":False,"checkpoint_policy":"verified_only","actual_working_head":SHA,"accepted_overlay_source":OVERLAY,"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"PREFLIGHT","llm_api_calls":0,"source_edits":False,"merge_or_deploy":False}
start=time.monotonic()
try:
    for name,tree in TREES.items():
        assert git(["rev-parse","HEAD"],tree).decode().strip()==SHA
        assert not git(["status","--porcelain"],tree).strip(),name+" is not clean"
    root=TREES["tests"]
    final_src=source(SHA,"tools/build_s1_candidate.py")
    final_ast=ast.parse(final_src.decode())
    checks=[]
    for name,sha in EXPECTED_FUNCS.items():
        same=astdump(astnode(final_ast,name))==astdump(astnode(ast.parse(source(sha,"tools/build_s1_candidate.py").decode()),name))
        checks.append({"name":name,"accepted_source":sha,"ast_equal":same})
        assert same,"AST mismatch "+name
    same=astdump(astnode(final_ast,"RISKS"))==astdump(astnode(ast.parse(source(OVERLAY,"tools/build_s1_candidate.py").decode()),"RISKS"))
    checks.append({"name":"RISKS","accepted_source":OVERLAY,"ast_equal":same})
    assert same,"RISKS overlay lost"
    result["ast_checks"]=checks
    paths=git(["ls-tree","-r","--name-only",OVERLAY,"tools/templates/s1-owner-excel","tools/templates/s1-reviewed-corrections"]).decode().splitlines()
    paths+=["tools/approved_s1_excel.py","tools/s1_route.py","tools/s1_interest.py"]
    registry=json.loads((root/"tools/templates/s1-reviewed-corrections/corrections.json").read_text())
    paths+=["tools/"+r["review_report"] for r in registry.values()]
    result["accepted_helper_template_registry_bytes"]=[]
    for path in sorted(set(paths)):
        actual=source(SHA,path);expected=source(OVERLAY,path)
        assert actual==expected,"Helper/template/registry mismatch "+path
        result["accepted_helper_template_registry_bytes"].append({"path":path,"sha256":digest(actual),"byte_exact":True})
    for path in TESTS:assert (root/path).is_file()
    passport=json.loads((OUT/"passport.json").read_text());passport.update(status="EXECUTING",frozen_input_sha=SHA,preflight_dependency="PASS_FINAL_WORKING_SHA_OBSERVED")
    (OUT/"passport.json").write_text(json.dumps(passport,ensure_ascii=False,indent=2)+"\n")
    result["status"]="EXECUTING"
    (OUT/"preflight.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    def run(name):
        tree=TREES[name]
        if name=="tests":command=["timeout","--kill-after=5s","180s","python3","-m","pytest","-q",*TESTS]
        else:command=["timeout","--kill-after=5s","120s","python3","tools/build_s1_candidate.py","--out",str(OUT/name)]
        begin=time.monotonic()
        with (OUT/(name+".log")).open("w") as log:
            process=subprocess.run(command,cwd=tree,stdout=log,stderr=subprocess.STDOUT,timeout=190 if name=="tests" else 130)
        receipt={"name":name,"command":command,"cwd":str(tree),"exact_head":SHA,"exit_code":process.returncode,"elapsed_seconds":time.monotonic()-begin}
        (OUT/(name+"-execution.json")).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
        return receipt
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        runs=list(executor.map(run,["tests","build-1","build-2"]))
    result["runs"]=runs
    assert all(r["exit_code"]==0 for r in runs),"At least one real execution failed"
    testlog=(OUT/"tests.log").read_text()
    summary=re.search(r"(\d+) passed(?:, (\d+) warnings)? in ([0-9.]+)s",testlog)
    assert summary,"Test summary missing"
    result["tests"]={"passed":int(summary[1]),"warnings":int(summary[2] or 0),"pytest_seconds":float(summary[3]),"named_skips":"ПРОПУСК" in testlog or bool(re.search(r"\d+ skipped",testlog))}
    assert result["tests"]["passed"]==105,"Expected 105 tests; actual count changed"
    assert not result["tests"]["named_skips"],"A required test layer was skipped"
    candidate="tools/candidates/s1-oplata-za-raboty"
    files=git(["ls-tree","--name-only",SHA,candidate+"/"]).decode().splitlines()
    assert len(files)==12,"Expected 12 complete output files"
    expected_sources={"01-karta-situacii-i-granic.docx":EXPECTED_FUNCS["f01"],"03-algoritm-dejstviy.docx":EXPECTED_FUNCS["f03"],"10-obrashchenie-v-sud.docx":EXPECTED_FUNCS["f10"]}
    result["all_output_checks"]=[]
    for path in files:
        name=Path(path).name
        one=(OUT/"build-1"/name).read_bytes();two=(OUT/"build-2"/name).read_bytes();final=source(SHA,path)
        accepted_sha=expected_sources.get(name,OVERLAY)
        accepted=source(accepted_sha,path)
        assert one==two==final==accepted,"Output byte mismatch "+name
        row={"file":name,"sha256":digest(one),"both_complete_builds_equal":True,"final_tracked_equal":True,"accepted_source":accepted_sha,"accepted_output_equal":True}
        if name in registry:assert row["sha256"]==registry[name]["correction_sha256"];row["reviewed_correction_exact"]=True
        if name.startswith("04-"):
            native=(root/"tools/templates/s1-owner-excel"/name).read_bytes();assert one==native;row["owner_native_exact"]=True
        result["all_output_checks"].append(row)
    assert {p.name for p in (OUT/"build-1").iterdir()}=={Path(p).name for p in files}
    assert {p.name for p in (OUT/"build-2").iterdir()}=={Path(p).name for p in files}
    route="tools/candidates/S1-ROUTE-MAP.json"
    final_route=source(SHA,route)
    assert (TREES["build-1"]/route).read_bytes()==(TREES["build-2"]/route).read_bytes()==final_route==source(OVERLAY,route)
    result["route_map"]={"sha256":digest(final_route),"both_builds_final_and_accepted_equal":True}
    result["post_execution_worktree_status"]={name:git(["status","--porcelain"],tree).decode() for name,tree in TREES.items()}
    assert all(not v.strip() for v in result["post_execution_worktree_status"].values()),"Execution changed tracked worktree files"
    result.update(status="VERIFIED_FULL_TESTS_TWO_COMPLETE_BUILDS_ACCEPTED_BYTES_AST",native_excel_new_text_acceptance=False,official_currentness="NOT_VERIFIED",human_legal_acceptance="NOT_PERFORMED",sale_ready=False,actual_pipeline_complete=True)
except Exception as exc:
    result.update(status="FAILED_OR_BLOCKED",error=str(exc),actual_pipeline_complete=False)
finally:
    result["elapsed_seconds"]=time.monotonic()-start
    (OUT/"final-proof.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False),flush=True)
if not result.get("actual_pipeline_complete"):raise SystemExit(1)
