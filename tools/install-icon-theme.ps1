<#
.SYNOPSIS
    Download and install the Breeze icon theme for python-manatools on Windows.

.DESCRIPTION
    Windows has no freedesktop icon theme, so the Qt, GTK and web backends
    find no named icons (document-open, edit-copy, ...) there.  This script
    downloads the KDE Breeze icon release tarball, verifies its SHA-256,
    installs the icons into <Destination>\breeze with a generated index.theme,
    and adds <Destination> to the user's MANATOOLS_ICON_PATH, which
    python-manatools searches for icon themes.

    The archive contains symbolic links; they are installed as plain copies
    of their targets, so neither Developer Mode nor admin rights are needed.

    Python 3 (already required by python-manatools) unpacks the .tar.xz.

.PARAMETER Version
    Breeze icons release (a KDE Frameworks version) to download.

.PARAMETER Url
    Download the tarball from this URL instead of download.kde.org.

.PARAMETER Sha256
    Expected SHA-256 of the tarball.  Defaults to the pinned hash of the
    default release, otherwise to the .sha256 file published next to it.

.PARAMETER Destination
    Icon theme root; the theme is installed into its "breeze" subfolder.

.PARAMETER Python
    Path to python.exe.  Defaults to the "py -3" launcher, then python.

.PARAMETER NoEnvironment
    Do not add Destination to the user's MANATOOLS_ICON_PATH.

.PARAMETER Force
    Reinstall even if the theme is already present.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\install-icon-theme.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\install-icon-theme.ps1 -Destination "$env:VIRTUAL_ENV\share\icons" -NoEnvironment
