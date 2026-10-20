$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'MB-ExcelQA'
$native=Join-Path $root 'native.ps1'
$agent=Join-Path $root 'agent.ps1'
foreach($p in @($native,$agent)) { if (-not (Test-Path -LiteralPath $p)) { throw ('Missing installed Excel QA worker: '+$p) } }
if (@(Get-ChildItem -LiteralPath $root -Filter '*.claimed').Count -gt 0) { throw 'An Excel QA job is still claimed. No changes made.' }
$before=[IO.File]::ReadAllText($native)
if (-not $before.Contains(':export_source_first') -or -not $before.Contains('function WritePrintState')) { throw 'The source-print worker update must be installed first. No changes made.' }
$oldOpen='$book = $excel.Workbooks.Open($path,0,$false)'
$newOpen=@'
$localOpen=$f.GetAttribute('open_local') -eq 'true'
$missing=[Type]::Missing
$book = $excel.Workbooks.Open($path,0,$true,$missing,$missing,$missing,$true,$missing,$missing,$missing,$false,$missing,$false,$localOpen,0)
Check ($tag+':opened_read_only') ([bool]$book.ReadOnly) 'True' ([string]$book.ReadOnly)
$mode=$report.CreateElement('open_mode');$mode.SetAttribute('tag',$tag);$mode.SetAttribute('read_only',[string]$book.ReadOnly);$mode.SetAttribute('local_argument',[string]$localOpen);$mode.SetAttribute('corrupt_load','xlNormalLoad=0');[void]$r.AppendChild($mode)
'@
if ($before.Contains($oldOpen)) { $after=$before.Replace($oldOpen,$newOpen) }
elseif ($before.Contains($newOpen)) { $after=$before }
else { throw 'Installed Open implementation differs from the reviewed version. No changes made.' }
if (-not $after.Contains(':opened_read_only') -or -not $after.Contains('$localOpen,0)')) { throw 'Source-opening patch validation failed.' }
[void][scriptblock]::Create($after)
$stop=Join-Path $root 'stop'
if (Test-Path -LiteralPath $stop) { throw 'An existing Excel QA stop flag is present. No changes made.' }
$marker='source-open-update-20261020'
$mutex=New-Object Threading.Mutex($false,'Local\MB-ExcelQA-v1')
$locked=$false;$written=$false
try {
    [IO.File]::WriteAllText($stop,$marker)
    if (-not $mutex.WaitOne(45000,$false)) { throw 'Excel QA worker did not stop in 45 seconds. No script changes made.' }
    $locked=$true
    if ([IO.File]::ReadAllText($native) -ne $before) { throw 'Worker script changed concurrently. No changes made.' }
    $backup=$native+'.before-source-open-20261020'
    if (-not (Test-Path -LiteralPath $backup)) { [IO.File]::WriteAllText($backup,$before) }
    [IO.File]::WriteAllText($native,$after)
    if ([IO.File]::ReadAllText($native) -ne $after) { throw 'Updated native worker read-back mismatch.' }
    $written=$true
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Close()
    if ((Test-Path -LiteralPath $stop) -and [IO.File]::ReadAllText($stop) -eq $marker) { Remove-Item -LiteralPath $stop }
}
if (-not $written) { throw 'Source-opening update not written.' }
try {
    [xml]$config=[IO.File]::ReadAllText((Join-Path $root 'config.xml'))
    [xml]$report='<report job="r3q-excel-source-open-update-20261020" status="PASS" scope="WORKER_SCRIPT_UPDATE_ONLY"><check name="reviewed_source_open_patch_written" pass="True" expected="read-only opening and explicit Local option" actual="read-back matched; native behavior requires fresh jobs" /></report>'
    $client=New-Object Net.WebClient;$client.Proxy=$null
    $client.Headers.Add('X-MB-Token',$config.DocumentElement.GetAttribute('token'))
    try { [void]$client.UploadData('http://192.168.1.72:8765/native/result/r3q-excel-source-open-update-20261020/report.xml',[Text.Encoding]::UTF8.GetBytes($report.OuterXml)) } finally { $client.Dispose() }
} finally {
    Start-Process powershell.exe -ArgumentList ('-NoProfile -STA -ExecutionPolicy Bypass -File "'+$agent+'"') -WindowStyle Minimized
}
Write-Host 'Excel QA source-opening update installed. Leave the laptop switched on.'
