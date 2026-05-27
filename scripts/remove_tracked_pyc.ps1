$ErrorActionPreference = 'Stop'
Write-Host "Checking out branch developgio..."
git checkout developgio

Write-Host "Listing tracked .pyc files..."
$files = @(git ls-files | Where-Object { $_ -match '\.pyc$' })
if ($files.Length -eq 0) {
    Write-Host 'No tracked .pyc files found'
    exit 0
}

Write-Host 'Files to untrack:'
foreach ($f in $files) { Write-Host " - $f" }

foreach ($f in $files) {
    git rm --cached -- "$f"
}

Write-Host 'Staging .gitignore (if needed) and committing...'
git add .gitignore

try {
    git -c user.email='jacksonlcruz@users.noreply.github.com' -c user.name='Jackson Cruz' commit -m 'Remove tracked .pyc files and update .gitignore'
} catch {
    Write-Host 'Nothing to commit or commit failed.'
}

Write-Host 'Pushing to origin/developgio...'
git push origin developgio
Write-Host 'Done.'
