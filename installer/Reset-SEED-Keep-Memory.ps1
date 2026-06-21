#Requires -Version 5.1

<#
.SYNOPSIS
Rimuove installazioni SEED e dati locali, preservando solo la memoria SQLite.

.DESCRIPTION
Script una tantum per tester che devono reinstallare SEED da zero. Opera solo
sotto LOCALAPPDATA, crea un backup verificato di data\seed.db e dei sidecar
SQLite, rimuove runtime/modelli/config/stato/lineage/workspace e ripristina la
sola memoria nella root dati canonica.

Usare prima -WhatIf. L'esecuzione reale richiede la frase RESET-SEED oppure
il parametro -Yes. Provider key e configurazioni devono essere reinseriti.
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Medium")]
param(
    [switch]$Yes,
    [string]$BackupRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$LocalRoot = [IO.Path]::GetFullPath(
    [Environment]::GetFolderPath("LocalApplicationData")
).TrimEnd("\")
if ([string]::IsNullOrWhiteSpace($LocalRoot)) {
    throw "LOCALAPPDATA non disponibile."
}

$ProgramsRoot = Join-Path $LocalRoot "Programs"
$CanonicalInstallRoot = Join-Path $ProgramsRoot "SEED"
$DataRoot = Join-Path $LocalRoot "SEED"
if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
    $BackupRoot = Join-Path $LocalRoot "SEED-memory-backups"
}
$BackupRoot = [IO.Path]::GetFullPath($BackupRoot).TrimEnd("\")
$MemoryNames = @("seed.db", "seed.db-wal", "seed.db-shm")
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDirectory = Join-Path $BackupRoot $Timestamp
$ReportPath = Join-Path $BackupDirectory "RESET_REPORT.txt"

function Write-Step([string]$Message) {
    Write-Host "[SEED reset] $Message"
}

function Get-FullPath([string]$Path) {
    return [IO.Path]::GetFullPath($Path).TrimEnd("\")
}

function Test-IsUnder([string]$Path, [string]$Parent) {
    $full = Get-FullPath $Path
    $root = (Get-FullPath $Parent) + "\"
    return $full.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)
}

function Assert-SafeLocalPath([string]$Path) {
    $full = Get-FullPath $Path
    if (-not (Test-IsUnder $full $LocalRoot)) {
        throw "Path rifiutato fuori da LOCALAPPDATA: $full"
    }
    if ([string]::Equals($full, $LocalRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "La root LOCALAPPDATA non puo essere rimossa."
    }
    if (Test-Path -LiteralPath $full) {
        $item = Get-Item -LiteralPath $full -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Path reparse/junction rifiutato: $full"
        }
    }
    return $full
}

function Test-SeedInstallRoot([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }
    foreach ($marker in @(
        "runtime\SEED.exe",
        "supervisor\SEEDSupervisor.exe",
        "release-manifest.json",
        "unins000.exe"
    )) {
        if (Test-Path -LiteralPath (Join-Path $Path $marker)) {
            return $true
        }
    }
    return $false
}

function Stop-SeedProcesses {
    foreach ($name in @("SEED", "SEEDSupervisor")) {
        foreach ($process in @(Get-Process -Name $name -ErrorAction SilentlyContinue)) {
            Write-Step "arresto processo $($process.ProcessName) ($($process.Id))"
            if ($process.MainWindowHandle -ne 0) {
                [void]$process.CloseMainWindow()
                Wait-Process -Id $process.Id -Timeout 5 -ErrorAction SilentlyContinue
            }
            if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
                Stop-Process -Id $process.Id -Force
                Wait-Process -Id $process.Id -Timeout 5 -ErrorAction SilentlyContinue
            }
        }
    }
}

function Get-FileDigest([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-MemorySources {
    $sources = @()
    $database = Join-Path (Join-Path $DataRoot "data") "seed.db"
    if (-not (Test-Path -LiteralPath $database -PathType Leaf)) {
        return $sources
    }
    foreach ($name in $MemoryNames) {
        $source = Join-Path (Join-Path $DataRoot "data") $name
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            $sources += $source
        }
    }
    return $sources
}

function Assert-SqliteHeader([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    try {
        if ($stream.Length -lt 16) {
            throw "Memoria SQLite troppo corta: $Path"
        }
        $header = New-Object byte[] 16
        [void]$stream.Read($header, 0, 16)
        $text = [Text.Encoding]::ASCII.GetString($header)
        if ($text -ne "SQLite format 3`0") {
            throw "Header SQLite non valido: $Path. Reset annullato."
        }
    }
    finally {
        $stream.Dispose()
    }
}

$InstallRoots = New-Object "System.Collections.Generic.List[string]"
function Add-InstallRoot([string]$Candidate, [switch]$Canonical) {
    if ([string]::IsNullOrWhiteSpace($Candidate)) {
        return
    }
    $full = Get-FullPath $Candidate
    if (-not (Test-IsUnder $full $LocalRoot)) {
        return
    }
    if (-not $Canonical -and -not (Test-SeedInstallRoot $full)) {
        return
    }
    if ((Test-Path -LiteralPath $full) -and -not $InstallRoots.Contains($full)) {
        [void]$InstallRoots.Add((Assert-SafeLocalPath $full))
    }
}

Add-InstallRoot $CanonicalInstallRoot -Canonical
if (Test-Path -LiteralPath $ProgramsRoot -PathType Container) {
    foreach ($directory in @(Get-ChildItem -LiteralPath $ProgramsRoot -Directory -Force `
            -ErrorAction SilentlyContinue)) {
        if ($directory.Name -match "^SEED(?:$|[-_ (].*)") {
            Add-InstallRoot $directory.FullName
        }
    }
}

$UninstallEntries = New-Object "System.Collections.Generic.List[object]"
$UninstallRegistry = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
if (Test-Path $UninstallRegistry) {
    foreach ($key in Get-ChildItem $UninstallRegistry -ErrorAction SilentlyContinue) {
        $entry = Get-ItemProperty $key.PSPath -ErrorAction SilentlyContinue
        if ($null -eq $entry) {
            continue
        }
        $displayProperty = $entry.PSObject.Properties["DisplayName"]
        if ($null -eq $displayProperty -or
            [string]$displayProperty.Value -notmatch "^SEED(?:\s|$)") {
            continue
        }
        $locationProperty = $entry.PSObject.Properties["InstallLocation"]
        $location = ""
        if ($null -ne $locationProperty) {
            $location = [string]$locationProperty.Value
        }
        if (-not [string]::IsNullOrWhiteSpace($location)) {
            Add-InstallRoot $location
        }
        [void]$UninstallEntries.Add([PSCustomObject]@{
            KeyPath = $key.PSPath
            InstallLocation = $location
        })
    }
}

$DataRoot = Assert-SafeLocalPath $DataRoot
if (-not (Test-IsUnder $BackupRoot $LocalRoot)) {
    throw "BackupRoot deve essere sotto LOCALAPPDATA: $BackupRoot"
}
if ((Test-IsUnder $BackupRoot $DataRoot) -or
    [string]::Equals($BackupRoot, $DataRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "BackupRoot non puo essere dentro la root dati che verra rimossa."
}

$scriptPath = [string]$MyInvocation.MyCommand.Path
if (-not [string]::IsNullOrWhiteSpace($scriptPath)) {
    foreach ($root in $InstallRoots) {
        if (Test-IsUnder $scriptPath $root) {
            throw "Copia lo script in Download o Desktop prima di eseguirlo."
        }
    }
}

$MemorySources = @(Get-MemorySources)

Write-Step "installazioni rilevate: $($InstallRoots.Count)"
foreach ($root in $InstallRoots) {
    Write-Host "  - $root"
}
Write-Step "root dati da azzerare: $DataRoot"
Write-Step "file memoria da preservare: $($MemorySources.Count)"
foreach ($memory in $MemorySources) {
    Write-Host "  - $memory"
}
Write-Step "backup memoria: $BackupDirectory"

if ($WhatIfPreference) {
    Write-Step "modalita WhatIf: nessuna modifica eseguita."
    return
}

if (-not $Yes) {
    Write-Host ""
    Write-Host "Verranno eliminati runtime, modelli, config/key, lineage, workspace e backup SEED."
    Write-Host "Rimarra solo la memoria SQLite. Le key provider dovranno essere reinserite."
    $answer = Read-Host "Scrivi RESET-SEED per continuare"
    if ($answer -cne "RESET-SEED") {
        Write-Step "annullato dall'utente."
        return
    }
}

$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
if (Get-ItemProperty -Path $RunKey -Name "SEED" -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess("HKCU Run/SEED", "rimuovere avvio automatico")) {
        Remove-ItemProperty -Path $RunKey -Name "SEED" -Force
    }
}

Stop-SeedProcesses
$MemorySources = @(Get-MemorySources)

if (Test-Path -LiteralPath (Join-Path $DataRoot "data\seed.db")) {
    Assert-SqliteHeader (Join-Path $DataRoot "data\seed.db")
}

if (Test-Path -LiteralPath $BackupDirectory) {
    throw "La directory backup esiste gia: $BackupDirectory. Riprova tra un secondo."
}
if ($PSCmdlet.ShouldProcess($BackupDirectory, "creare backup verificato memoria")) {
    New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
}

$BackupHashes = @{}
foreach ($source in $MemorySources) {
    $destination = Join-Path $BackupDirectory ([IO.Path]::GetFileName($source))
    Copy-Item -LiteralPath $source -Destination $destination -Force
    $sourceHash = Get-FileDigest $source
    $backupHash = Get-FileDigest $destination
    if ($sourceHash -ne $backupHash) {
        throw "Verifica backup fallita per $source. Nessun dato verra cancellato."
    }
    $BackupHashes[[IO.Path]::GetFileName($source)] = $backupHash
}

foreach ($root in @($InstallRoots)) {
    foreach ($uninstaller in @(Get-ChildItem -LiteralPath $root -Filter "unins*.exe" -File -ErrorAction SilentlyContinue)) {
        if ($PSCmdlet.ShouldProcess($uninstaller.FullName, "eseguire uninstaller silenzioso")) {
            Write-Step "esecuzione uninstaller $($uninstaller.FullName)"
            $process = Start-Process -FilePath $uninstaller.FullName `
                -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" `
                -Wait -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Warning "Uninstaller terminato con codice $($process.ExitCode); rimuovo i residui gestiti."
            }
        }
    }
}

foreach ($root in @($InstallRoots)) {
    if (Test-Path -LiteralPath $root) {
        $safe = Assert-SafeLocalPath $root
        if ($PSCmdlet.ShouldProcess($safe, "rimuovere installazione SEED")) {
            Remove-Item -LiteralPath $safe -Recurse -Force
        }
    }
}

foreach ($entry in @($UninstallEntries)) {
    if (Test-Path -LiteralPath $entry.KeyPath) {
        if ($PSCmdlet.ShouldProcess($entry.KeyPath, "rimuovere registrazione uninstall SEED residua")) {
            Remove-Item -LiteralPath $entry.KeyPath -Recurse -Force
        }
    }
}

$ShortcutPaths = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "SEED.lnk"),
    (Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\SEED.lnk")
)
foreach ($shortcut in $ShortcutPaths) {
    if (Test-Path -LiteralPath $shortcut -PathType Leaf) {
        if ($PSCmdlet.ShouldProcess($shortcut, "rimuovere shortcut SEED")) {
            Remove-Item -LiteralPath $shortcut -Force
        }
    }
}

if (Test-Path -LiteralPath $DataRoot) {
    if ($PSCmdlet.ShouldProcess($DataRoot, "rimuovere tutti i dati SEED eccetto memoria salvata")) {
        Remove-Item -LiteralPath $DataRoot -Recurse -Force
    }
}

$RestoredData = Join-Path $DataRoot "data"
New-Item -ItemType Directory -Path $RestoredData -Force | Out-Null
foreach ($name in $BackupHashes.Keys) {
    $source = Join-Path $BackupDirectory $name
    $destination = Join-Path $RestoredData $name
    Copy-Item -LiteralPath $source -Destination $destination -Force
    if ((Get-FileDigest $destination) -ne $BackupHashes[$name]) {
        throw "Ripristino memoria fallito per $name. La copia resta in $BackupDirectory"
    }
}

$Report = @(
    "SEED tester clean reset",
    "timestamp=$Timestamp",
    "data_root=$DataRoot",
    "memory_backup=$BackupDirectory",
    "memory_files=$($BackupHashes.Keys -join ',')",
    "install_roots_removed=$($InstallRoots -join ';')",
    "result=runtime_config_lineage_workspace_removed_memory_restored"
)
$Report | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host ""
Write-Step "reset completato."
Write-Step "memoria ripristinata in: $RestoredData"
Write-Step "copia di sicurezza conservata in: $BackupDirectory"
Write-Step "ora installa la release completa piu recente da:"
Write-Host "https://github.com/Criss-0429/Seed_ai/releases/latest"
Write-Host "Le key provider e le preferenze non presenti nella memoria dovranno essere configurate di nuovo."
