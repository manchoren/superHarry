[CmdletBinding()]
param(
    [ValidateSet('Validate', 'Install', 'Run')]
    [string]$Mode = 'Validate',
    [string]$FirmwareCodePath,
    [string]$FirmwareVarsPath,
    [string]$FirmwareCodeSha256,
    [string]$FirmwareVarsSha256,
    [string]$InstallerIso,
    [string]$InstallerSha256,
    [ValidateSet('debian-13.7-arm64-base.qcow2', 'debian-13-nocloud-configured-base.qcow2', 'debian-13-nocloud-arm64-base.qcow2')]
    [string]$RunBaseName = 'debian-13.7-arm64-base.qcow2',
    [switch]$ResumeInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:ExpectedSids = @(
    [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value,
    'S-1-5-18',
    'S-1-5-32-544'
)
$script:RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$script:VmRoot = [System.IO.Path]::GetFullPath('C:\superHarry-vm')
$script:QemuDirectory = 'C:\Program Files\qemu'
$script:QemuPath = Join-Path $script:QemuDirectory 'qemu-system-aarch64.exe'
$script:QemuImgPath = Join-Path $script:QemuDirectory 'qemu-img.exe'
$script:FirmwareDirectory = Join-Path $script:QemuDirectory 'share'
$script:ExpectedQemuVersionLine = 'QEMU emulator version 11.1.0 (v11.1.0-12130-ge470268ff4)'
$script:ExpectedQemuImgVersionLine = 'qemu-img version 11.1.0 (v11.1.0-12130-ge470268ff4)'
$script:ExpectedQemuSha256 = '952f897511177803722efed6fefe79bc3e7e5a51a026112dfc40f9a37fb0dad2'
$script:ExpectedQemuImgSha256 = '9d930582d0d574bb106d89982c547688e10b8f356192d302cc3d0ae4e8674534'
$script:BaseDiskName = 'debian-13.7-arm64-base.qcow2'
$script:DiskBytes = 32GB
$script:MinimumFreeBytes = 64GB

function Stop-WithError {
    param([Parameter(Mandatory)][string]$Message)
    throw $Message
}

function Resolve-FilePath {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Label
    )

    if (-not [System.IO.Path]::IsPathRooted($Path)) {
        Stop-WithError "$Label must be an absolute Windows path: $Path"
    }

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        Stop-WithError "$Label was not found: $fullPath"
    }
    if ((Get-Item -LiteralPath $fullPath -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Stop-WithError "$Label must not be a reparse point: $fullPath"
    }
    if ($fullPath.Contains(',')) {
        Stop-WithError "$Label path must not contain a comma because QEMU's drive options use comma separators: $fullPath"
    }
    return $fullPath
}

function Get-Sha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-Sha256 {
    param(
        [Parameter(Mandatory)][string]$Actual,
        [Parameter(Mandatory)][string]$Expected,
        [Parameter(Mandatory)][string]$Label
    )

    if ($Expected -notmatch '^[0-9a-fA-F]{64}$') {
        Stop-WithError "$Label SHA-256 must be supplied as exactly 64 hexadecimal characters."
    }
    if ($Actual -ne $Expected.ToLowerInvariant()) {
        Stop-WithError "$Label SHA-256 mismatch. Expected $($Expected.ToLowerInvariant()), got $Actual."
    }
}

function Invoke-Probe {
    param(
        [Parameter(Mandatory)][string]$Executable,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$Label
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()
    try {
        $quotedArguments = $Arguments | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }
        $process = Start-Process -FilePath $Executable -ArgumentList $quotedArguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $exitCode = $process.ExitCode
        $output = (@(Get-Content -LiteralPath $stdoutPath) + @(Get-Content -LiteralPath $stderrPath)) -join "`n"
    } finally {
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -ErrorAction SilentlyContinue
    }
    if ($exitCode -ne 0) {
        Stop-WithError "$Label probe failed with exit code $exitCode.`n$output"
    }
    return $output
}

function Assert-QemuCandidate {
    $script:QemuPath = Resolve-FilePath -Path $script:QemuPath -Label 'Selected QEMU executable'
    $script:QemuImgPath = Resolve-FilePath -Path $script:QemuImgPath -Label 'Selected sibling qemu-img executable'
    $qemuHash = Get-Sha256 -Path $script:QemuPath
    Assert-Sha256 -Actual $qemuHash -Expected $script:ExpectedQemuSha256 -Label 'Selected QEMU executable'
    $imgHash = Get-Sha256 -Path $script:QemuImgPath
    Assert-Sha256 -Actual $imgHash -Expected $script:ExpectedQemuImgSha256 -Label 'Selected sibling qemu-img executable'
    $qemuVersion = Invoke-Probe -Executable $script:QemuPath -Arguments @('--version') -Label 'QEMU version'
    if (($qemuVersion -split "`n")[0].Trim() -cne $script:ExpectedQemuVersionLine) {
        Stop-WithError "Expected exact QEMU build '$($script:ExpectedQemuVersionLine)'; the executable reported:`n$qemuVersion"
    }
    $imgVersion = Invoke-Probe -Executable $script:QemuImgPath -Arguments @('--version') -Label 'qemu-img version'
    if (($imgVersion -split "`n")[0].Trim() -cne $script:ExpectedQemuImgVersionLine) {
        Stop-WithError "Expected exact sibling qemu-img build '$($script:ExpectedQemuImgVersionLine)'; it reported:`n$imgVersion"
    }

    $machines = Invoke-Probe -Executable $script:QemuPath -Arguments @('-machine', 'help') -Label 'QEMU machine list'
    if ($machines -notmatch '(?m)^\s*virt-11\.1(?:\s|$)') {
        Stop-WithError 'This QEMU build does not advertise the exact required machine virt-11.1. Refusing to fall back to virt.'
    }
    $cpus = Invoke-Probe -Executable $script:QemuPath -Arguments @('-cpu', 'help') -Label 'QEMU CPU list'
    if ($cpus -notmatch '(?m)^\s*cortex-a76(?:\s|$)') {
        Stop-WithError 'This QEMU build does not advertise the selected CPU cortex-a76.'
    }
    $devices = Invoke-Probe -Executable $script:QemuPath -Arguments @('-device', 'help') -Label 'QEMU device list'
    foreach ($device in @('virtio-blk-device', 'virtio-scsi-device', 'scsi-cd', 'virtio-net-pci', 'pcie-root-port', 'virtio-serial-device', 'virtserialport')) {
        $devicePattern = '(?m)^\s*(?:name\s+)?["'']?{0}["'']?(?:\s|,|$)' -f [regex]::Escape($device)
        if ($devices -notmatch $devicePattern) {
            Stop-WithError "This QEMU build does not advertise the required device $device."
        }
    }

    Write-Host "QEMU: $($script:QemuPath)"
    Write-Host "QEMU SHA-256: $qemuHash"
    Write-Host ($qemuVersion.Trim())
    Write-Host "qemu-img: $($script:QemuImgPath)"
    Write-Host "qemu-img SHA-256: $imgHash"
    Write-Host ($imgVersion.Trim())
    Write-Host 'Machine: virt-11.1 (exact identifier confirmed)'
    Write-Host 'CPU/devices: cortex-a76, virtio-blk-device, virtio-scsi-device, scsi-cd, pcie-root-port, virtio-net-pci, virtio-serial-device, virtserialport'
}

function Get-ExpectedFirmwarePins {
    if ([string]::IsNullOrWhiteSpace($FirmwareCodePath) -or
        [string]::IsNullOrWhiteSpace($FirmwareVarsPath) -or
        [string]::IsNullOrWhiteSpace($FirmwareCodeSha256) -or
        [string]::IsNullOrWhiteSpace($FirmwareVarsSha256)) {
        Stop-WithError 'Firmware file inputs are required. Pass explicit -FirmwareCodePath, -FirmwareVarsPath and both SHA-256 pins; no firmware path is defaulted.'
    }

    $script:FirmwareCodePath = Resolve-FilePath -Path $FirmwareCodePath -Label 'AArch64 firmware code image'
    $script:FirmwareVarsPath = Resolve-FilePath -Path $FirmwareVarsPath -Label 'AArch64 firmware VARS template'
    if ([System.IO.Path]::GetFullPath($script:FirmwareCodePath) -ine (Join-Path $script:FirmwareDirectory 'edk2-aarch64-code.fd') -or
        [System.IO.Path]::GetFullPath($script:FirmwareVarsPath) -ine (Join-Path $script:FirmwareDirectory 'edk2-arm-vars.fd')) {
        Stop-WithError "Firmware paths must be the selected files under $($script:FirmwareDirectory)."
    }
    if ($script:FirmwareCodePath -ieq $script:FirmwareVarsPath) {
        Stop-WithError 'Firmware code and VARS template must be distinct files.'
    }
    $script:FirmwareCodeHash = Get-Sha256 -Path $script:FirmwareCodePath
    $script:FirmwareVarsHash = Get-Sha256 -Path $script:FirmwareVarsPath
    Assert-Sha256 -Actual $script:FirmwareCodeHash -Expected $FirmwareCodeSha256 -Label 'Firmware code'
    Assert-Sha256 -Actual $script:FirmwareVarsHash -Expected $FirmwareVarsSha256 -Label 'Firmware VARS template'
    if ($script:FirmwareCodeHash -ne '47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d' -or
        $script:FirmwareVarsHash -ne 'b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f') {
        Stop-WithError 'This draft is pinned to the owner-selected bundled QEMU firmware code/VARS pair. The supplied files do not match both selected firmware hashes.'
    }
    Write-Host "Firmware code SHA-256: $($script:FirmwareCodeHash)"
    Write-Host "Firmware VARS SHA-256: $($script:FirmwareVarsHash)"
}

function Get-ExpectedAclSids {
    return @($script:ExpectedSids | Sort-Object -Unique)
}

function Assert-RestrictedAcl {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][bool]$Directory
    )

    $acl = Get-Acl -LiteralPath $Path
    if ($Directory -and -not $acl.AreAccessRulesProtected) {
        Stop-WithError "superHarry-vm ACL still inherits permissions from its parent: $Path"
    }
    $rules = @($acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]))
    $expected = Get-ExpectedAclSids
    if ($rules.Count -ne $expected.Count) {
        Stop-WithError "Unexpected number of ACL entries on $Path; expected only current user, SYSTEM, and local Administrators."
    }

    $actualSids = @()
    foreach ($rule in $rules) {
        $sid = $rule.IdentityReference.Value
        $actualSids += $sid
        if ($sid -notin $expected -or
            $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or
            $rule.FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl) {
            Stop-WithError "Unexpected ACL entry on $Path for SID $sid."
        }
        if ($Directory) {
            if ($rule.IsInherited -or
                $rule.InheritanceFlags -ne ([System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit)) {
                Stop-WithError "Unexpected inheritance flags on superHarry-vm ACL entry for SID $sid."
            }
        } elseif (-not $rule.IsInherited) {
            Stop-WithError "Unexpected explicit ACL entry on VM file $Path for SID $sid."
        }
    }
    if (@($actualSids | Sort-Object -Unique) -join ',' -ne ($expected -join ',')) {
        Stop-WithError "The ACL on $Path does not contain exactly the expected principals."
    }
}

