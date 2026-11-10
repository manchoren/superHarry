# Prepare and start the persistent VM (superHarry-vm)
# Based on docs/platform/vm/t174-durable-vm-profile.md

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$qemuDir = 'C:\Program Files\qemu'
$baseDisk = 'C:\superHarry-vm\debian-13.7-arm64-base.qcow2'
$sessionVars = 'C:\superHarry-vm\install-vars-20261104-123930-d17dc04ad0ae4991b1f087adfd0a0dab.fd'

# 1. Ensure base disk is read-only (required by Run mode)
$i = Get-Item -LiteralPath $baseDisk
$isReadOnly = ($i.Attributes -band 4) -ne 0
Write-Host "Base disk readonly: $isReadOnly"
if (-not $isReadOnly) {
    Write-Host "Marking base disk read-only..."
    [System.IO.File]::SetAttributes($baseDisk, $i.Attributes -bor 4)
    $i = Get-Item -LiteralPath $baseDisk
    Write-Host "Base disk marked read-only: $(($i.Attributes -band 4) -ne 0)"
}

# 2. Verify base disk is valid
& "$qemuDir\qemu-img.exe" info --output=json $baseDisk | Out-File -FilePath 'C:\superHarry\qemu-base-info.json' -Encoding UTF8
Write-Host "qemu-img info written"

# 3. Start QEMU persistent VM
$args = @(
    '-machine', 'virt-11.1,accel=tcg',
    '-cpu', 'cortex-a76',
    '-smp', '4',
    '-m', '8G',
    '-drive', "if=pflash,format=raw,unit=0,readonly=on,file=C:\Program Files\qemu\share\edk2-aarch64-code.fd",
    '-drive', "if=pflash,format=raw,unit=1,file=$sessionVars",
    '-drive', "if=none,id=rootdisk,file=$baseDisk,format=qcow2",
    '-device', 'virtio-blk-device,drive=rootdisk',
    '-device', 'pcie-root-port,id=netrp,bus=pcie.0,addr=0x1,chassis=1,slot=1',
    '-netdev', 'user,id=guestnet,hostfwd=tcp:127.0.0.1:2222-:22',
    '-device', 'virtio-net-pci,bus=netrp,netdev=guestnet,id=guestnic',
    '-boot', 'order=c',
    '-display', 'none',
    '-serial', 'mon:stdio'
)

Write-Host "Starting QEMU with $(@($args).Count) args"
& "$qemuDir\qemu-system-aarch64.exe" @args
