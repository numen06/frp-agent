mkdir -Force "$env:FRP_DIR" 2>$null
Write-Host "Downloading {{filename}} ..."
Invoke-WebRequest -Uri "{{download_url}}" -OutFile "$env:TEMP\{{filename}}"
tar -xf "$env:TEMP\{{filename}}" -C "$env:TEMP"
Copy-Item "$env:TEMP\frp_*\frpc.exe" "$FRP_DIR\frpc.exe" -Force
Remove-Item "$env:TEMP\{{filename}}" -Force -ErrorAction SilentlyContinue
{{config_line}}{{done_echo}}