function Set-NewVmRootAcl {
    if (Test-Path -LiteralPath $script:VmRoot) {
        if ((Get-Item -LiteralPath $script:VmRoot -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            Stop-WithError "superHarry-vm must not be a reparse point: $script:VmRoot"
        }
        Assert-RestrictedAcl -Path $script:VmRoot -Directory $true
        return
    }

    New-Item -ItemType Directory -Path $script:VmRoot -ErrorAction Stop | Out-Null
    $acl = Get-Acl -LiteralPath $script:VmRoot
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sidText in (Get-ExpectedAclSids)) {
        $sid = [System.Security.Principal.SecurityIdentifier]::new($sidText)
        $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            ([System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit),
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
        $acl.SetAccessRule($rule)
    }
    Set-Acl -LiteralPath $script:VmRoot -AclObject $acl
    Assert-RestrictedAcl -Path $script:VmRoot -Directory $true
    Write-Host "Created protected VM storage directory: $script:VmRoot"
}

function Assert-VmRoot {
    if (-not (Test-Path -LiteralPath $script:VmRoot -PathType Container)) {
        Stop-WithError "VM storage does not exist. Run Install first to create it with a restricted ACL: $script:VmRoot"
    }
    if ((Get-Item -LiteralPath $script:VmRoot -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Stop-WithError "superHarry-vm must not be a reparse point: $script:VmRoot"
    }
    Assert-RestrictedAcl -Path $script:VmRoot -Directory $true
}

function Assert-VmChildPath {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$ExpectedName
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if ([System.IO.Path]::GetDirectoryName($fullPath).TrimEnd('\') -ine $script:VmRoot.TrimEnd('\') -or
        [System.IO.Path]::GetFileName($fullPath) -cne $ExpectedName) {
        Stop-WithError "Refusing an unexpected VM artifact path: $fullPath"
    }
    return $fullPath
}

function Assert-VmFile {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$ExpectedName
    )

    $fullPath = Assert-VmChildPath -Path $Path -ExpectedName $ExpectedName
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        Stop-WithError "Required VM artifact not found: $fullPath"
    }
    if ((Get-Item -LiteralPath $fullPath -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Stop-WithError "VM artifact must not be a reparse point: $fullPath"
    }
    Assert-RestrictedAcl -Path $fullPath -Directory $false
    return $fullPath
}

function Assert-FreeSpace {
    $driveRoot = [System.IO.Path]::GetPathRoot($script:VmRoot)
    $driveName = $driveRoot.TrimEnd('\').TrimEnd(':')
    $drive = Get-PSDrive -Name $driveName -ErrorAction Stop
    if ($drive.Free -lt $script:MinimumFreeBytes) {
        Stop-WithError "At least 64 GiB free space is required on $driveRoot for the 32 GiB base plus session overlay; available: $([math]::Floor($drive.Free / 1GB)) GiB."
    }
}

function Get-Qcow2Info {
    param([Parameter(Mandatory)][string]$Path)
    $output = Invoke-Probe -Executable $script:QemuImgPath -Arguments @('info', '--output=json', $Path) -Label "qemu-img info for $Path"
    try {
        return ($output | ConvertFrom-Json -ErrorAction Stop)
    } catch {
        Stop-WithError "Could not parse qemu-img JSON metadata for $Path. $($_.Exception.Message)"
    }
}

function Assert-CleanBaseDisk {
    param([Parameter(Mandatory)][string]$Path)
    $info = Get-Qcow2Info -Path $Path
    if ($info.format -ne 'qcow2' -or [long]$info.'virtual-size' -ne $script:DiskBytes) {
        Stop-WithError "Base disk must be QCOW2 with the selected virtual size of $($script:DiskBytes / 1GB) GiB."
    }
    $backingFilename = $info.PSObject.Properties['backing-filename']
    if ($null -ne $backingFilename -and -not [string]::IsNullOrWhiteSpace([string]$backingFilename.Value)) {
        Stop-WithError "Base disk unexpectedly has a backing file: $($backingFilename.Value)"
    }
}

function Assert-PristineEmptyBaseDisk {
    param([Parameter(Mandatory)][string]$Path)

    Invoke-Probe -Executable $script:QemuImgPath -Arguments @('check', '-f', 'qcow2', $Path) -Label "qemu-img check for $Path" | Out-Null
    $output = Invoke-Probe -Executable $script:QemuImgPath -Arguments @('map', '--output=json', $Path) -Label "qemu-img map for $Path"
    try {
        $parsedExtents = ConvertFrom-Json -InputObject $output -ErrorAction Stop
        $extents = @($parsedExtents | ForEach-Object { $_ })
    } catch {
        Stop-WithError "Could not parse qemu-img map for $Path. $($_.Exception.Message)"
    }

    $nextOffset = [long]0
    foreach ($extent in $extents) {
        if ([long]$extent.start -ne $nextOffset -or
            [long]$extent.length -le 0 -or
            $extent.present -or
            $extent.data -or
            -not $extent.zero) {
            Stop-WithError "Existing base disk is not a pristine empty image; refusing to resume installation: $Path"
        }
        $nextOffset += [long]$extent.length
    }
    if ($nextOffset -ne $script:DiskBytes) {
        Stop-WithError "Existing base disk map does not cover exactly 32 GiB; refusing to resume installation: $Path"
    }
}

function Assert-SessionOverlay {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$BackingPath
    )

    $info = Get-Qcow2Info -Path $Path
    $reportedBacking = [string]$info.'backing-filename'
    if ($info.format -ne 'qcow2' -or
        [long]$info.'virtual-size' -ne $script:DiskBytes -or
        $info.'backing-filename-format' -ne 'qcow2' -or
        [string]::IsNullOrWhiteSpace($reportedBacking)) {
        Stop-WithError 'Session overlay must be QCOW2, 32 GiB, and backed by the selected QCOW2 base.'
    }

    if ([System.IO.Path]::IsPathRooted($reportedBacking)) {
        $resolvedBacking = [System.IO.Path]::GetFullPath($reportedBacking)
    } else {
        $resolvedBacking = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $Path) $reportedBacking))
    }
    if ($resolvedBacking -ine [System.IO.Path]::GetFullPath($BackingPath)) {
        Stop-WithError "Session overlay refers to an unexpected backing file: $reportedBacking"
    }
}

