$ErrorActionPreference = 'Stop'
Write-Host "Fetching origin..."
git fetch origin

$commitsRaw = git rev-list --reverse origin/main..developgio
if (-not $commitsRaw) {
    Write-Host 'No commits to rewrite (origin/main..developgio is empty).'
    exit 0
}

$commits = $commitsRaw -split "`n"
Write-Host "Commits to rewrite:"
$commits | ForEach-Object { Write-Host $_ }

Write-Host "Creating branch developgio-fixed from origin/main..."
git checkout -b developgio-fixed origin/main

foreach ($sha in $commits) {
    if (-not $sha) { continue }
    Write-Host "Cherry-pick $sha"
    try {
        git cherry-pick $sha --no-commit
    } catch {
        Write-Error "Cherry-pick failed for $sha"
        try {
            git cherry-pick --abort
        } catch {
            Write-Host 'Abort failed or no cherry-pick to abort'
        }
        exit 1
    }
    Write-Host "Committing with noreply author for $sha"
    git -c user.email="jacksonlcruz@users.noreply.github.com" -c user.name="Jackson Cruz" commit --author='Jackson Cruz <jacksonlcruz@users.noreply.github.com>' -C $sha
}

Write-Host "Pushing developgio-fixed -> developgio on origin..."
git push -u origin developgio-fixed:developgio

Write-Host "Replacing local branch 'developgio' with rewritten branch..."
if (git show-ref --verify --quiet refs/heads/developgio) {
    git branch -D developgio
}
git branch -m developgio-fixed developgio

Write-Host 'Rewrite and push complete.'
