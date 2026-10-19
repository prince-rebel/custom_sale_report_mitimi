<#
.SYNOPSIS
  Met a jour le module Odoo custom_sale_report_mitimi sur le serveur Windows du client.

.DESCRIPTION
  Sauvegarde le module (et la base), recupere la nouvelle version, met a jour le module
  dans Odoo et redemarre le service. En cas d'echec, l'ancien module est restaure.

.EXAMPLE
  .\mise_a_jour_module.ps1                        # derniere version taguee du depot GitHub
  .\mise_a_jour_module.ps1 -Tag v1.2.0            # une version precise
  .\mise_a_jour_module.ps1 -FromFolder C:\temp\custom_sale_report_mitimi   # sans GitHub (dossier copie a la main)
  .\mise_a_jour_module.ps1 -Rollback              # revient a la derniere sauvegarde

  A lancer dans PowerShell "Executer en tant qu'administrateur".
  Prerequis pour le mode GitHub : Git for Windows installe + cle de deploiement (lecture seule).
#>
[CmdletBinding()]
param(
    [string]$Tag,
    [string]$FromFolder,
    [switch]$Rollback,
    [switch]$SkipDbBackup
)

$ErrorActionPreference = 'Stop'

# ======================= CONFIGURATION (a adapter une seule fois) =======================
$ModuleName   = 'custom_sale_report_mitimi'
$RepoUrl      = 'https://github.com/prince-rebel/custom_sale_report_mitimi.git'   # depot public : pas de cle necessaire
$OdooRoot     = 'C:\Program Files\Odoo19'
$AddonsPath   = Join-Path $OdooRoot 'server\odoo\addons'      # dossier ou le module est installe
$Python       = Join-Path $OdooRoot 'python\python.exe'
$OdooBin      = Join-Path $OdooRoot 'server\odoo-bin'
$OdooConf     = Join-Path $OdooRoot 'server\odoo.conf'
$OdooService  = 'odoo-server-19.0'
$DbName       = 'mitmi'                                       # vide = db_name de odoo.conf
$PgDump       = Join-Path $OdooRoot 'PostgreSQL\bin\pg_dump.exe'
$WorkDir      = 'C:\Deploiement\mitimi'
$DeployKey    = Join-Path $WorkDir 'deploy_key'               # cle privee SSH, lecture seule
$KeepBackups  = 10
# ========================================================================================

if ((Test-Path 'C:\Program Files\Git\cmd\git.exe') -and ($env:Path -notlike '*Program Files\Git\cmd*')) {
    $env:Path += ';C:\Program Files\Git\cmd'
}

$RepoDir    = Join-Path $WorkDir 'depot'
$BackupRoot = Join-Path $WorkDir 'sauvegardes'
$Dest       = Join-Path $AddonsPath $ModuleName

function Log([string]$Msg) { Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Msg) }

function Get-OdooConf([string]$Key, [string]$Default = '') {
    $line = Select-String -Path $OdooConf -Pattern "^\s*$Key\s*=\s*(.*)$" | Select-Object -First 1
    if ($line) {
        $v = $line.Matches[0].Groups[1].Value.Trim()
        if ($v -and $v -ne 'False') { return $v }
    }
    return $Default
}

function Invoke-Git {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try {
        $out = & git @args 2>&1 | ForEach-Object { "$_" }
        if ($LASTEXITCODE -ne 0) { throw ("git {0} a echoue : {1}" -f ($args -join ' '), ($out -join ' ')) }
        return $out
    }
    finally { $ErrorActionPreference = $old }
}

function Copy-Module([string]$From, [string]$To) {
    New-Item -ItemType Directory -Force -Path $To | Out-Null
    robocopy $From $To /MIR /XD .git __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy a echoue (code $LASTEXITCODE)" }
    $global:LASTEXITCODE = 0
}

function Stop-Odoo {
    if ((Get-Service $OdooService).Status -ne 'Stopped') {
        Log "Arret du service $OdooService"
        Stop-Service $OdooService -Force
        (Get-Service $OdooService).WaitForStatus('Stopped', '00:01:30')
    }
}

function Start-Odoo {
    Log "Demarrage du service $OdooService"
    Start-Service $OdooService
}

# ---------- Controles ----------
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Lancez ce script dans PowerShell en administrateur."
}
foreach ($p in @($AddonsPath, $Python, $OdooBin, $OdooConf)) {
    if (-not (Test-Path $p)) { throw "Introuvable : $p (corrigez la section CONFIGURATION)" }
}
if (-not $DbName) { $DbName = Get-OdooConf 'db_name' }
if (-not $DbName) { throw "Nom de base inconnu : renseignez `$DbName dans la section CONFIGURATION." }
New-Item -ItemType Directory -Force -Path $WorkDir, $BackupRoot | Out-Null