function Remove-NormalExitArtifacts {
    param([Parameter(Mandatory)][string[]]$Artifacts)

    foreach ($artifact in $Artifacts) {
        $path = Assert-VmChildPath -Path $artifact -ExpectedName ([System.IO.Path]::GetFileName($artifact))
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            continue
        }
        if ((Get-Item -LiteralPath $path -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            Stop-WithError "Refusing to delete a reparse point during session cleanup: $path"
        }
        Remove-Item -LiteralPath $path -Force -ErrorAction Stop
    }
}

function New-SessionId {
    return '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N'))
}

function Assert-LoopbackPortAvailable {
    param([Parameter(Mandatory)][ValidateRange(1, 65535)][int]$Port)

    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
    } catch {
        Stop-WithError "SSH forwarding requires 127.0.0.1:$Port to be available. Stop the process using that port and retry. $($_.Exception.Message)"
    } finally {
        $listener.Stop()
    }
}

Assert-QemuCandidate
Get-ExpectedFirmwarePins

if ($Mode -eq 'Validate') {
    if (Test-Path -LiteralPath $script:VmRoot -PathType Container) {
        Assert-VmRoot
        Write-Host 'superHarry-vm exists and its ACL passed validation.'
    } else {
        Write-Host 'superHarry-vm has not been created; Validate mode does not create repository state.'
    }
    Write-Host 'Validation only: no disk/image was created and no VM was started.'
    return
}

