# ChatGPT 批量导入脚本
# 导入所有导出的 ChatGPT 对话到 PMH

$exportDir = "F:\LI_YONGSHUN\AI\ChatGPT_export\extracted"
$pmhDir = "F:\LI_YONGSHUN\AI\personal-memory-hub"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ChatGPT 批量导入到 PMH" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 查找所有 JSON 文件
$jsonFiles = Get-ChildItem -Path $exportDir -Recurse -Filter "*.json" | Where-Object { $_.Name -match '_c[0-9a-f]{12}\.json$' }

Write-Host "找到 $($jsonFiles.Count) 个对话文件" -ForegroundColor Yellow
Write-Host ""

$successCount = 0
$errorCount = 0

foreach ($file in $jsonFiles) {
    Write-Host "导入: $($file.Name)" -ForegroundColor Green
    try {
        Set-Location $pmhDir
        $result = python scripts/import_chatgpt_v8.py $file.FullName
        if ($LASTEXITCODE -eq 0) {
            $successCount++
            Write-Host "  ✓ 成功" -ForegroundColor Green
        } else {
            $errorCount++
            Write-Host "  ✗ 失败 (exit code: $LASTEXITCODE)" -ForegroundColor Red
        }
    } catch {
        $errorCount++
        Write-Host "  ✗ 异常: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "导入完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "成功: $successCount" -ForegroundColor Green
Write-Host "失败: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { 'Red' } else { 'Green' })
Write-Host ""
Write-Host "提示: 可以在 Dashboard 查看导入结果" -ForegroundColor Yellow
