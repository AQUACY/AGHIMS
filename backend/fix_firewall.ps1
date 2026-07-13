# PowerShell script to configure Windows Firewall for Analyzer Server
# Run as Administrator: powershell -ExecutionPolicy Bypass -File fix_firewall.ps1

Write-Host "=" * 70
Write-Host "Configuring Windows Firewall for Analyzer Server"
Write-Host "=" * 70
Write-Host ""

# Check if rule exists
$rule = Get-NetFirewallRule -Name "HMS Analyzer Server Port 5150" -ErrorAction SilentlyContinue

if ($rule) {
    Write-Host "Rule already exists. Removing old rule..."
    Remove-NetFirewallRule -Name "HMS Analyzer Server Port 5150"
}

Write-Host "Creating firewall rule..."
New-NetFirewallRule -DisplayName "HMS Analyzer Server Port 5150" `
    -Name "HMS Analyzer Server Port 5150" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5150 `
    -Action Allow `
    -Description "Allow incoming connections to HMS Analyzer Server on port 5150" `
    -Enabled True

Write-Host ""
Write-Host "✓ Firewall rule created successfully!"
Write-Host ""
Write-Host "Rule details:"
Get-NetFirewallRule -Name "HMS Analyzer Server Port 5150" | Format-List
Write-Host ""
Write-Host "=" * 70

