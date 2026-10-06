param([ValidateSet('setup','models','demo-data','dataset-build','dataset-validate','test','evaluate','report','demo-video','release','release-check','serve','e2e')][string]$Task = 'serve')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Invoke-Checked { param([string]$Executable, [string[]]$Arguments) & $Executable @Arguments; if ($LASTEXITCODE -ne 0) { throw "Command failed: $Executable $Arguments" } }
if ($Task -eq 'setup') {
    Invoke-Checked python @('-m','pip','install','uv==0.12.23')
    Invoke-Checked python @('-m','uv','sync','--frozen','--extra','dev')
    Invoke-Checked npm @('--prefix','frontend','ci')
    Invoke-Checked npm @('--prefix','frontend','run','build')
    exit
}
$PythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $PythonExe)) { throw 'Run .\speechlens.ps1 setup first.' }
switch ($Task) {
    models { Invoke-Checked $PythonExe @('-m','scripts.download_models') }
    demo-data { Invoke-Checked $PythonExe @('-m','scripts.collect_sources'); Invoke-Checked $PythonExe @('-m','scripts.build_dataset','--demo') }
    dataset-build { Invoke-Checked $PythonExe @('-m','scripts.collect_sources'); Invoke-Checked $PythonExe @('-m','scripts.build_dataset') }
    dataset-validate { Invoke-Checked $PythonExe @('-m','scripts.validate_dataset') }
    test { Invoke-Checked $PythonExe @('-m','pytest','tests/unit','tests/integration','-q'); Invoke-Checked npm @('--prefix','frontend','test') }
    evaluate { Invoke-Checked $PythonExe @('-m','scripts.run_evaluation'); Invoke-Checked $PythonExe @('-m','scripts.stress_tests') }
    report { Invoke-Checked $PythonExe @('-m','scripts.finalize_evidence'); Invoke-Checked $PythonExe @('-m','scripts.make_report') }
    demo-video { Invoke-Checked $PythonExe @('-m','scripts.make_video') }
    release { Invoke-Checked $PythonExe @('-m','scripts.make_release') }
    release-check { Invoke-Checked $PythonExe @('-m','scripts.release_check') }
    e2e { Invoke-Checked $PythonExe @('-m','scripts.browser_e2e') }
    serve { Invoke-Checked $PythonExe @('-m','uvicorn','backend.app.api:app','--host','127.0.0.1','--port','8000') }
}
