param(
    [string]$Root = (Resolve-Path ".").Path
)

$extensions = @(
    "*.py","*.pyw","*.html","*.css","*.js","*.json","*.md","*.txt",
    "*.yml","*.yaml","*.ini","*.cfg","*.toml","*.ps1","*.bat","*.csv"
)

$utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)

$files = Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\\.venv\\" -and $_.FullName -notmatch "\\\.git\\" } |
    Where-Object { $extensions -contains ('*' + $_.Extension) }

$bad = @()
foreach ($file in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    $hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $isUtf8 = $true

    try {
        [void]$utf8Strict.GetString($bytes)
    } catch {
        $isUtf8 = $false
    }

    if ($hasBom -or -not $isUtf8) {
        $bad += [PSCustomObject]@{
            Path = $file.FullName
            Bom = $hasBom
            Utf8 = $isUtf8
        }
    }
}

if ($bad.Count -gt 0) {
    $bad | Format-Table -AutoSize
    exit 1
}

Write-Host "Encoding check passed."
