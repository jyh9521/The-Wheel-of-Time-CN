param([ValidateSet('check','apply','verify','restore','launch')][string]$Action='verify', [string]$GameDir, [switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$utf8=New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding=$utf8
$OutputEncoding=$utf8
Set-StrictMode -Version 2
$root=[IO.Path]::GetFullPath($GameDir).TrimEnd('\')
$package=Split-Path -Parent $MyInvocation.MyCommand.Path
$backup=Join-Path $root '.localization-backup\player-test'
function Hash([string]$p) {
 $s=[IO.File]::OpenRead($p); $h=[Security.Cryptography.SHA256]::Create()
 try { return [BitConverter]::ToString($h.ComputeHash($s)).Replace('-','').ToLowerInvariant() } finally {$s.Dispose();$h.Dispose()}
}
function Target([string]$p) {
 if ($p -notmatch '^(System|Maps|Movies|Fonts)/[^/\\]+$' -or $p.Contains('..')) {throw "Invalid resource path: $p"}
 $full=[IO.Path]::GetFullPath((Join-Path $root $p))
 if (!$full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Path escape'}
 if ((Test-Path $full) -and ((Get-Item -LiteralPath $full).Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'Linked resource rejected'}
 $parent=Split-Path -Parent $full
 if ((Test-Path $parent) -and ((Get-Item -LiteralPath $parent).Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'Linked directory rejected'}
 return $full
}
function Match([string]$p,[string]$hash,[long]$size) {return ((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p).Length -eq $size -and (Hash $p) -eq $hash)}
function AssertWritable([string]$p) {
 if ((Get-Item -LiteralPath $p).IsReadOnly) {throw ('Read-only game file: '+$p)}
 $probe=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
 $probe.Dispose() # Open permissions/locks checked; no bytes written.
}
function FileResult([string]$path,[string]$reason,[string]$expected='',[string]$actual='') {
 Write-Output ('FILE_RESULT '+(@{path=$path;reason=$reason;expected=$expected;actual=$actual}|ConvertTo-Json -Compress))
}
function Put([string]$p,[byte[]]$bytes) { [IO.Directory]::CreateDirectory((Split-Path -Parent $p)) | Out-Null; [IO.File]::WriteAllBytes($p,$bytes) }
function Snapshot-Progress([string]$phase) {
 $destination=Join-Path $backup ('progress-snapshots/'+[DateTime]::Now.ToString('yyyyMMdd-HHmmss')+'-'+$phase+'-'+[Guid]::NewGuid().ToString('N'))
 $paths=@($m.config | ForEach-Object {$_.path} | Select-Object -Unique)
 if ($m.PSObject.Properties['progress']) {
  foreach($directory in $m.progress.directories) {
   if($directory -notmatch '^[A-Za-z0-9_-]+$'){throw 'Invalid progress directory'}
   $folder=Join-Path $root $directory
   if(Test-Path -LiteralPath $folder) {
    if((Get-Item -LiteralPath $folder).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked progress directory rejected'}
    foreach($file in Get-ChildItem -LiteralPath $folder -File) {$paths+=($directory+'/'+$file.Name)}
   }
  }
 }
 $records=@()
 foreach($relative in $paths) {
  $source=[IO.Path]::GetFullPath((Join-Path $root $relative))
  if(!$source.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Progress path escape'}
  if(!(Test-Path -LiteralPath $source)){throw 'Progress file missing'}
  if((Get-Item -LiteralPath $source).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked progress file rejected'}
  $bytes=[IO.File]::ReadAllBytes($source);$target=Join-Path $destination $relative
  Put $target $bytes
  $hash=Hash $source
  if((Hash $target) -ne $hash){throw 'Progress snapshot differs'}
  $records+=@{path=$relative;sha256=$hash;size=$bytes.Length}
 }
 Put (Join-Path $destination 'SNAPSHOT.json') ($utf8.GetBytes((@{phase=$phase;files=$records}|ConvertTo-Json -Depth 8)))
 Write-Output ('PROGRESS BACKUP PASS: '+$destination)
}
function Edit-Ini([string]$p,$changes) {
 $bytes=[IO.File]::ReadAllBytes($p); $enc=[Text.Encoding]::GetEncoding(1252); $skip=0
 if ($bytes.Length -ge 2 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254) {$enc=[Text.Encoding]::Unicode;$skip=2}
 elseif ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {$enc=New-Object Text.UTF8Encoding($true);$skip=3}
 $text=$enc.GetString($bytes,$skip,$bytes.Length-$skip); $newline="`r`n"
 if (!$text.Contains("`r`n")) {$newline="`n"}
 $lines=New-Object 'Collections.Generic.List[string]'
 foreach ($line in ($text -split '\r?\n')) {$lines.Add($line)}
 foreach ($change in $changes) {
  $start=-1;$end=$lines.Count
  for($i=0;$i -lt $lines.Count;$i++) {
   if ($lines[$i] -match '^\s*\[([^]]+)\]') {
    if ($start -ge 0) {$end=$i;break}
    if ($Matches[1] -ieq $change.section) {$start=$i}
   }
  }
  if ($start -lt 0 -and $change.PSObject.Properties['match_values']) {continue}
  if ($start -lt 0) {$lines.Add('['+$change.section+']');$lines.Add($change.key+'='+$change.value);continue}
  $found=$false
  for($i=$start+1;$i -lt $end;$i++) {if ($lines[$i] -match ('^\s*'+[regex]::Escape($change.key)+'\s*=')) {$found=$true; if($change.PSObject.Properties['match_values'] -and $lines[$i].Split('=',2)[1].Trim().Trim('"') -notin $change.match_values){continue}; $lines[$i]=$change.key+'='+$change.value}}
  if (!$found -and !$change.PSObject.Properties['match_values']) {$lines.Insert($end,$change.key+'='+$change.value)}
 }
 $text=$lines -join $newline
 if ($enc.CodePage -eq 1252 -and $enc.GetString($enc.GetBytes($text)) -ne $text) {$enc=[Text.Encoding]::Unicode;$skip=2}
 $body=$enc.GetBytes($text);$prefix=$enc.GetPreamble()
 if ($skip -eq 0) {$prefix=[byte[]]@()}
 Put $p ([byte[]]($prefix+$body))
}
try {
 $contents=Get-Content -LiteralPath (Join-Path $package 'CONTENTS.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 foreach($item in $contents.PSObject.Properties) {
  $name=$item.Name
  if ($name.StartsWith('LocalizationTest/')) {$p=Join-Path $package $name.Substring(17)} else {$p=Join-Path (Split-Path -Parent $package) $name}
  if ((Hash $p) -ne $item.Value) {throw "Package checksum differs: $name"}
 }
 $m=Get-Content -LiteralPath (Join-Path $package 'MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 if ($m.format -ne 'player-test-v1') {throw 'Unknown package format'}
 if ($Action -ne 'check' -and (Hash (Target $m.launch.path)) -ne $m.launch.sha256) {throw 'Unsupported game executable'}
 $statePath=Join-Path $backup 'STATE.json'
 if (Test-Path $statePath) {
  $existing=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($existing.manifest_sha256 -ne (Hash (Join-Path $package 'MANIFEST.json'))) {
   # Explicitly packaged predecessor manifests permit resource-only recovery.
   $recovery=Join-Path $package 'RESTORE_MANIFESTS.json'
   if($Action -eq 'restore' -and (Test-Path -LiteralPath $recovery)) {
    $known=Get-Content -LiteralPath $recovery -Raw -Encoding UTF8 | ConvertFrom-Json
    $entry=$known.PSObject.Properties[$existing.manifest_sha256]
    if($entry) {$prior=$entry.Value; $prior|Add-Member -MemberType NoteProperty -Name progress -Value $m.progress -Force; $m=$prior}
    else {throw 'Backup belongs to another package; matching recovery manifest required'}
   } else {
   # A completed restore may leave an older STATE.json. Accept only fully
   # restored resources for check/apply; foreign active patches remain rejected.
   $restored=($Action -eq 'check' -or $Action -eq 'apply')
   foreach($e in $m.files) {
    if($e.owned) {if(Test-Path (Target $e.path)){$restored=$false}}
    elseif(!(Match (Target $e.path) $e.original_sha256 $e.original_size)) {$restored=$false}
   }
   if(!$restored){FileResult '.localization-backup/player-test/STATE.json' 'backup_package';throw 'Backup belongs to another package; restore with its original installer first'}
   }
  }
 }
 if ($Action -eq 'check') {
  $installed=Test-Path $statePath
  $allInstalled=$installed
  if ($installed) {foreach($e in $m.files) {if (!(Match (Target $e.path) $e.modified_sha256 $e.modified_size)) {$allInstalled=$false}}}
  $failures=0
  $checks=@(@{path=$m.launch.path;owned=$false;original_sha256=$m.launch.sha256;original_size=-1})+@($m.files)
  foreach($e in $checks) {
   try {
    $p=Target $e.path
    if ($allInstalled -and $e.path -ne $m.launch.path) {AssertWritable $p;FileResult $e.path 'installed';continue}
    if ($e.owned) {if(Test-Path -LiteralPath $p){FileResult $e.path 'addition_exists';$failures++}else{FileResult $e.path 'ready'};continue}
    if (!(Test-Path -LiteralPath $p -PathType Leaf)) {FileResult $e.path 'missing';$failures++;continue}
    $actual=Hash $p
    if ($actual -ne $e.original_sha256 -or ($e.original_size -ge 0 -and (Get-Item -LiteralPath $p).Length -ne $e.original_size)) {
     FileResult $e.path 'hash_mismatch' $e.original_sha256 $actual;$failures++;continue
    }
    if ((Get-Item -LiteralPath $p).IsReadOnly) {FileResult $e.path 'readonly';$failures++;continue}
    AssertWritable $p;FileResult $e.path 'pass'
   } catch {FileResult $e.path 'access' '' ('0x'+$_.Exception.HResult.ToString('X8'));$failures++}
  }
  foreach($group in ($m.config | Group-Object path)) {
   try {$p=Target $group.Name;if(!(Test-Path -LiteralPath $p -PathType Leaf)){FileResult $group.Name 'missing';$failures++;continue};AssertWritable $p;FileResult $group.Name 'pass'}
   catch {FileResult $group.Name 'access' '' ('0x'+$_.Exception.HResult.ToString('X8'));$failures++}
  }
  if($failures -gt 0){Write-Output ('CHECK FAILED: files='+$failures);exit 1}
  Write-Output ('CHECK PASS: resources='+$m.files.Count+'; supported game files matched; no game files written')
  exit 0
 }
 if ($Action -eq 'verify' -or $Action -eq 'launch') {
  if (!(Test-Path $statePath)) {throw 'Localization installation must complete first'}
  foreach($e in $m.files) {if (!(Match (Target $e.path) $e.modified_sha256 $e.modified_size)) {throw "Installed resource differs: $($e.path)"}}
  Write-Output ('VERIFY PASS: resources='+$m.files.Count)
  if ($Action -eq 'launch' -and !$VerifyOnly) {Push-Location (Join-Path $root 'System');try {& .\WoT.exe} finally {Pop-Location}}
  elseif ($Action -eq 'launch') {Write-Output 'LAUNCH PRECHECK PASS: normal WoT.exe, no arguments; no game launch'}
  exit 0
 }
 if ($Action -eq 'restore') {
  if (!(Test-Path $statePath)) {throw 'No installation backup'}
  $state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach($e in $m.files) {
   $p=Target $e.path
   if ($e.owned) {if ((Test-Path $p) -and !(Match $p $e.modified_sha256 $e.modified_size)) {throw "Changed addition: $($e.path)"}}
   else {if (!(Match (Join-Path $backup $e.path) $e.original_sha256 $e.original_size)) {throw 'Backup differs'}
    if (!(Match $p $e.original_sha256 $e.original_size) -and !(Match $p $e.modified_sha256 $e.modified_size)) {throw "External modification: $($e.path)"}}
  }
  Snapshot-Progress 'restore'
  foreach($e in $m.files) {$p=Target $e.path;if($e.owned) {if(Test-Path $p){[IO.File]::Delete($p)}} else {Put $p ([IO.File]::ReadAllBytes((Join-Path $backup $e.path)))}}
  # Preserve current INI bytes: settings and save-slot metadata evolve during play.
  foreach($e in $m.files) {if($e.owned) {if(Test-Path (Target $e.path)){throw 'Addition restore failed'}} elseif (!(Match (Target $e.path) $e.original_sha256 $e.original_size)) {throw 'Restore verification failed'}}
  Write-Output ('RESTORE PASS: resources='+$m.files.Count+'; current settings and save slots preserved; saves untouched')
  exit 0
 }
 if (Test-Path $statePath) {
  $all=$true; foreach($e in $m.files) {if(!(Match (Target $e.path) $e.modified_sha256 $e.modified_size)) {$all=$false}}
  if($all){Write-Output 'APPLY PASS: already installed';exit 0}
 }
 # Stage and validate every output before touching game resources.
 $staged=New-Object 'Collections.Generic.Dictionary[string,string]'
 $stage=Join-Path ([IO.Path]::GetTempPath()) ('LocaleStage-'+[Guid]::NewGuid().ToString('N'))
 [IO.Directory]::CreateDirectory($stage)|Out-Null
 foreach($e in $m.files) {
  $p=Target $e.path
  if($e.owned) {if(Test-Path $p){throw "Addition already exists: $($e.path)"};$original=[byte[]]@()}
  else {if(!(Match $p $e.original_sha256 $e.original_size)){throw "Unsupported original: $($e.path)"};AssertWritable $p;$original=[IO.File]::ReadAllBytes($p)}
  $stream=New-Object IO.MemoryStream
  try {
   foreach($op in $e.operations) {
    $n=[long]$op.size;if($n -lt 0 -or $stream.Length+$n -gt $e.modified_size){throw 'Invalid output size'}
    if($op.PSObject.Properties['copy']) { $at=[long]$op.copy;if($at -lt 0 -or $at+$n -gt $original.Length){throw 'Invalid copy range'};$stream.Write($original,[int]$at,[int]$n) }
    else {if($op.payload -notmatch '^payload/[0-9a-f]{64}\.bin$'){throw 'Invalid payload path'};$literal=Join-Path $package $op.payload
     if(!(Match $literal $op.sha256 $n)){throw 'Payload differs'};$b=[IO.File]::ReadAllBytes($literal);$stream.Write($b,0,$b.Length)}
   }
   $bytes=$stream.ToArray();if($bytes.Length -ne $e.modified_size){throw 'Output length differs'}
   $h=[Security.Cryptography.SHA256]::Create();try{$sum=[BitConverter]::ToString($h.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}
   if($sum -ne $e.modified_sha256){throw 'Output hash differs'}
   $stageFile=Join-Path $stage ([Guid]::NewGuid().ToString('N')+'.bin')
   [IO.File]::WriteAllBytes($stageFile,$bytes);$staged.Add($e.path,$stageFile)
  }finally{$stream.Dispose()}
 }
 $config=@();foreach($group in ($m.config | Group-Object path)) {$p=Target $group.Name;if(!(Test-Path $p)){throw "Missing configuration: $($group.Name)"};AssertWritable $p;$config+=@{path=$group.Name;sha256=(Hash $p)}}
 Snapshot-Progress 'apply'
 [IO.Directory]::CreateDirectory($backup)|Out-Null
 foreach($e in $m.files){if(!$e.owned){Put (Join-Path $backup $e.path) ([IO.File]::ReadAllBytes((Target $e.path)))}}
 foreach($c in $config){Put (Join-Path $backup $c.path) ([IO.File]::ReadAllBytes((Target $c.path)))}
 @{config=$config;manifest_sha256=(Hash (Join-Path $package 'MANIFEST.json'))} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding UTF8
 $written=@()
 try {
  foreach($e in $m.files){$written+=,$e;Put (Target $e.path) ([IO.File]::ReadAllBytes($staged[$e.path]))}
  foreach($group in ($m.config | Group-Object path)){Edit-Ini (Target $group.Name) $group.Group}
  foreach($e in $m.files){if(!(Match (Target $e.path) $e.modified_sha256 $e.modified_size)){throw 'Install readback differs'}}
 }catch{
  foreach($e in $written){$p=Target $e.path;if($e.owned){if(Test-Path $p){[IO.File]::Delete($p)}}else{Put $p ([IO.File]::ReadAllBytes((Join-Path $backup $e.path)))}}
  foreach($c in $config){Put (Target $c.path) ([IO.File]::ReadAllBytes((Join-Path $backup $c.path)))}
  throw
 }
 Write-Output ('APPLY PASS: resources='+$m.files.Count+'; subtitles enabled; original settings and resources backed up')
 exit 0
}catch{Write-Output ('ERROR: '+$_.Exception.Message);exit 1}
finally {
 if (Get-Variable stage -ErrorAction SilentlyContinue) {
  # Delete only files created in this unique staging folder; never recurse.
  if (Test-Path -LiteralPath $stage) {
   foreach($f in [IO.Directory]::GetFiles($stage)) {[IO.File]::Delete($f)}
   [IO.Directory]::Delete($stage)
  }
 }
}
