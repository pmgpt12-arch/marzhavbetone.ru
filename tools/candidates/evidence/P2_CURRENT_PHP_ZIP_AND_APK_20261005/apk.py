import pathlib,json,urllib.request,urllib.error,hashlib,datetime,re,time
R=pathlib.Path("/home/denis/.local/state/claude-dispatcher/recovery-20261004/next-packaging-qa-20261005/apk");R.mkdir(exist_ok=True);url="https://pravo.gov.ru/proxy/ips/?docbody=&nd=102079219"
E={"observed":datetime.datetime.now(datetime.timezone.utc).isoformat(),"url":url,"execution_pattern":"one_shot","primary_result":"APK_OFFICIAL_HTTP_ACQUISITION_RECEIPT","feedback_loop_required":False,"checkpoint_policy":"verified_only","attempts":1,"transport":"server urllib.request;20s socket timeout;8MiB limit","currentness":"NOT_VERIFIED","legal_acceptance":"NOT_PERFORMED"}
start=time.monotonic()
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (source availability verification)"}),timeout=20) as response:
  E.update({"http_status":response.status,"final_url":response.url,"headers":dict(response.headers.items())})
  raw=response.read(8388609);assert len(raw)<=8388608,"BODY_LIMIT_EXCEEDED";(R/"response.body").write_bytes(raw)
  E["raw_sha256"]=hashlib.sha256(raw).hexdigest();E["size"]=len(raw);encoding=response.headers.get_content_charset() or "cp1251";E["encoding"]=encoding
  text=raw.decode(encoding,errors="replace");(R/"response.txt").write_text(text);E["text_sha256"]=hashlib.sha256(text.encode()).hexdigest()
  E["title_elements"]=re.findall(r"<title[^>]*>(.*?)</title>",text,re.I|re.S);E["identity_phrase_found"]="Арбитражный процессуальный кодекс" in text;E["date_token_found"]="22.07.2002" in text
  E["displayed_edition"]="NOT_VERIFIED_REQUIRES_ACTUAL_TEXT_INSPECTION";E["status"]="RETRIEVED_PENDING_IDENTITY_READ" if E["identity_phrase_found"] else "BLOCKED_WRONG_OR_UNVERIFIED_DOCUMENT"
except Exception as err:
 E["status"]="BLOCKED";E["error"]=repr(err)
 if isinstance(err,urllib.error.HTTPError):
  raw=err.read(8388608);(R/"error.body").write_bytes(raw);E["error_body_sha256"]=hashlib.sha256(raw).hexdigest();E["http_status"]=err.code
E["elapsed_seconds"]=round(time.monotonic()-start,3)
(R/"receipt.json").write_text(json.dumps(E,ensure_ascii=False,indent=2)+"\n");print(json.dumps(E,ensure_ascii=False))
