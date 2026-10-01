<#
.SYNOPSIS
    Thin bootstrap launcher for router_preflight.py (development-delegation).

.DESCRIPTION
    Discovers and validates an existing Python 3.11+ interpreter that provides
    tomllib, then runs the preflight helper that sits next to this script with
    that interpreter. This launcher performs no preflight logic of its own, and
    it never installs packages, downloads an interpreter, creates a virtual
    environment or writes repository state.
    Probe and helper child environments remove PYLAUNCHER_ALLOW_INSTALL and
    PYLAUNCHER_ALWAYS_INSTALL: legacy py treats any non-empty value, including
    0, as enabling installation. Both children also set
    PYTHON_MANAGER_AUTOMATIC_INSTALL to false to disable Python Install Manager
    automatic installation. The launcher's own environment is unchanged.

    Discovery order, first qualifying candidate wins:
      1. -PythonPath                (explicit)
      2. $env:GLOBAL_SKILL_PYTHON   (explicit)
      3. py -3
      4. python
      5. python3

    Every candidate must start, report Python >= 3.11 and expose tomllib. An
    explicit candidate that is unusable ends the launcher with its own
    classification instead of silently selecting another interpreter. Ordinary
    candidates that are missing, too old or unusable fall through to the next.

    Bootstrap failure categories:
      interpreter_not_found   candidate cannot be resolved
      interpreter_too_old     candidate runs Python < 3.11
      dependency_unavailable  candidate starts but cannot provide tomllib; a
                              denial that only surfaces inside the interpreter
                              is reported this way
      execution_denied        the process could not be started because of an
                              access/execution policy denial; stops the launcher
      probe_timeout           the probe exceeded -ProbeTimeoutSeconds
      helper_failed           router_preflight.py is missing or unreadable, or
                              the helper process cannot be started

    On success the helper's exit code (0/1/130) is forwarded unchanged and its
    output is passed through. On failure the launcher writes one
    preflight_report/1 JSON document with bootstrap "blocked" to stdout, one
    short line to stderr, and exits 3. Reports never contain absolute paths,
    user names, environment values or raw interpreter stderr.

    The helper is resolved relative to this script's own directory, never the
    process CWD. Arguments are passed as arrays with quoted paths; there is no
    Invoke-Expression and no interpolation into a shell string.

.PARAMETER PythonPath
    Explicit interpreter to use. Overrides all other discovery.

.PARAMETER ProbeTimeoutSeconds
    Bound, in seconds, for each interpreter probe. Default 10.

.PARAMETER HelperArguments
    Arguments forwarded verbatim to router_preflight.py.

.EXAMPLE
    pwsh -NoProfile -File scripts/bootstrap.ps1 -HelperArguments @('--help')

.EXAMPLE
    powershell -NoProfile -File scripts/bootstrap.ps1 -PythonPath C:\Python312\python.exe

.EXAMPLE
    # The PowerShell host consumes flags that begin with two dashes in -File
    # mode, so forward helper flags through the -Command form:
    pwsh -NoProfile -Command "& '.\scripts\bootstrap.ps1' -HelperArguments @('--check-local-router')"
#>
[CmdletBinding()]
param(
    [string] $PythonPath = '',
    [ValidateRange(1, 2147483647)]
    [int] $ProbeTimeoutSeconds = 10,
    [string[]] $HelperArguments = @()
)

$ErrorActionPreference = 'Stop'

$HelperPath = Join-Path -Path $PSScriptRoot -ChildPath 'router_preflight.py'

# Fixed probe: imports tomllib and prints a status plus the interpreter record.
# It contains no character that PowerShell or a POSIX shell would interpolate.
$ProbeText = "import sys;ok=sys.version_info[:2]>=(3,11) and bool(__import__('tomllib'));print('BOOTSTRAP_OK' if ok else 'BOOTSTRAP_TOO_OLD',sys.version_info[0],sys.version_info[1],sys.platform,sys.executable)"

function Get-FailureCategory {
    param([System.Exception] $Exception)
    $current = $Exception
    while ($null -ne $current) {
        if ($current.GetType().Name -like '*UnauthorizedAccess*') { return 'execution_denied' }
        if ($current -is [System.ComponentModel.Win32Exception]) {
            $code = $current.NativeErrorCode
            if ($code -eq 5 -or $code -eq 740 -or $code -eq 1260) { return 'execution_denied' }
            if ($code -eq 2 -or $code -eq 3) { return 'interpreter_not_found' }
            return 'dependency_unavailable'
        }
        $current = $current.InnerException
    }
    $message = [string]$Exception.Message
    if ($message -like '*Access is denied*') { return 'execution_denied' }
    return 'dependency_unavailable'
}

