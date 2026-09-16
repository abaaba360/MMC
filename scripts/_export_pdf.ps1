
$ErrorActionPreference = 'Stop'
$docx = 'D:\数模工作流\delivery\A题_智能评估\终稿\A题_数学建模论文_终稿.docx'
$pdf  = 'D:\数模工作流\delivery\A题_智能评估\终稿\A题_数学建模论文_终稿.pdf'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx, $false, $true)
    $pages = $doc.ComputeStatistics(2)
    Write-Output ('PAGES=' + $pages)
    $doc.SaveAs([ref]$pdf, [ref]17)
    $doc.Close($false)
    Write-Output ('PDF_EXISTS=' + (Test-Path $pdf))
    Write-Output ('PDF_SIZE=' + (Get-Item $pdf).Length)
} finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