if ($Mode -eq 'Install') {
    if ([string]::IsNullOrWhiteSpace($InstallerIso) -or [string]::IsNullOrWhiteSpace($InstallerSha256)) {
        Stop-WithError 'Install requires -InstallerIso and its independently verified -InstallerSha256.'
    }
    $script:InstallerIso = Resolve-FilePath -Path $InstallerIso -Label 'Debian installer ISO'
    if ([System.IO.Path]::GetFileName($script:InstallerIso) -notmatch '^debian-13\.7(?:\.0)?-arm64-netinst\.iso$') {
        Stop-WithError 'The installer must be named debian-13.7.0-arm64-netinst.iso (or debian-13.7-arm64-netinst.iso).'
    }
    $installerHash = Get-Sha256 -Path $script:InstallerIso
    Assert-Sha256 -Actual $installerHash -Expected $InstallerSha256 -Label 'Debian installer ISO'
    Write-Host "Debian installer ISO SHA-256 verified against the supplied pin: $installerHash"

    Set-NewVmRootAcl
    Assert-FreeSpace
    $baseDisk = Assert-VmChildPath -Path (Join-Path $script:VmRoot $script:BaseDiskName) -ExpectedName $script:BaseDiskName
    $baseDiskExists = Test-Path -LiteralPath $baseDisk
    if ($baseDiskExists -and -not $ResumeInstall) {
        Stop-WithError "Install will not overwrite an existing base disk: $baseDisk. Preserve and inspect it; choose an owner-reviewed recovery action."
    }
    if (-not $baseDiskExists -and $ResumeInstall) {
        Stop-WithError "ResumeInstall requires an existing base disk to validate: $baseDisk"
    }

    $sessionId = New-SessionId
    $installVarsName = "install-vars-$sessionId.fd"
    $installVars = Assert-VmChildPath -Path (Join-Path $script:VmRoot $installVarsName) -ExpectedName $installVarsName
    if ($baseDiskExists) {
        Assert-VmFile -Path $baseDisk -ExpectedName $script:BaseDiskName | Out-Null
        if ((Get-Item -LiteralPath $baseDisk).Attributes -band [System.IO.FileAttributes]::ReadOnly) {
            Stop-WithError "ResumeInstall requires a writable pristine base disk: $baseDisk"
        }
        Assert-CleanBaseDisk -Path $baseDisk
        Assert-PristineEmptyBaseDisk -Path $baseDisk
        Write-Host 'Resuming installation with the existing base disk verified clean and entirely empty.'
    } else {
        & $script:QemuImgPath create -f qcow2 $baseDisk 32G
        if ($LASTEXITCODE -ne 0) {
            Stop-WithError "qemu-img could not create the 32 GiB QCOW2 base disk (exit code $LASTEXITCODE). Any partial artifact is preserved."
        }
    }
    Assert-VmFile -Path $baseDisk -ExpectedName $script:BaseDiskName | Out-Null
    Assert-CleanBaseDisk -Path $baseDisk
    Copy-Item -LiteralPath $script:FirmwareVarsPath -Destination $installVars -ErrorAction Stop
    Assert-VmFile -Path $installVars -ExpectedName $installVarsName | Out-Null

    $arguments = @(
        '-machine', 'virt-11.1,accel=tcg',
        '-cpu', 'cortex-a76',
        '-smp', '4',
        '-m', '8G',
        '-drive', "if=pflash,format=raw,unit=0,readonly=on,file=$script:FirmwareCodePath",
        '-drive', "if=pflash,format=raw,unit=1,file=$installVars",
        '-drive', "if=none,id=rootdisk,file=$baseDisk,format=qcow2",
        '-device', 'virtio-blk-device,drive=rootdisk',
        '-drive', "if=none,id=installer,file=$script:InstallerIso,format=raw,media=cdrom,readonly=on",
        '-device', 'virtio-scsi-device,id=scsi',
        '-device', 'scsi-cd,drive=installer,bus=scsi.0',
        '-device', 'pcie-root-port,id=netrp,bus=pcie.0,addr=0x1,chassis=1,slot=1',
        '-boot', 'order=d',
        '-nic', 'none',
        '-display', 'none',
        '-serial', 'mon:stdio'
    )
    $qemuReturned = $false
    $qemuExitCode = $null
    try {
        Write-Host 'Install mode: starts with no NIC/backend. Wait for the Debian installer Linux kernel/menu, then follow the runbook to add networking; never attach during firmware boot.'
        & $script:QemuPath @arguments
        $qemuExitCode = $LASTEXITCODE
        $qemuReturned = $true
    } finally {
        if ($qemuReturned -and $qemuExitCode -eq 0) {
            Remove-NormalExitArtifacts -Artifacts @($installVars)
        } else {
            Write-Warning "Installer session did not finish with exit code 0. Preserving base disk and firmware state under $script:VmRoot."
        }
    }
    if ($qemuExitCode -ne 0) {
        Stop-WithError "QEMU exited with code $qemuExitCode. The base disk remains writable and all remaining artifacts are preserved."
    }

    $confirmation = Read-Host 'After confirming Debian 13.7 ARM64 installed successfully and was shut down from the guest, type INSTALL-COMPLETE to seal this base disk'
    if ($confirmation -cne 'INSTALL-COMPLETE') {
        Write-Warning "Base disk was not sealed. Preserve it for review; do not use Run until the installation is verified."
        return
    }
    Assert-CleanBaseDisk -Path $baseDisk
    $attributes = [System.IO.File]::GetAttributes($baseDisk)
    [System.IO.File]::SetAttributes($baseDisk, $attributes -bor [System.IO.FileAttributes]::ReadOnly)
    if (-not ((Get-Item -LiteralPath $baseDisk).Attributes -band [System.IO.FileAttributes]::ReadOnly)) {
        Stop-WithError 'Could not mark the verified base disk read-only.'
    }
    Assert-VmFile -Path $baseDisk -ExpectedName $script:BaseDiskName | Out-Null
    Write-Host "Installed base disk is sealed read-only: $baseDisk"
    return
}