# ---------- Retour arriere ----------
if ($Rollback) {
    $last = Get-ChildItem $BackupRoot -Directory | Sort-Object Name -Descending |
            Where-Object { Test-Path (Join-Path $_.FullName 'module') } | Select-Object -First 1
    if (-not $last) { throw "Aucune sauvegarde du module dans $BackupRoot" }
    Log "Retour arriere vers la sauvegarde $($last.Name)"
    Stop-Odoo
    Copy-Module (Join-Path $last.FullName 'module') $Dest
    Start-Odoo
    Log "Module restaure. La base n'est pas modifiee (dump eventuel : $($last.FullName)\base.dump)."
    Log "Si besoin, mettre a jour le module restaure : Applications > $ModuleName > Mettre a jour."
    return
}

# ---------- 1. Recuperation de la nouvelle version ----------
$Version = ''
if ($FromFolder) {
    $Src = $FromFolder
    $Version = "dossier:$FromFolder"
}
else {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git n'est pas installe (https://git-scm.com/download/win)." }
    if (Test-Path $DeployKey) {
        $env:GIT_SSH_COMMAND = "ssh -i `"$DeployKey`" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    }
    if (-not (Test-Path (Join-Path $RepoDir '.git'))) {
        Log "Clonage du depot dans $RepoDir"
        Invoke-Git clone $RepoUrl $RepoDir | Out-Null
    }
    Push-Location $RepoDir
    try {
        Log "Recuperation des versions"
        Invoke-Git fetch --tags --prune --force | Out-Null
        if (-not $Tag) { $Tag = (Invoke-Git tag --sort=-v:refname | Select-Object -First 1) }
        if (-not $Tag) { throw "Aucune version taguee dans le depot (creer un tag, ex. v1.0.0)." }
        Log "Version a deployer : $Tag"
        Invoke-Git checkout --force $Tag | Out-Null
    }
    finally { Pop-Location }
    $Version = $Tag
    $Src = Join-Path $RepoDir $ModuleName
    if (-not (Test-Path $Src)) { $Src = $RepoDir }
}
if (-not (Test-Path (Join-Path $Src '__manifest__.py'))) { throw "Pas de __manifest__.py dans $Src" }

# ---------- 2. Sauvegardes ----------
$Stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$Backup = Join-Path $BackupRoot $Stamp
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
$HadModule = Test-Path $Dest
if ($HadModule) {
    Log "Sauvegarde du module actuel"
    Copy-Module $Dest (Join-Path $Backup 'module')
}
if (-not $SkipDbBackup) {
    if (-not (Test-Path $PgDump)) { throw "pg_dump introuvable ($PgDump). Corrigez `$PgDump ou utilisez -SkipDbBackup." }
    Log "Sauvegarde de la base $DbName (peut prendre du temps)"
    $env:PGPASSWORD = Get-OdooConf 'db_password'
    $dbHost = Get-OdooConf 'db_host' 'localhost'
    $dbPort = Get-OdooConf 'db_port' '5432'
    $dbUser = Get-OdooConf 'db_user' 'openpg'
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & $PgDump -h $dbHost -p $dbPort -U $dbUser -Fc -f (Join-Path $Backup 'base.dump') $DbName 2>&1 | Out-Null
    $dumpCode = $LASTEXITCODE
    $ErrorActionPreference = $old
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    if ($dumpCode -ne 0) { throw "Sauvegarde de la base echouee (code $dumpCode). Mise a jour annulee, rien n'a ete modifie." }
}

# ---------- 3. Installation et mise a jour dans Odoo ----------
$LogFile = Join-Path $Backup 'mise_a_jour_odoo.log'
$failed  = $false
try {
    Stop-Odoo
    Log "Copie du module dans $Dest"
    Copy-Module $Src $Dest

    Log "Mise a jour du module dans Odoo (base $DbName)"
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & $Python $OdooBin -c $OdooConf -d $DbName -u $ModuleName --stop-after-init --no-http 2>&1 |
        Tee-Object -FilePath $LogFile | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    $hasErrors = [bool](Select-String -Path $LogFile -Pattern 'CRITICAL|Failed to load registry|Traceback' -Quiet)
    if ($code -ne 0 -or $hasErrors) { $failed = $true }
}
catch {
    Log "ERREUR : $_"
    $failed = $true
}

# ---------- 4. Resultat ----------
if ($failed) {
    Log "ECHEC de la mise a jour. Restauration de l'ancien module."
    if ($HadModule) { Copy-Module (Join-Path $Backup 'module') $Dest }
    Start-Odoo
    Log "Ancien module remis en place, service redemarre. Journal : $LogFile"
    Log "Envoyez ce journal pour diagnostic. Dump de la base : $Backup\base.dump"
    exit 1
}

Start-Odoo
$mf = Get-Content (Join-Path $Dest '__manifest__.py') -Raw
$ver = if ($mf -match "'version'\s*:\s*'([^']+)'") { $Matches[1] } else { '?' }
"{0}  version module {1}  source {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm'), $ver, $Version |
    Add-Content (Join-Path $WorkDir 'historique_deploiements.txt')

Get-ChildItem $BackupRoot -Directory | Sort-Object Name -Descending | Select-Object -Skip $KeepBackups |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

Log "Termine : module $ModuleName en version $ver ($Version). Sauvegarde : $Backup"