function ConvertTo-ArgumentString {
    <# Windows command-line quoting for ProcessStartInfo.Arguments (Windows
       PowerShell 5.1 has no ArgumentList API). Values are trusted launcher
       inputs; nothing here is evaluated by a shell. #>
    param([string[]] $ArgumentList)
    $parts = New-Object System.Collections.ArrayList
    foreach ($argument in $ArgumentList) {
        if ([string]::IsNullOrEmpty($argument)) {
            [void]$parts.Add('""')
            continue
        }
        if ($argument -notmatch '[\s"]') {
            [void]$parts.Add($argument)
            continue
        }
        $builder = New-Object System.Text.StringBuilder
        [void]$builder.Append('"')
        $backslashes = 0
        foreach ($character in $argument.ToCharArray()) {
            if ($character -eq [char]92) { $backslashes++; continue }
            if ($character -eq [char]34) {
                [void]$builder.Append(([string][char]92) * (2 * $backslashes + 1))
                [void]$builder.Append('"')
            }
            else {
                if ($backslashes -gt 0) { [void]$builder.Append(([string][char]92) * $backslashes) }
                [void]$builder.Append($character)
            }
            $backslashes = 0
        }
        if ($backslashes -gt 0) { [void]$builder.Append(([string][char]92) * (2 * $backslashes)) }
        [void]$builder.Append('"')
        [void]$parts.Add($builder.ToString())
    }
    return (@($parts) -join ' ')
}

function Invoke-InterpreterProbe {
    param([string] $FilePath, [string[]] $Arguments, [int] $TimeoutSeconds)
    $result = [ordered]@{
        Started         = $false
        StartException  = $null
        TimedOut        = $false
        ExitCode        = $null
        StandardOutput  = ''
    }
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = ConvertTo-ArgumentString -ArgumentList $Arguments
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    $startInfo.EnvironmentVariables.Remove('PYLAUNCHER_ALLOW_INSTALL')
    $startInfo.EnvironmentVariables.Remove('PYLAUNCHER_ALWAYS_INSTALL')
    $startInfo.EnvironmentVariables['PYTHON_MANAGER_AUTOMATIC_INSTALL'] = 'false'

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        [void]$process.Start()
    }
    catch {
        $result.StartException = $_.Exception
        return $result
    }
    $result.Started = $true
    $outputTask = $process.StandardOutput.ReadToEndAsync()
    $errorTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $result.TimedOut = $true
        try { $process.Kill() } catch { }
        try { [void]$process.WaitForExit(5000) } catch { }
    }
    # Descendants may retain redirected handles after the candidate is killed.
    # Never wait indefinitely for either stream, even after a normal exit.
    try {
        if ($outputTask.Wait(1000)) { $result.StandardOutput = $outputTask.Result }
        else { $result.TimedOut = $true }
    } catch { $result.StandardOutput = '' }
    try {
        if (-not $errorTask.Wait(1000)) { $result.TimedOut = $true }
    } catch { }
    try { $result.ExitCode = $process.ExitCode } catch { $result.ExitCode = $null }
    try { $process.Dispose() } catch { }
    return $result
}

function Write-BootstrapFailure {
    param([string] $Category, [string[]] $Attempts)
    $attemptList = @($Attempts)
    $report = [ordered]@{
        schema_version    = 'preflight_report/1'
        bootstrap         = 'blocked'
        bootstrap_failure = $Category
        provenance        = [ordered]@{
            generated_at  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            roles         = @()
            operation     = 'preflight_bootstrap'
            requirements  = @()
            inputs        = @('bootstrap.ps1')
            interpreter   = $null
            host          = [ordered]@{ platform = 'windows'; shell = 'powershell' }
            scope         = 'bootstrap'
            limits        = 'no interpreter candidate satisfied >=3.11 with tomllib'
        }
        roles             = @()
        error             = [ordered]@{
            code          = 'bootstrap_blocked'
            message       = "no candidate qualified; attempted $($attemptList.Count): $($attemptList -join ', ')"
        }
    }
    $report | ConvertTo-Json -Depth 8
    [Console]::Error.WriteLine("bootstrap failed: $Category (attempted $($attemptList.Count) interpreter candidate(s))")
}

$attempts = New-Object System.Collections.ArrayList
$candidates = New-Object System.Collections.ArrayList

if (-not [string]::IsNullOrWhiteSpace($PythonPath)) {
    [void]$candidates.Add([ordered]@{ Name = 'explicit'; Explicit = $true; Command = $PythonPath; Leading = @() })
}
$environmentPython = [System.Environment]::GetEnvironmentVariable('GLOBAL_SKILL_PYTHON')
if (-not [string]::IsNullOrWhiteSpace($environmentPython)) {
    [void]$candidates.Add([ordered]@{ Name = 'GLOBAL_SKILL_PYTHON'; Explicit = $true; Command = $environmentPython; Leading = @() })
}
foreach ($specification in @(
        [ordered]@{ Name = 'py -3'; Explicit = $false; Command = 'py'; Leading = @('-3') },
        [ordered]@{ Name = 'python'; Explicit = $false; Command = 'python'; Leading = @() },
        [ordered]@{ Name = 'python3'; Explicit = $false; Command = 'python3'; Leading = @() })) {
    [void]$candidates.Add($specification)
}

$selected = $null

