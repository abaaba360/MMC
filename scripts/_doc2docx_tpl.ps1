$ErrorActionPreference = "Stop"
$src = 'E:\微信聊天记录\xwechat_files\wxid_so1zh5t7c8rl22_8e76\msg\file\2026-08\2026数学建模国赛标准论文Word模板(3).doc'
$dst = 'D:\数模工作流\templates\CUMCM2026_标准论文模板_转docx.docx'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
    $d = $w.Documents.Open($src, $false, $true)
    $d.SaveAs2($dst, 16)
    $d.Close($false)
    Write-Output "OK"
} finally {
    $w.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($w) | Out-Null
}
