#!/usr/bin/env python3
"""NSP free lead route: exact production HOLD + ephemeral replay of existing form/lead code.
NO real mail, leads, orders, payments, external access or production modifications.
A replay with a removed HOLD guard is NOT acceptance of the shipping code.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()

def req(base, path, method="GET", data=None):
    body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
    r = urllib.request.Request(base+path,method=method,data=body,
                              headers={"Content-Type":"application/x-www-form-urlencoded",
                                       "Accept":"application/json"} if data is not None else {})
    try:
        with urllib.request.urlopen(r,timeout=12) as out:
            return out.status, out.read(), out.headers.get("Content-Type")
    except urllib.error.HTTPError as ex:
        return ex.code,ex.read(),ex.headers.get("Content-Type")

@contextmanager
def serve(directory, muted_mail=False):
    sock=socket.socket()
    sock.bind(("127.0.0.1",0));port=sock.getsockname()[1];sock.close()
    with tempfile.TemporaryFile() as log:
        args=["php"]
        if muted_mail:
            args+=["-d","sendmail_path=/bin/true"]
        args+=["-S",f"127.0.0.1:{port}","-t",str(directory)]
        proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
        try:
            for i in range(50):
                if proc.poll() is not None:
                    raise RuntimeError("PHP_LOCAL_SERVER_EXIT")
                try:
                    req(f"http://127.0.0.1:{port}","/__probe_nonexistent__")
                    break
                except (urllib.error.URLError,TimeoutError,ConnectionError):
                    time.sleep(.1)
            yield f"http://127.0.0.1:{port}"
        finally:
            proc.terminate()
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill()

def fields(slug, **extra):
    d={"name":"SyntheticQA","contact":"synthetic@example.invalid",
       "consent":"yes","material":slug,"source":"qa-v43"}
    d.update(extra)
    return d

def downloaded_filename(slug):
    return "checklist-zakrytiya-rabot.pdf" if slug=="checklist" else slug+".zip"

def source_filename(slug):
    return "checklist.pdf" if slug=="checklist" else slug+".zip"

def status_json(raw):
    try: return json.loads(raw)
    except (ValueError,UnicodeDecodeError): return {"parse_error":raw[:120].decode("utf-8","replace")}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--accepted-dir",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    sources=pathlib.Path(args.accepted_dir).resolve()
    assert sources.is_dir() and not sources.is_relative_to(ROOT), "Accepted sources must be off-webroot"
    matrix=json.loads((HERE/"NSP_ACCEPTED_ARTIFACTS_MATRIX.json").read_text())
    free=[r for r in matrix["rows"] if r["SKU"].startswith("FREE/")]
    assert len(free)==11 and all(r["release_permission"]=="HOLD" for r in free)
    lead_source=(ROOT/"lead.php").read_bytes()
    raw=lead_source.decode("utf-8")
    guard_begin="// Отдельное разрешение выпуска отсутствует."
    guard_end="// Откуда пришёл человек:"
    assert raw.count(guard_begin)==1 and raw.count(guard_end)==1
    assert raw.index(guard_begin)<raw.index(guard_end)
    # Guard remains ON in the real checked-in lead.php. Only TEMPORARY localhost copy removes it.
    altered=raw[:raw.index(guard_begin)] + (
        "// STAGING_REPLAY_ONLY: HOLD guard removed in temp dir for route inspection.\n"
    ) +raw[raw.index(guard_end):]
    assert "http_response_code(409)" in raw and "http_response_code(409)" not in altered
    # The historic route is used as-is otherwise, including its material selector and field rules.
    page_checks=[]
    with serve(ROOT) as current:
        for row in free:
            slug=row["SKU"].split("/",1)[1]
            status,page,mime=req(current,row["url"])
            soup=BeautifulSoup(page,"html.parser")
            heading=soup.find("h1")
            form=soup.find("form",{"id":"lead-form"})
            hold,statusbody,_=req(current,"/lead.php","POST",fields(slug))
            assert status==200 and heading and hold==409 and not form
            page_checks.append({"SKU":row["SKU"],"page_http":status,
                "h1":heading.get_text(" ",strip=True),"form_present":False,
                "current_lead_post":hold,
                "hold_response_download_field":"download" in status_json(statusbody),
                "page_sha256":sha(page),"stage":"PAGE_200_FORM_ABSENT_HOLD_409"})
        basic_validation={}
        for name,payload in [
            ("empty_name",fields("dengi",name="")),
            ("missing_contact",fields("dengi",contact="")),
            ("no_consent",fields("dengi",consent="")),
            ("invalid_email_format_with_nonempty_contact",fields("dengi",contact="bad@@address"))]:
            code,body,_=req(current,"/lead.php","POST",payload)
            basic_validation[name]={"http":code,"returned_download":"download" in status_json(body)}
        assert [basic_validation[k]["http"] for k in
                ("empty_name","missing_contact","no_consent")]==[422,422,422]
        assert basic_validation["invalid_email_format_with_nonempty_contact"]["http"]==409
        legacy_code,legacy_bytes,_=req(current,"/downloads/dengi.zip")
        assert legacy_code==200
        legacy_direct={"http":legacy_code,"sha256":sha(legacy_bytes),
                       "identity":"UNCHANGED_HISTORICAL_STATIC_PUBLIC_URL"}
    temporary_positive=[]
    negatives={}
    with tempfile.TemporaryDirectory(prefix="nsp-free-route-ephemeral-") as temp:
        sandbox=pathlib.Path(temp);www=sandbox/"www";www.mkdir()
        (www/"lead.php").write_text(altered,encoding="utf-8")
        # Explicit event stub: no telemetry requests, no real leads.
        (www/"mvb_funnel.php").write_text(
            "<?php function mvb_funnel_release(){} "
            "function mvb_clean_uuid($v){return null;} "
            "function mvb_pain_of_magnet($v){return null;} "
            "function mvb_funnel_event($type,$v){}\n",encoding="utf-8")
        (www/"downloads").mkdir()
        (www/"materialy").mkdir()
        for r in free:
            slug=r["SKU"].split("/",1)[1]
            src=sources/source_filename(slug)
            data=src.read_bytes()
            assert sha(data)==r["accepted_archive_sha256"],r["SKU"]
            shutil.copyfile(src,www/"downloads"/downloaded_filename(slug))
            html=(ROOT/r["url"].lstrip("/")).read_text(encoding="utf-8")
            assert "id=\"lead-form\"" not in html
            # Form is ONLY a disposable test fixture; the real HOLD pages remain form-free.
            form=(f"<form id=\"lead-form\" method=\"post\" action=\"../lead.php\">"
                  f"<input type=\"hidden\" name=\"material\" value=\"{slug}\">"
                  f"<input name=\"name\" required><input name=\"contact\" required>"
                  "<input name=\"consent\" value=\"yes\" type=\"checkbox\" required>"
                  "<button type=\"submit\">SyntheticQA</button></form>")
            assert html.count("</main>")==1
            test_html=html.replace("</main>",form+"</main>")
            (www/r["url"].lstrip("/")).write_text(test_html,encoding="utf-8")
        with serve(www,muted_mail=True) as replay:
            for r in free:
                slug=r["SKU"].split("/",1)[1]
                page_status,page,_=req(replay,r["url"])
                soup=BeautifulSoup(page,"html.parser")
                form=soup.find("form",{"id":"lead-form"})
                assert page_status==200 and form and form.find("input",{"name":"material"}).get("value")==slug
                st,body,_=req(replay,"/lead.php","POST",fields(slug))
                result=status_json(body)
                expected="/downloads/"+downloaded_filename(slug)
                assert st==200 and result.get("download")==expected,(slug,st,result)
                get_code,got,mime=req(replay,expected)
                again_code,got_again,_=req(replay,expected)
                correct=sha(got)==r["accepted_archive_sha256"]
                assert get_code==again_code==200 and correct and sha(got_again)==sha(got),slug
                temporary_positive.append({
                    "SKU":r["SKU"],"form_source":"SYNTHETIC_FORM_INJECTED_ONLY_IN_TEMP_WEBROOT",
                    "server_source":"UNCHANGED_LEAD_PHP_EXCEPT_GUARD_REMOVED_IN_TEMP_COPY",
                    "page_http":page_status,"post_http":st,"selected_archive":expected,
                    "delivery_http":get_code,"received_sha256":sha(got),
                    "accepted_sha256":r["accepted_archive_sha256"],
                    "repeat_http":again_code,"repeat_sha256":sha(got_again),
                    "mime":mime,"stage":"SIMULATED_HTTP_PASS_NOT_CURRENT_USER_JOURNEY"})
            # Demonstrate where the legacy handler does not satisfy new explicit requirements.
            for name,payload in [
                ("required_email_missing",fields("dengi",contact="@synthetic_telegram")),
                ("email_invalid",fields("dengi",contact="not-an-email",email="bad@@")),
                ("unknown_sku",fields("unknown-free-product")),
                ("sku_of_paid_product",fields("p8")),
                ("optional_contact_omitted",fields("dengi",contact="",email="qa@example.invalid"))
            ]:
                st,body,_=req(replay,"/lead.php","POST",payload)
                result=status_json(body)
                negatives[name]={"http":st,"download":result.get("download"),
                    "expected":"REJECT_INVALID_OR_UNAUTHORIZED_INPUT" if name!="optional_contact_omitted" else "ALLOW_WITH_VALID_EMAIL_ONLY",
                    "contract_pass": st in (400,403,422) if name!="optional_contact_omitted" else st==200}
            a1,b1,_=req(replay,"/lead.php","POST",fields("dengi"))
            a2,b2,_=req(replay,"/lead.php","POST",fields("dengi"))
            negatives["duplicate_submit"]={"first_http":a1,"repeat_http":a2,
                "contract_pass":a2 in (409,429),"same_download":
                status_json(b1).get("download")==status_json(b2).get("download")}
            direct,raw_direct,_=req(replay,"/downloads/dengi.zip")
            negatives["direct_get_bypass_form"]={"http":direct,
                "sha256":sha(raw_direct),"contract_pass":direct in (401,403,404)}
            # The old handler has no archive-SHA validation; prove wrong edition would be offered
            # ONLY INSIDE TEMP DIRECTORY. Never modify real/staged archives.
            old_bytes=(ROOT/"downloads"/"dengi.zip").read_bytes()
            correct_path=www/"downloads"/"dengi.zip"
            expected_good=sha(correct_path.read_bytes())
            assert sha(old_bytes)!=expected_good
            correct_path.write_bytes(old_bytes)
            code,actual,_=req(replay,"/downloads/dengi.zip")
            negatives["historical_archive_same_filename"]={
                "http":code,"accepted_sha256":expected_good,
                "received_sha256":sha(actual),
                "contract_pass":code!=200 or sha(actual)==expected_good}
            correct_path.write_bytes(sources.joinpath("dengi.zip").read_bytes())
            assert sha(correct_path.read_bytes())==expected_good
    assert len(temporary_positive)==11
    assert all(x["stage"]=="SIMULATED_HTTP_PASS_NOT_CURRENT_USER_JOURNEY" for x in temporary_positive)
    gaps=[name for name,row in negatives.items() if not row["contract_pass"]]
    report={
        "schema":"NSP_FREE_FORM_E2E_V1","test_date_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"LOCALHOST_ONLY; NO REAL_CUSTOMER_LEADS; NO EMAIL_OR_PAYMENTS",
        "actual_lead_php_sha256":sha(lead_source),
        "test_only_guard_removed_lead_php_sha256":sha(altered.encode("utf-8")),
        "source_pages_unchanged":True,"source_lead_php_unchanged":True,
        "mail_delivery":"DISABLED_PHP_SENDMAIL_PATH_/bin/true_ONLY_TEST_COPY",
        "funnel_events":"NOOP_STUB_ONLY_IN_TEMP_TEST",
        "actual_pages_checked":len(page_checks),
        "actual_pages_with_form":sum(x["form_present"] for x in page_checks),
        "actual_free_hold_post_409":sum(x["current_lead_post"]==409 for x in page_checks),
        "sandbox_replay_pages_forms_post_get_repeat_sha_pass":len(temporary_positive),
        "sandbox_replay_does_not_verify_undeployed_public_code":True,
        "real_checkout_or_free_customer_email":"NOT_INVOKED",
        "required_email_semantics":"NOT_IMPLEMENTED_CURRENT_HANDLER_ACCEPTS_GENERIC_CONTACT",
        "current_lead_material_unknown_fallback":"CHECKLIST_FALLBACK",
        "duplicate_submit_protection":"NOT_IMPLEMENTED_IN_OLD_HANDLER",
        "current_no_form_blocker":"11/11 HOLD PAGES HAVE NO FORM BY DESIGN",
        "public_hold":"REMAINS_HOLD_11_OF_11",
        "previous_direct_historical_archive":legacy_direct,
        "actual_hold_basic_validation":basic_validation,
        "actual_pages":page_checks,
        "isolated_replay_positive":temporary_positive,
        "isolated_negative_cases":negatives,
        "negative_contract_gaps":gaps,
        "full_chain_requirement":"PAGE→FORM→VALIDATION→SKU→FINAL_ARCHIVE→DELIVERY→RECEIVED_SHA",
        "FREE_FORM_E2E_PASS":False,
        "STAGING_STATUS":"BLOCKED_REAL_ROUTE_HOLD_AND_MISSING_FORM_AND_VALIDATION",
        "FINAL_STATUS":"PARTIAL_READY_WITH_BLOCKERS",
        "next_action":"Separate owner authorization required for final version-pinned lead/form implementation with email validation, anti-replay, unknown SKU rejection, final SHA gate and historical entitlement preservation. No live handler changed."
    }
    pathlib.Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"state":report["FINAL_STATUS"],
        "actual_hold":report["actual_free_hold_post_409"],"actual_pages_with_form":0,
        "isolated_replay_sha_pass":len(temporary_positive),
        "negative_contract_gaps":gaps,"public_release_allowed":0},ensure_ascii=False))

if __name__=="__main__":
    main()