#>
[CmdletBinding()]
param(
    [string]$Version = '6.31.0',
    [string]$Url,
    [string]$Sha256,
    [string]$Destination = (Join-Path $env:LOCALAPPDATA 'manatools\icons'),
    [string]$Python,
    [switch]$NoEnvironment,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# Invoke-WebRequest is very slow on Windows PowerShell 5.1 with the progress bar
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$PinnedSha256 = @{
    '6.31.0' = '82ab1c13f782cb37176e7c13c5fb2c77536a65f24b85d09127f3575f917fb56d'
}

# Unpacks the icons/ tree of the tarball into <target>.  Members are checked
# to stay inside the staging folder, symlinks become plain copies of their
# targets, and index.theme is assembled the way breeze-icons' CMake build
# does it.
$Extractor = @'
import os, shutil, sys, tarfile

archive, staging, target = sys.argv[1:4]

def inside(base, path):
    base = os.path.realpath(base)
    path = os.path.realpath(path)
    return path == base or path.startswith(base + os.sep)

with tarfile.open(archive) as tar:
    members = tar.getmembers()
    top = members[0].name.split('/')[0]
    icons = top + '/icons/'
    license_file = top + '/COPYING-ICONS'
    regular, links = [], {}
    for m in members:
        if not (m.name.startswith(icons) or m.name == license_file):
            continue
        if not inside(staging, os.path.join(staging, m.name)):
            sys.exit('unsafe path in archive: ' + m.name)
        if m.issym():
            dest = os.path.normpath(os.path.join(os.path.dirname(m.name), m.linkname))
            links[m.name] = dest.replace(os.sep, '/')
        elif m.isfile() or m.isdir():
            regular.append(m)
    if not any(m.name.startswith(icons) for m in regular):
        sys.exit('no icons/ folder in archive; is this a breeze-icons tarball?')
    kwargs = {'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}
    tar.extractall(staging, members=regular, **kwargs)

# Copy link targets from the extracted files: Windows only creates symlinks
# in Developer Mode, and tarfile's own fallback re-reads the .xz stream from
# the start for every link, which takes minutes.  Links to folders (the
# HiDPI aliases such as actions/22@2x -> 22) are skipped: the icons are SVG
# and scale anyway.
for name, dest in links.items():
    seen = {name}
    while dest in links and dest not in seen:
        seen.add(dest)
        dest = links[dest]
    src = os.path.join(staging, dest)
    if dest.startswith(icons) and os.path.isfile(src):
        link_path = os.path.join(staging, name)
        os.makedirs(os.path.dirname(link_path), exist_ok=True)
        shutil.copyfile(src, link_path)

src = os.path.join(staging, top, 'icons')
if os.path.exists(target):
    shutil.rmtree(target)
os.makedirs(target)
for name in sorted(os.listdir(src)):
    path = os.path.join(src, name)
    if os.path.isdir(path):
        shutil.copytree(path, os.path.join(target, name))
with open(os.path.join(target, 'index.theme'), 'w', encoding='utf-8', newline='\n') as out:
    for part in ('breeze.theme.in', 'commonthemeinfo.theme.in'):
        with open(os.path.join(src, part), encoding='utf-8') as f:
            out.write(f.read())
if os.path.isfile(os.path.join(staging, license_file)):
    shutil.copy(os.path.join(staging, license_file), target)
print(sum(len(files) for _, _, files in os.walk(target)))
'@

function Find-Python {
    if ($Python) {
        return @{ Exe = $Python; Args = @() }
    }
    foreach ($candidate in @('py -3', 'python', 'python3')) {
        $parts = $candidate -split ' '
        $exe = $parts[0]
        $pre = @($parts | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
            continue
        }
        # Rejects the Microsoft Store "python" alias, which only opens the Store.
        # Windows PowerShell 5.1 turns redirected native stderr into
        # terminating errors under 'Stop', so probe with 'Continue'.
        $ErrorActionPreference = 'Continue'
        $out = & $exe @pre -c 'import sys; print(sys.version_info[0])' 2>$null
        $ok = ($LASTEXITCODE -eq 0 -and "$out".Trim() -eq '3')
        $ErrorActionPreference = 'Stop'
        if ($ok) {
            return @{ Exe = $exe; Args = $pre }
        }
    }
    throw 'Python 3 not found; install it or pass -Python <path\to\python.exe>.'
}

function Get-ExpectedHash([string]$TarballUrl, [string]$DefaultUrl, [string]$WorkDir) {
    if ($Sha256) {
        return $Sha256
    }
    if ($TarballUrl -eq $DefaultUrl -and $PinnedSha256.ContainsKey($Version)) {
        return $PinnedSha256[$Version]
    }
    # Same-origin checksum: catches corrupt downloads, not a compromised server
    $sumFile = Join-Path $WorkDir 'tarball.sha256'
    try {
        Invoke-WebRequest -Uri "$TarballUrl.sha256" -OutFile $sumFile -UseBasicParsing
    } catch {
        throw "No checksum available for $TarballUrl; pass -Sha256."
    }
    return ((Get-Content -Raw $sumFile).Trim() -split '\s+')[0]
}

function Add-IconPath([string]$Dir) {
    $current = [Environment]::GetEnvironmentVariable('MANATOOLS_ICON_PATH', 'User')
    $entries = @()
    if ($current) {
        $entries = @($current -split ';' | Where-Object { $_ })
    }
    if ($entries -notcontains $Dir) {
        [Environment]::SetEnvironmentVariable('MANATOOLS_ICON_PATH', (($entries + $Dir) -join ';'), 'User')
        Write-Host "Added $Dir to the user MANATOOLS_ICON_PATH (new terminals pick it up)."
    }
    $session = @()
    if ($env:MANATOOLS_ICON_PATH) {
        $session = @($env:MANATOOLS_ICON_PATH -split ';' | Where-Object { $_ })
    }
    if ($session -notcontains $Dir) {
        $env:MANATOOLS_ICON_PATH = ($session + $Dir) -join ';'
    }
}

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Invalid -Version '$Version'; expected e.g. 6.31.0."
}
$Destination = [IO.Path]::GetFullPath($Destination)
$themeDir = Join-Path $Destination 'breeze'

if ((Test-Path (Join-Path $themeDir 'index.theme')) -and -not $Force) {
    Write-Host "Breeze icons already installed in $themeDir (use -Force to reinstall)."
} else {
    $series = ($Version -split '\.')[0..1] -join '.'
    $defaultUrl = "https://download.kde.org/stable/frameworks/$series/breeze-icons-$Version.tar.xz"
    if (-not $Url) {
        $Url = $defaultUrl
    }
    $py = Find-Python
    $work = Join-Path ([IO.Path]::GetTempPath()) ('manatools-icons-' + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $work | Out-Null
    $staged = $null
    try {
        $archive = Join-Path $work 'breeze-icons.tar.xz'
        Write-Host "Downloading $Url"
        Invoke-WebRequest -Uri $Url -OutFile $archive -UseBasicParsing

        $expected = Get-ExpectedHash $Url $defaultUrl $work
        $actual = (Get-FileHash -Algorithm SHA256 $archive).Hash
        if ($actual -ne $expected) {
            throw "SHA-256 mismatch for $Url`n  expected $expected`n  got      $actual"
        }

        $script = Join-Path $work 'extract.py'
        Set-Content -Path $script -Value $Extractor -Encoding ASCII
        New-Item -ItemType Directory -Force -Path $Destination | Out-Null
        $staged = Join-Path $Destination 'breeze.new'
        Write-Host 'Unpacking icons...'
        $pyArgs = $py.Args
        $count = & $py.Exe @pyArgs -I $script $archive (Join-Path $work 'staging') $staged
        if ($LASTEXITCODE -ne 0) {
            throw "Unpacking failed (exit code $LASTEXITCODE)."
        }
        if (Test-Path $themeDir) {
            Remove-Item -Recurse -Force $themeDir
        }
        Move-Item $staged $themeDir
        Write-Host "Installed $count files into $themeDir"
        Write-Host 'Breeze icons are licensed under the LGPL; see COPYING-ICONS there.'
    } finally {
        Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
        if ($staged -and (Test-Path $staged)) {
            Remove-Item -Recurse -Force $staged -ErrorAction SilentlyContinue
        }
    }
}

if (-not $NoEnvironment) {
    Add-IconPath $Destination
}
