$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.RandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $resultType) {
    $m = $asTaskGeneric.MakeGenericMethod($resultType)
    $task = $m.Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    return $task.Result
}

$out = 'D:\数模工作流\scripts\_ocr_req_result.txt'
[System.IO.File]::WriteAllText($out, 'START' + [Environment]::NewLine, [System.Text.Encoding]::UTF8)
function Log($s) {
    [System.IO.File]::AppendAllText($out, $s + [Environment]::NewLine, [System.Text.Encoding]::UTF8)
}

$path = 'E:\微信聊天记录\xwechat_files\wxid_so1zh5t7c8rl22_8e76\msg\file\2026-08\数学建模A题\7121c6162839d24937c4016274d67a6a.jpg'
if (Test-Path $path) { Log 'PATH_OK' } else { Log 'PATH_MISSING'; exit 1 }

$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
Log ('FILE: ' + $file.Name)
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
Log 'STREAM_OK'
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
Log ('DECODER: ' + $decoder.PixelWidth + 'x' + $decoder.PixelHeight)
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
Log 'BITMAP_OK'
$lang = New-Object Windows.Globalization.Language 'zh-Hans-CN'
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if ($null -eq $engine) { Log 'ENGINE_NULL'; exit 1 }
Log 'ENGINE_OK'
$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
foreach ($line in $result.Lines) { Log $line.Text }
Log 'DONE'
