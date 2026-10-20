$ErrorActionPreference='Stop'
$excelRoot=Join-Path $env:LOCALAPPDATA 'MB-ExcelQA'
$wordRoot=Join-Path $env:LOCALAPPDATA 'MB-WordQA'
$agent=Join-Path $excelRoot 'agent.ps1'
$native=Join-Path $excelRoot 'native.ps1'
$wordAgent=Join-Path $wordRoot 'word-agent.ps1'
foreach($p in @($agent,$native,$wordAgent)) { if (-not (Test-Path -LiteralPath $p)) { throw ('Missing installed worker: '+$p) } }
foreach($dir in @($excelRoot,$wordRoot)) {
    if (@(Get-ChildItem -LiteralPath $dir -Filter '*.claimed').Count -gt 0) { throw ('A job is still claimed in '+$dir+'. No changes made; allow the current job to finish.') }
}
$beforeAgent=[IO.File]::ReadAllText($agent)
$beforeNative=[IO.File]::ReadAllText($native)
$beforeWord=[IO.File]::ReadAllText($wordAgent)
$newAgent=$beforeAgent.Replace('\.xlsx$','\.xlsx?$')
$newNative=$beforeNative.Replace('\.xlsx$','\.xlsx?$')
$newNative=$newNative.Replace("if ([bool][ProductCells]::Read(`$sheet,`$address,'Locked'))", "if ([bool]`$sheet.ProtectContents -and [bool][ProductCells]::Read(`$sheet,`$address,'Locked'))")
$oldSet="[ProductCells]::Set(`$sheet,`$address,`$input.GetAttribute('kind'),`$input.GetAttribute('value'))"
$newSet="`$targetSheet=`$sheet; if (`$input.HasAttribute('sheet')) { `$targetSheet=`$book.Worksheets.Item(`$input.GetAttribute('sheet')) }; [ProductCells]::Set(`$targetSheet,`$address,`$input.GetAttribute('kind'),`$input.GetAttribute('value'))"
$newNative=$newNative.Replace($oldSet,$newSet)
$oldExpect="`$actual=[ProductCells]::Read(`$sheet,`$address,'Value2')"
$newExpect="`$expectSheet=`$sheet; if (`$expected.HasAttribute('sheet')) { `$expectSheet=`$book.Worksheets.Item(`$expected.GetAttribute('sheet')) }; `$actual=[ProductCells]::Read(`$expectSheet,`$address,'Value2')"
$newNative=$newNative.Replace($oldExpect,$newExpect)
$oldClear="[ProductCells]::Set(`$sheet,`$input.GetAttribute('cell'),'blank','')"
$newClear="`$clearSheet=`$sheet; if (`$input.HasAttribute('sheet')) { `$clearSheet=`$book.Worksheets.Item(`$input.GetAttribute('sheet')) }; [ProductCells]::Set(`$clearSheet,`$input.GetAttribute('cell'),'blank','')"
$newNative=$newNative.Replace($oldClear,$newClear)
$oldPrint="[ProductCells]::Set(`$sheet,`$input.GetAttribute('cell'),`$input.GetAttribute('kind'),`$input.GetAttribute('value'))"
$newPrint="`$printSheet=`$sheet; if (`$input.HasAttribute('sheet')) { `$printSheet=`$book.Worksheets.Item(`$input.GetAttribute('sheet')) }; [ProductCells]::Set(`$printSheet,`$input.GetAttribute('cell'),`$input.GetAttribute('kind'),`$input.GetAttribute('value'))"
$newNative=$newNative.Replace($oldPrint,$newPrint)
$oldExport="`$book.SaveAs(`$output,51); `$book.ExportAsFixedFormat(0,`$pdfPath)"
$newExport="if (`$f.GetAttribute('export_source_first') -eq 'true') { `$book.ExportAsFixedFormat(0,`$pdfPath,0,`$true,`$false); `$book.SaveAs(`$output,51); Check (`$tag+':export_source_first') `$true 'direct source export; IgnorePrintAreas=False' 'direct source export; IgnorePrintAreas=False' } else { "+$oldExport+" }"
if (-not $newNative.Contains(':export_source_first')) { $newNative=$newNative.Replace($oldExport,$newExport) }
$printState=@'
function WritePrintState([string]$Stage) {
    $state=$report.CreateElement('print_preflight');$state.SetAttribute('tag',$tag);$state.SetAttribute('stage',$Stage)
    try { $state.SetAttribute('excel_active_printer_present',[string](-not [string]::IsNullOrEmpty([string]$excel.ActivePrinter))) } catch { $state.SetAttribute('active_printer_error',$_.Exception.Message) }
    try {
        $printers=@(Get-WmiObject Win32_Printer -ErrorAction Stop)
        $state.SetAttribute('installed_printer_count',[string]$printers.Count)
        $state.SetAttribute('default_printer_present',[string](@($printers | Where-Object { $_.Default }).Count -gt 0))
    } catch { $state.SetAttribute('printer_inventory_error',$_.Exception.Message) }
    try { $state.SetAttribute('spooler_state',[string](Get-Service Spooler -ErrorAction Stop).Status) } catch { $state.SetAttribute('spooler_error',$_.Exception.Message) }
    foreach($ws in $book.Worksheets) {
        $entry=$report.CreateElement('sheet');$entry.SetAttribute('name',[string]$ws.Name)
        try {
            $entry.SetAttribute('print_area',[string]$ws.PageSetup.PrintArea)
            $entry.SetAttribute('print_title_rows',[string]$ws.PageSetup.PrintTitleRows)
            $entry.SetAttribute('print_title_columns',[string]$ws.PageSetup.PrintTitleColumns)
        } catch { $entry.SetAttribute('pagesetup_error',$_.Exception.Message) }
        [void]$state.AppendChild($entry)
    }
    $ws=$null
    foreach($nm in $book.Names) {
        if ([string]$nm.Name -match 'Print_Area|Print_Titles') {
            $entry=$report.CreateElement('print_name');$entry.SetAttribute('name',[string]$nm.Name)
            $entry.SetAttribute('refers_to',[string]$nm.RefersTo);[void]$state.AppendChild($entry)
        }
    }
    $nm=$null;[void]$r.AppendChild($state)
}
if ($f.GetAttribute('print_preflight') -eq 'true') { WritePrintState 'opened' }
'@
$sheetNeedle="`$sheet = `$book.Worksheets.Item(`$f.GetAttribute('sheet'))"
if (-not $newNative.Contains('function WritePrintState')) { $newNative=$newNative.Replace($sheetNeedle,$sheetNeedle+"`n"+$printState) }
$closeNeedle='        $book.Close($false); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet); $sheet=$null'
if (-not $newNative.Contains("WritePrintState 'exported_saved'")) { $newNative=$newNative.Replace($closeNeedle,"        if (`$f.GetAttribute('print_preflight') -eq 'true') { WritePrintState 'exported_saved' }`n"+$closeNeedle) }
$wordNeedle="`$node.SetAttribute('status',`$status)"
$wordInsert=$wordNeedle+"; if (Test-Path -LiteralPath `$result) { `$childDoc=New-Object Xml.XmlDocument; `$childDoc.Load(`$result); [void]`$node.AppendChild(`$report.ImportNode(`$childDoc.DocumentElement,`$true)) }"
$newWord=$beforeWord
if (-not $beforeWord.Contains('$childDoc=')) { $newWord=$beforeWord.Replace($wordNeedle,$wordInsert) }
if (-not $newNative.Contains('$targetSheet=') -or -not $newNative.Contains('$expectSheet=') -or -not $newNative.Contains('$sheet.ProtectContents -and') -or -not $newNative.Contains(':export_source_first') -or -not $newNative.Contains('function WritePrintState') -or -not $newNative.Contains("WritePrintState 'exported_saved'") -or -not $newAgent.Contains('\.xlsx?$') -or -not $newWord.Contains('$childDoc=')) { throw 'Installed worker differs from the reviewed version; no changes made.' }
foreach($text in @($newAgent,$newNative,$newWord)) { [void][scriptblock]::Create($text) }
# Preserve diagnostics from the earlier failed Word attempt before restarting.
[xml]$diagnostics='<report job="r3f-worker-diagnostics-20261019" status="FAIL" scope="WORKER_DIAGNOSTICS_ONLY" />'
$oldRun=Join-Path $wordRoot 'runs\r3b-word-p1-1-20261018'
if (Test-Path -LiteralPath $oldRun) {
    foreach($item in @(Get-ChildItem -LiteralPath $oldRun -Recurse -Filter 'result.xml')) {
        [xml]$child=[IO.File]::ReadAllText($item.FullName)
        $node=$diagnostics.ImportNode($child.DocumentElement,$true)
        $node.SetAttribute('tag',$item.Directory.Name)
        [void]$diagnostics.DocumentElement.AppendChild($node)
    }
}
[xml]$config=[IO.File]::ReadAllText((Join-Path $excelRoot 'config.xml'))
$client=New-Object Net.WebClient; $client.Proxy=$null
$client.Headers.Add('X-MB-Token',$config.DocumentElement.GetAttribute('token'))
try { [void]$client.UploadData('http://192.168.1.72:8765/native/result/r3f-worker-diagnostics-20261019/report.xml',[Text.Encoding]::UTF8.GetBytes($diagnostics.OuterXml)) } finally { $client.Dispose() }
$locks=@();$stops=@()
try {
    foreach($spec in @(@($excelRoot,'Local\MB-ExcelQA-v1'),@($wordRoot,'Local\MB-WordQA-v1'))) {
        $stop=Join-Path $spec[0] 'stop'
        if (Test-Path -LiteralPath $stop) { throw ('An existing stop flag was found: '+$stop) }
        [IO.File]::WriteAllText($stop,'final-office-review-20261019');$stops+=,$stop
        $mutex=New-Object Threading.Mutex($false,$spec[1])
        if (-not $mutex.WaitOne(45000,$false)) { $mutex.Close();throw 'Worker did not stop within 45 seconds; no script changes made.' }
        $locks+=,$mutex
    }
    foreach($spec in @(@($agent,$beforeAgent,$newAgent),@($native,$beforeNative,$newNative),@($wordAgent,$beforeWord,$newWord))) {
        if ([IO.File]::ReadAllText($spec[0]) -ne $spec[1]) { throw 'Worker changed concurrently; restart aborted.' }
        $backup=$spec[0]+'.before-final-20261019'
        if (-not (Test-Path -LiteralPath $backup)) { [IO.File]::WriteAllText($backup,$spec[1]) }
        [IO.File]::WriteAllText($spec[0],$spec[2])
    }
} finally {
    foreach($mutex in $locks) { $mutex.ReleaseMutex();$mutex.Close() }
    foreach($stop in $stops) { if ((Test-Path -LiteralPath $stop) -and [IO.File]::ReadAllText($stop) -eq 'final-office-review-20261019') { Remove-Item -LiteralPath $stop } }
}
foreach($worker in @($wordAgent,$agent)) { Start-Process powershell.exe -ArgumentList ('-NoProfile -STA -ExecutionPolicy Bypass -File "'+$worker+'"') -WindowStyle Minimized }
Write-Host 'Word and Excel review workers started. Leave the laptop switched on.'