foreach ($candidate in $candidates) {
    $executable = $null
    $category = $null

    if ($candidate.Explicit) {
        try {
            if (Test-Path -LiteralPath $candidate.Command -PathType Leaf -ErrorAction Stop) {
                $executable = (Get-Item -LiteralPath $candidate.Command -ErrorAction Stop).FullName
            }
            else {
                $category = 'interpreter_not_found'
            }
        }
        catch {
            $category = Get-FailureCategory -Exception $_.Exception
            if ($category -ne 'execution_denied') { $category = 'interpreter_not_found' }
        }
    }
    else {
        $command = $null
        try {
            $command = @(Get-Command -Name $candidate.Command -CommandType Application -ErrorAction Stop) | Select-Object -First 1
        }
        catch {
            $command = $null
        }
        if ($null -eq $command) {
            $category = 'interpreter_not_found'
        }
        else {
            $executable = $command.Path
        }
    }

    if ($null -ne $category) {
        [void]$attempts.Add($candidate.Name + '=' + $category)
        if ($candidate.Explicit -or $category -eq 'execution_denied') {
            Write-BootstrapFailure -Category $category -Attempts $attempts
            exit 3
        }
        continue
    }

    $probeArguments = @($candidate.Leading) + @('-c', $ProbeText)
    $probe = Invoke-InterpreterProbe -FilePath $executable -Arguments $probeArguments -TimeoutSeconds $ProbeTimeoutSeconds

    if ($null -ne $probe.StartException) {
        $category = Get-FailureCategory -Exception $probe.StartException
    }
    elseif ($probe.TimedOut) {
        $category = 'probe_timeout'
    }
    else {
        $output = [string]$probe.StandardOutput
        if ($probe.ExitCode -ne 0) {
            $category = 'dependency_unavailable'
        }
        elseif ($output -match '(?m)^BOOTSTRAP_OK ([0-9]+) ([0-9]+) (\S+) (.+)\r?$') {
            $selected = [ordered]@{
                Name = $candidate.Name; Executable = $executable; Leading = @($candidate.Leading)
                Resolved = [ordered]@{
                    Major = [int]$Matches[1]; Minor = [int]$Matches[2]
                    Platform = $Matches[3]; Executable = $Matches[4].TrimEnd([char]13)
                }
            }
            break
        }
        elseif ($output -match '(?m)^BOOTSTRAP_TOO_OLD(?: |\r?$)') {
            $category = 'interpreter_too_old'
        }
        else {
            # A missing/unrecognized token cannot establish a usable runtime.
            $category = 'dependency_unavailable'
        }
    }

    [void]$attempts.Add($candidate.Name + '=' + $category)
    if ($candidate.Explicit -or $category -eq 'execution_denied') {
        Write-BootstrapFailure -Category $category -Attempts $attempts
        exit 3
    }
}

if ($null -eq $selected) {
    $lastCategory = 'interpreter_not_found'
    if ($attempts.Count -gt 0) { $lastCategory = ($attempts[$attempts.Count - 1] -split '=', 2)[1] }
    Write-BootstrapFailure -Category $lastCategory -Attempts $attempts
    exit 3
}

$helperReadable = $true
try {
    if (-not (Test-Path -LiteralPath $HelperPath -PathType Leaf -ErrorAction Stop)) { $helperReadable = $false }
}
catch {
    $helperReadable = $false
}
if (-not $helperReadable) {
    [void]$attempts.Add('helper=helper_failed')
    Write-BootstrapFailure -Category 'helper_failed' -Attempts $attempts
    exit 3
}

$helperCall = @()
$helperCall += @($selected.Leading)
$helperCall += $HelperPath
$helperCall += @($HelperArguments)

$helperExitCode = 0
$helperStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$helperStartInfo.FileName = $selected.Executable
$helperStartInfo.Arguments = ConvertTo-ArgumentString -ArgumentList $helperCall
$helperStartInfo.UseShellExecute = $false
$helperStartInfo.EnvironmentVariables.Remove('PYLAUNCHER_ALLOW_INSTALL')
$helperStartInfo.EnvironmentVariables.Remove('PYLAUNCHER_ALWAYS_INSTALL')
$helperStartInfo.EnvironmentVariables['PYTHON_MANAGER_AUTOMATIC_INSTALL'] = 'false'
$helperProcess = New-Object System.Diagnostics.Process
$helperProcess.StartInfo = $helperStartInfo
try {
    [void]$helperProcess.Start()
    $helperProcess.WaitForExit()
    $helperExitCode = $helperProcess.ExitCode
}
catch {
    $category = Get-FailureCategory -Exception $_.Exception
    if ($category -ne 'execution_denied') { $category = 'helper_failed' }
    [void]$attempts.Add('helper=' + $category)
    Write-BootstrapFailure -Category $category -Attempts $attempts
    exit 3
}
finally {
    $helperProcess.Dispose()
}
if ($null -eq $helperExitCode) { $helperExitCode = 0 }
exit $helperExitCode
