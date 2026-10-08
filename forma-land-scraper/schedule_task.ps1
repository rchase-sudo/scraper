<#
Registers a Windows Task Scheduler job to run the scraper on a recurring
schedule (default: weekly, Monday 6am). Run this script once, manually,
from an elevated or normal PowerShell prompt:

    .\schedule_task.ps1

To change frequency, edit -Trigger below (examples in comments).
To remove the scheduled task later:

    Unregister-ScheduledTask -TaskName "FormaLandScraper" -Confirm:$false
#>

$taskName = "FormaLandScraper"
$scriptDir = $PSScriptRoot
$pythonExe = (Get-Command python).Source

$action = New-ScheduledTaskAction -Execute $pythonExe `
    -Argument "main.py" `
    -WorkingDirectory $scriptDir

# Weekly, Monday at 6:00 AM. For daily instead, use:
#   New-ScheduledTaskTrigger -Daily -At 6am
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 6am

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 3)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Weekly Forma Designs land-listing scrape" `
    -Force

Write-Host "Scheduled task '$taskName' registered: weekly, Monday 6am."
Write-Host "Output CSVs will land in: $scriptDir\output"
Write-Host "Logs will land in: $scriptDir\logs"
