[CmdletBinding()]
param(
    [switch]$StartVm,
    [switch]$InstallTestDependencies,
    [string]$IdentityFile = (Join-Path $env:USERPROFILE '.ssh\id_ed25519'),
    [string]$SshHost = '127.0.0.1',
    [ValidateRange(1, 65535)]
    [int]$SshPort = 2222,
    [string]$SshUser = 'copilot',
    [string]$VirtualenvPath = '/opt/superharry/venv',
    [ValidateRange(30, 900)]
    [int]$StartupTimeoutSeconds = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ssh = (Get-Command ssh.exe -ErrorAction Stop).Source
$scp = (Get-Command scp.exe -ErrorAction Stop).Source
$tar = (Get-Command tar.exe -ErrorAction Stop).Source
$devVm = Join-Path $PSScriptRoot 'dev-vm.ps1'
$vmProcess = $null
$vmStdout = Join-Path $env:TEMP 'superharry-dev-vm.stdout.log'
$vmStderr = Join-Path $env:TEMP 'superharry-dev-vm.stderr.log'
$stageId = [guid]::NewGuid().ToString('N')
$archiveName = "superharry-dependencies-$stageId.tar.gz"
$archivePath = Join-Path $env:TEMP $archiveName
$remoteArchive = "/tmp/$archiveName"
$remoteStage = "/tmp/superharry-dependencies-$stageId"
$commonSsh = @('-i', $IdentityFile, '-p', [string]$SshPort, '-o', 'BatchMode=yes',
    '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=8')
$target = "$SshUser@$SshHost"

if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    throw "SSH identity file was not found: $IdentityFile"
}
if ($VirtualenvPath -notmatch '^/[A-Za-z0-9._/-]+$') {
    throw 'VirtualenvPath must be an absolute POSIX path containing only letters, digits, dot, underscore, slash, or hyphen.'
}

function Test-SshReady {
    param([string]$HostName, [int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(1000, $false)) { return $false }
        $client.EndConnect($pending)
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

try {
    if ($StartVm) {
        if (Test-SshReady -HostName $SshHost -Port $SshPort) {
            throw "SSH is already listening on ${SshHost}:$SshPort; omit -StartVm to provision that running VM."
        }
        $powershell = Join-Path $PSHOME 'powershell.exe'
        $vmProcess = Start-Process -FilePath $powershell -WindowStyle Hidden -PassThru `
            -WorkingDirectory $repositoryRoot -RedirectStandardOutput $vmStdout -RedirectStandardError $vmStderr `
            -ArgumentList @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $devVm, '-Mode', 'Run', '-NonInteractive')
        Write-Host "Started dev VM launcher PID $($vmProcess.Id); waiting for SSH on ${SshHost}:$SshPort."
        $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
        $guestReady = $false
        while (-not $guestReady) {
            if ($vmProcess.HasExited) {
                throw "VM launcher exited with code $($vmProcess.ExitCode). See $vmStderr"
            }
            if ([DateTime]::UtcNow -ge $deadline) {
                throw "Timed out waiting for VM SSH. The VM launcher is still running as PID $($vmProcess.Id); see $vmStdout and $vmStderr"
            }
            if (Test-SshReady -HostName $SshHost -Port $SshPort) {
                & $ssh @commonSsh $target 'sudo -n true' *> $null
                $guestReady = ($LASTEXITCODE -eq 0)
            }
            if ($guestReady) { break }
            Start-Sleep -Seconds 2
        }
    }

    & $ssh @commonSsh $target 'id; sudo -n true'
    if ($LASTEXITCODE -ne 0) {
        throw "SSH or passwordless sudo validation failed for $target."
    }

    & $tar -czf $archivePath -C $repositoryRoot `
        requirements.txt requirements-test.txt scripts/install-vm-dependencies.sh scripts/verify_sqlcipher_binding.py
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare the dependency bundle (tar exit $LASTEXITCODE)." }

    & $scp -i $IdentityFile -P $SshPort -o BatchMode=yes -o StrictHostKeyChecking=yes `
        $archivePath "${target}:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw "Could not upload dependency bundle (scp exit $LASTEXITCODE)." }

    $testDependencyFlag = if ($InstallTestDependencies) { '1' } else { '0' }
    $guestScript = @"
set -eu
stage='$remoteStage'
archive='$remoteArchive'
mkdir -m 700 "`$stage"
tar -xzf "`$archive" -C "`$stage"
sudo -n env SUPERHARRY_VENV_PATH='$VirtualenvPath' INSTALL_TEST_DEPENDENCIES='$testDependencyFlag' bash "`$stage/scripts/install-vm-dependencies.sh"
rm -rf -- "`$stage" "`$archive"
"@
    $guestEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($guestScript))
    & $ssh @commonSsh $target "bash -lc 'echo $guestEncoded | base64 -d | bash'"
    if ($LASTEXITCODE -ne 0) {
        throw "VM dependency installation failed. The uploaded bundle remains under $remoteStage for diagnosis."
    }

    if ($vmProcess) {
        Write-Host "VM remains running. Launcher PID: $($vmProcess.Id). QEMU output: $vmStdout"
    }
} finally {
    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }
}
