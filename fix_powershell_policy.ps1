# PowerShell 执行策略修复脚本
# 用于解决 npm 命令执行时的安全策略问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PowerShell 执行策略修复" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`n当前执行策略: " -NoNewline -ForegroundColor Yellow
$currentPolicy = Get-ExecutionPolicy
Write-Host $currentPolicy -ForegroundColor White

if ($currentPolicy -eq "Restricted") {
    Write-Host "`n检测到执行策略为 Restricted，需要修改。" -ForegroundColor Yellow
    Write-Host "`n选项 1: 为当前用户设置 RemoteSigned（推荐）" -ForegroundColor Green
    Write-Host "选项 2: 为当前进程临时设置 Bypass" -ForegroundColor Green
    Write-Host "选项 3: 取消（使用 cmd.exe 执行任务，无需修改策略）" -ForegroundColor Green
    
    $choice = Read-Host "`n请选择 (1/2/3)"
    
    switch ($choice) {
        "1" {
            Write-Host "`n正在设置执行策略为 RemoteSigned..." -ForegroundColor Yellow
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
            Write-Host "✓ 执行策略已设置为 RemoteSigned" -ForegroundColor Green
        }
        "2" {
            Write-Host "`n正在为当前进程设置 Bypass..." -ForegroundColor Yellow
            Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
            Write-Host "✓ 当前进程的执行策略已设置为 Bypass" -ForegroundColor Green
            Write-Host "注意: 此设置仅在当前 PowerShell 会话中有效" -ForegroundColor Yellow
        }
        "3" {
            Write-Host "`n已取消。VSCode 任务已配置为使用 cmd.exe，无需修改执行策略。" -ForegroundColor Yellow
            exit 0
        }
        default {
            Write-Host "`n无效选择，已取消。" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "`n执行策略已允许脚本运行，无需修改。" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "修复完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n提示: VSCode 任务已配置为使用 cmd.exe，" -ForegroundColor Yellow
Write-Host "即使不修改执行策略，任务也能正常运行。" -ForegroundColor Yellow
Write-Host "`n按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

