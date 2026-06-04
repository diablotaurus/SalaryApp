param(
    [string]$Root = (Resolve-Path ".").Path
)

$extensions = @(
    "*.py","*.pyw","*.html","*.css","*.js","*.json","*.md","*.txt",
    "*.yml","*.yaml","*.ini","*.cfg","*.toml","*.bat","*.ps1","*.csv"
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
$cp1251 = [System.Text.Encoding]::GetEncoding(1251)
$mojibakePattern = '[ЂЃ‚ѓ„…†‡€‰‹ЉЊЋЌЍЎЏђѓ€™“”•–—™љњћќўџ]'

$files = Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\\.venv\\' -and $_.FullName -notmatch '\\\.git\\' } |
    Where-Object { $extensions -contains ('*' + $_.Extension) }

foreach ($file in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    $text = $null

    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    } else {
        try {
            $text = $utf8Strict.GetString($bytes)
        } catch {
            try {
                $text = $cp1251.GetString($bytes)
            } catch {
                continue
            }
        }
    }

    if ($null -eq $text) { continue }

    if ($text -match $mojibakePattern) {
        try {
            $fixed = $utf8Strict.GetString($cp1251.GetBytes($text))
            if (-not ($fixed -match $mojibakePattern)) {
                $text = $fixed
            }
        } catch {
            # ignore fix failures
        }
    }

    [System.IO.File]::WriteAllText($file.FullName, $text, $utf8NoBom)
}

Write-Host "Encoding fix completed."
