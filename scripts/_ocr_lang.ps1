$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null
$langs = [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages
foreach ($l in $langs) { Write-Output ("LANG: " + $l.LanguageTag) }
if (-not $langs) { Write-Output 'LANG: NONE' }
