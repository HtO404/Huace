param($src, $dst, $maxW = 800)

Add-Type -AssemblyName System.Drawing

if (-not (Test-Path (Split-Path $dst -Parent))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
}

$img = [System.Drawing.Image]::FromFile((Resolve-Path $src))
$ratio = if ($img.Width -gt $maxW) { $maxW / $img.Width } else { 1.0 }
$nw = [int]($img.Width * $ratio)
$nh = [int]($img.Height * $ratio)

$bmp = New-Object System.Drawing.Bitmap($nw, $nh)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = 'HighQualityBicubic'
$g.DrawImage($img, 0, 0, $nw, $nh)
$g.Dispose()
$bmp.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$img.Dispose()

$old = [int]((Get-Item (Resolve-Path $src)).Length / 1KB)
$new = [int]((Get-Item $dst).Length / 1KB)
Write-Output "$dst | ${old}KB -> ${new}KB"
