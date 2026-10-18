$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'MB-ExcelQA'
$id='batch-r3-p1-empty-protection-20261018'
$run=Join-Path $root ('runs\'+$id)
$report=Join-Path $run 'report.xml'
if (-not (Test-Path -LiteralPath $report)) { throw 'Expected completed report is missing; nothing changed.' }
[xml]$doc=[IO.File]::ReadAllText($report)
if ($doc.report.job -ne $id) { throw 'Report identity mismatch; nothing changed.' }
# Include the existing Word child diagnostics that the older agent omitted from its summary.
$wordRun=Join-Path $env:LOCALAPPDATA 'MB-WordQA\runs\r3b-word-p1-1-20261018'
if (Test-Path -LiteralPath $wordRun) {
    $diagnostics=$doc.CreateElement('word-diagnostics')
    $diagnostics.SetAttribute('job','r3b-word-p1-1-20261018')
    foreach($item in @(Get-ChildItem -LiteralPath $wordRun -Recurse -Filter 'result.xml')) {
        [xml]$child=[IO.File]::ReadAllText($item.FullName)
        $node=$doc.ImportNode($child.DocumentElement,$true)
        $node.SetAttribute('tag',$item.Directory.Name)
        [void]$diagnostics.AppendChild($node)
    }
    [void]$doc.DocumentElement.AppendChild($diagnostics)
}
[xml]$config=[IO.File]::ReadAllText((Join-Path $root 'config.xml'))
$client=New-Object Net.WebClient
$client.Proxy=$null
$client.Headers.Add('X-MB-Token',$config.DocumentElement.GetAttribute('token'))
try {
    foreach($f in @(Get-ChildItem -LiteralPath $run -Filter '*-filled.*')) {
        [void]$client.UploadData(('http://192.168.1.72:8765/native/result/'+$id+'/'+$f.Name),[IO.File]::ReadAllBytes($f.FullName))
    }
    [void]$client.UploadData(('http://192.168.1.72:8765/native/result/'+$id+'/report.xml'),[Text.Encoding]::UTF8.GetBytes($doc.OuterXml))
} finally { $client.Dispose() }
[IO.File]::WriteAllText((Join-Path $root ($id+'.done')),(Get-Date).ToString('s'))
Remove-Item -LiteralPath (Join-Path $root ($id+'.claimed')) -ErrorAction SilentlyContinue
if (@(Get-ChildItem -LiteralPath $root -Filter '*.claimed' -ErrorAction SilentlyContinue).Count -gt 0) { throw 'Another claimed job exists; worker scripts were not changed.' }
# Keep published XLS forms in their original format. Extend only the filename guard.
foreach($name in @('agent.ps1','native.ps1')) {
    $path=Join-Path $root $name
    $text=[IO.File]::ReadAllText($path)
    $updated=$text.Replace('\.xlsx$','\.xlsx?$')
    if ($text -ne $updated) {
        $backup=$path+'.before-r3'
        if (-not (Test-Path -LiteralPath $backup)) { [IO.File]::WriteAllText($backup,$text) }
        [IO.File]::WriteAllText($path,$updated)
    }
}
$worker=Join-Path $root 'agent.ps1'
Start-Process powershell.exe -ArgumentList ('-NoProfile -STA -ExecutionPolicy Bypass -File "'+$worker+'"') -WindowStyle Minimized
Write-Host 'Completed receipt delivered. Existing Excel worker restarted.'
