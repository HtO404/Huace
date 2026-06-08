Add-Type -AssemblyName System.Drawing

function Resize-Image {
    param($src, $dst, $maxW = 800, $quality = 70)
    
    $img = [System.Drawing.Image]::FromFile($src)
    $ratio = [Math]::Min($maxW / $img.Width, 1.0)
    $w = [int]($img.Width * $ratio)
    $h = [int]($img.Height * $ratio)
    
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($img, 0, 0, $w, $h)
    $g.Dispose()
    
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
    $params = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, $quality)
    $bmp.Save($dst, $codec, $params)
    
    $bmp.Dispose()
    $img.Dispose()
    Write-Output "OK: $dst ($($w)x$($h)) | $([int]((Get-Item $dst).Length/1KB))KB"
}

$srcDir = "d:\Hcode\识别默认sim卡\output\image"
$thumbDir = "$srcDir\thumb"
New-Item -ItemType Directory -Force -Path $thumbDir | Out-Null

$files = @(
    "no_signal_17_20260515_142033.png",
    "no_signal_28_20260515_143540.png",
    "no_signal_92_20260515_155907.png",
    "no_signal_98_20260515_160741.png",
    "cycle52_卡1_20260515_150703.png",
    "cycle99_卡1_20260515_160938.png"
)

foreach ($f in $files) {
    $src = Join-Path $srcDir $f
    $dst = Join-Path $thumbDir ($f -replace '\.png$', '.jpg')
    Resize-Image -src $src -dst $dst
}
