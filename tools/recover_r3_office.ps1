$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'MB-ExcelQA'
$id='batch-r3-p1-empty-protection-20261018'
$run=Join-Path $root ('runs\'+$id)
$report=Join-Path $run 'report.xml'
if (-not (Test-Path -LiteralPath $report)) { throw 'Expected completed report is missing; nothing changed.' }
[xml]$doc=[IO.File]::ReadAllText($report)
if ($doc.report.job -ne $id) { throw 'Report identity mismatch; nothing changed.' }
[xml]$config=[IO.File]::ReadAllText((Join-Path $root 'config.xml'))
$client=New-Object Net.WebClient
$client.Proxy=$null
$client.Headers.Add('X-MB-Token',$config.DocumentElement.GetAttribute('token'))
try {
    foreach($f in @(Get-ChildItem -LiteralPath $run -Filter '*-filled.*')) {
        [void]$client.UploadData(('http://192.168.1.72:8765/native/result/'+$id+'/'+$f.Name),[IO.File]::ReadAllBytes($f.FullName))
    }
    [void]$client.UploadData(('http://192.168.1.72:8765/native/result/'+$id+'/report.xml'),[IO.File]::ReadAllBytes($report))
} finally { $client.Dispose() }
[IO.File]::WriteAllText((Join-Path $root ($id+'.done')),(Get-Date).ToString('s'))
Remove-Item -LiteralPath (Join-Path $root ($id+'.claimed')) -ErrorAction SilentlyContinue
$worker=Join-Path $root 'agent.ps1'
Start-Process powershell.exe -ArgumentList ('-NoProfile -STA -ExecutionPolicy Bypass -File "'+$worker+'"') -WindowStyle Minimized
Write-Host 'Completed receipt delivered. Existing Excel worker restarted.'
