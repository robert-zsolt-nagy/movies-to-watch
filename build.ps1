Write-Output ">generate assets"
$null = New-Item ".\web\dist" -ItemType Directory -ea 0
npm install --prefix web > web\dist\install-log.txt
if (-not $?)
{
    Write-Output  "ERROR: npm install failed:"
    Get-Content web/dist/install-log.txt
    Write-Output  "exiting..."
    exit 1
}

npm run build --prefix web > web/dist/build-log.txt
if (-not $?)
{
    Write-Output  "ERROR: npm build failed:"
    Get-Content web/dist/build-log.txt
    Write-Output  "exiting..."
    exit 1
}

Write-Output  ">copy generated assets"
$null = New-Item ".\static\style" -ItemType Directory -ea 0
$null = New-Item ".\static\script" -ItemType Directory -ea 0
Copy-Item ".\web\dist\main.css" -Destination ".\static\style"
Copy-Item ".\web\dist\main.js" -Destination ".\static\script"
Copy-Item ".\web\dist\main.js.LICENSE.txt" -Destination ".\static\script"

Write-Output  ">build completed $( Get-Date )"