Assert-VmRoot
Assert-FreeSpace
$baseDisk = Assert-VmFile -Path (Join-Path $script:VmRoot $RunBaseName) -ExpectedName $RunBaseName
if (-not ((Get-Item -LiteralPath $baseDisk).Attributes -band [System.IO.FileAttributes]::ReadOnly)) {
    Stop-WithError "Base disk is not marked read-only; refusing to run: $baseDisk"
}
$baseInfo = Get-Qcow2Info -Path $baseDisk
if ($baseInfo.format -ne 'qcow2' -or
    [long]$baseInfo.'virtual-size' -lt 3GB -or
    [long]$baseInfo.'virtual-size' -gt 32GB) {
    Stop-WithError 'Run base disk must be QCOW2 with a virtual size from 3 GiB through 32 GiB.'
}
$script:DiskBytes = [long]$baseInfo.'virtual-size'
Assert-CleanBaseDisk -Path $baseDisk

$sessionId = New-SessionId
$overlayName = "session-$sessionId.qcow2"
$varsName = "session-vars-$sessionId.fd"
$overlay = Assert-VmChildPath -Path (Join-Path $script:VmRoot $overlayName) -ExpectedName $overlayName
$sessionVars = Assert-VmChildPath -Path (Join-Path $script:VmRoot $varsName) -ExpectedName $varsName
Assert-LoopbackPortAvailable -Port 2222
Copy-Item -LiteralPath $script:FirmwareVarsPath -Destination $sessionVars -ErrorAction Stop
Assert-VmFile -Path $sessionVars -ExpectedName $varsName | Out-Null
& $script:QemuImgPath create -f qcow2 -F qcow2 -b $baseDisk $overlay
if ($LASTEXITCODE -ne 0) {
    Stop-WithError "qemu-img could not create the disposable overlay (exit code $LASTEXITCODE). Firmware state is preserved at $sessionVars."
}
Assert-VmFile -Path $overlay -ExpectedName $overlayName | Out-Null
Assert-SessionOverlay -Path $overlay -BackingPath $baseDisk

