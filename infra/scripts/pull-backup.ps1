# Roda no seu PC (PowerShell). Puxa o backup mais recente do lab e mantém os últimos 14 aqui.
#   powershell -File infra\scripts\pull-backup.ps1 -HostIp <ip> -Key <caminho da chave ssh>
param(
  [Parameter(Mandatory = $true)][string]$HostIp,
  [Parameter(Mandatory = $true)][string]$Key,
  [string]$Dest = "$env:USERPROFILE\Documents\seismo-backups",
  [int]$Keep = 14
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $Dest | Out-Null
$latest = ssh -i $Key "ubuntu@$HostIp" "ls -1t /var/backups/seismo/seismo-*.dump | head -1"
if (-not $latest) { throw "Nenhum backup encontrado no servidor." }
scp -i $Key "ubuntu@${HostIp}:$latest" $Dest
Get-ChildItem $Dest -Filter "seismo-*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep | Remove-Item
Write-Output "Copiado: $(Split-Path $latest -Leaf) -> $Dest"
