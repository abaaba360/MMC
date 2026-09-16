$ErrorActionPreference = 'Stop'
$docx = 'D:\数模工作流\delivery\C题论文_光伏微网储能购电滚动优化_图表论证增强版.docx'
$outDir = 'D:\数模工作流\state\docx_render_qa\visual_enhanced_v1_word'
$pdf = Join-Path $outDir 'C题论文_光伏微网储能购电滚动优化_图表论证增强版.pdf'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx, $false, $true)
    $pages = $doc.ComputeStatistics(2)
    Write-Output ('PAGES=' + $pages)
    $doc.ExportAsFixedFormat($pdf, 17)
    $doc.Close($false)
    Write-Output ('PDF=' + $pdf)
    Write-Output ('PDF_SIZE=' + (Get-Item -LiteralPath $pdf).Length)
} finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
