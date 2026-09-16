$ErrorActionPreference = "Stop"
$src = "d:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.docx"
$dst = "d:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.pdf"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($src, $false, $true)
    foreach ($f in $doc.Fields) { $f.Update() | Out-Null }
    $doc.SaveAs($dst, 17)
    $pages = $doc.ComputeStatistics(2)
    $doc.Close($false)
    Write-Output ("PDF_OK pages=" + $pages)
} finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
