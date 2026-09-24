param([string]$Destination = (Join-Path $env:USERPROFILE 'reachy-lab2-custom'))
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path $PSScriptRoot -Parent
$simulatorRoot = Join-Path $env:USERPROFILE 'reachy-lab2'
$simulatorPython = Join-Path $simulatorRoot '.venv312\Scripts\python.exe'
$destinationPath = [IO.Path]::GetFullPath($Destination)
if ($destinationPath.TrimEnd('\') -eq $simulatorRoot.TrimEnd('\')) { throw 'Destination must not be the simulator folder' }
if (!(Test-Path -LiteralPath $simulatorPython)) { throw "Python 3.12 simulator interpreter not found: $simulatorPython" }
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
if ($destinationPath -ne $sourceRoot) {
    foreach ($name in @('reachy_lab2','assets','config','scripts','tests','third_party','evidence','README.md','STUDY_PLAN.md','SOURCE_INTEGRATION.md','VALIDATION.md','THIRD_PARTY_NOTICES.md','requirements-lock.txt','pyproject.toml','.gitignore')) {
        Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $destinationPath -Recurse -Force
    }
    $studyDestination = Join-Path $destinationPath 'study'
    New-Item -ItemType Directory -Force -Path $studyDestination | Out-Null
    foreach ($item in (Get-ChildItem -LiteralPath (Join-Path $sourceRoot 'study') -File)) {
        Copy-Item -LiteralPath $item.FullName -Destination $studyDestination -Force
    }
    $rawDestination = Join-Path $studyDestination 'data\raw'
    New-Item -ItemType Directory -Force -Path $rawDestination | Out-Null
    foreach ($template in (Get-ChildItem -LiteralPath (Join-Path $sourceRoot 'study\data\raw') -File)) {
        $target = Join-Path $rawDestination $template.Name
        if (!(Test-Path -LiteralPath $target)) { Copy-Item -LiteralPath $template.FullName -Destination $target }
    }
}
$customEnv = Join-Path $destinationPath '.venv312'
$customPython = Join-Path $customEnv 'Scripts\python.exe'
if (!(Test-Path -LiteralPath $customPython)) {
    uv venv --python $simulatorPython $customEnv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
}
uv pip sync --python $customPython (Join-Path $destinationPath 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
Write-Output "Ready: $destinationPath"
Write-Output "cd '$destinationPath'"
Write-Output '.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 trial --condition B --question q1'