$runArguments = @(
    '-machine', 'virt-11.1,accel=tcg',
    '-cpu', 'cortex-a76',
    '-smp', '4',
    '-m', '8G',
    '-drive', "if=pflash,format=raw,unit=0,readonly=on,file=$script:FirmwareCodePath",
    '-drive', "if=pflash,format=raw,unit=1,file=$sessionVars",
    '-drive', "if=none,id=rootdisk,file=$overlay,format=qcow2",
    '-device', 'virtio-blk-device,drive=rootdisk',
    '-device', 'pcie-root-port,id=netrp,bus=pcie.0,addr=0x1,chassis=1,slot=1',
    '-boot', 'order=c',
    '-nic', 'none',
    '-display', 'none',
    '-serial', 'mon:stdio'
)
$qemuReturned = $false
$qemuExitCode = $null
try {
    Write-Host 'Run mode: starts without a NIC or network backend. Log in to Debian first; only then switch to the QEMU monitor (Ctrl+A, C) and run:'
    Write-Host '  netdev_add user,id=guestnet,hostfwd=tcp:127.0.0.1:2222-:22'
    Write-Host '  device_add virtio-net-pci,bus=netrp,netdev=guestnet,id=guestnic'
    Write-Host 'Use Ctrl+A, C to return to the guest serial console. Do not attach networking before login.'
    Write-Host 'SSH forwarding is bound only to 127.0.0.1:2222; no LAN listener is configured.'
    & $script:QemuPath @runArguments
    $qemuExitCode = $LASTEXITCODE
    $qemuReturned = $true
} finally {
    if ($qemuReturned -and $qemuExitCode -eq 0) {
        Remove-NormalExitArtifacts -Artifacts @($overlay, $sessionVars)
        Write-Host 'Normal QEMU exit: only this session overlay and writable VARS copy were discarded.'
    } else {
        Write-Warning "QEMU did not finish with exit code 0. Preserve these session artifacts until QEMU is stopped and file handles are released: $overlay ; $sessionVars"
    }
}
if ($qemuExitCode -ne 0) {
    Stop-WithError "QEMU exited with code $qemuExitCode. Session artifacts are preserved."
}
