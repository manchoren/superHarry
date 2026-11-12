# Compatibility wrapper. The VM lifecycle is implemented only in dev-vm.ps1.
# Use Run mode so validation always runs on a disposable QCOW2 overlay.

[CmdletBinding()]
param(
    [string]$FirmwareCodePath = 'C:\Program Files\qemu\share\edk2-aarch64-code.fd',
    [string]$FirmwareVarsPath = 'C:\Program Files\qemu\share\edk2-arm-vars.fd',
    [string]$FirmwareCodeSha256,
    [string]$FirmwareVarsSha256,
    [ValidateSet('debian-13.7-arm64-base.qcow2', 'debian-13-nocloud-configured-base.qcow2', 'debian-13-nocloud-arm64-base.qcow2')]
    [string]$RunBaseName = 'debian-13.7-arm64-base.qcow2'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$devVm = Join-Path $PSScriptRoot 'dev-vm.ps1'
& $devVm -Mode Run -FirmwareCodePath $FirmwareCodePath -FirmwareVarsPath $FirmwareVarsPath -FirmwareCodeSha256 $FirmwareCodeSha256 -FirmwareVarsSha256 $FirmwareVarsSha256 -RunBaseName $RunBaseName
exit $LASTEXITCODE
