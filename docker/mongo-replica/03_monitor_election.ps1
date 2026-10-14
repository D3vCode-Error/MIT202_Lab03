
$ErrorActionPreference = "Stop"

$resultsDir = ".\results"
New-Item -ItemType Directory -Force -Path $resultsDir |
    Out-Null

$log = Join-Path $resultsDir "e2_mongo_election_log.txt"

"MongoDB Controlled Election Test" |
    Tee-Object -FilePath $log

"Start: $(Get-Date -Format o)" |
    Tee-Object -FilePath $log -Append

$timer = [System.Diagnostics.Stopwatch]::StartNew()

# Stop only the current replica-set primary.
docker stop mit03_mongo_rs1 |
    Tee-Object -FilePath $log -Append

$newPrimary = $null

for ($attempt = 1; $attempt -le 90; $attempt++) {

    foreach ($node in @(
        "mit03_mongo_rs2",
        "mit03_mongo_rs3"
    )) {
        $result = (
            docker exec $node mongosh --quiet --eval `
                "db.hello().isWritablePrimary" 2>$null
        )

        $elapsed = [math]::Round(
            $timer.Elapsed.TotalSeconds, 2
        )

        if ($result -match "^true$") {
            $newPrimary = $node

            "ELECTED: $node at ${elapsed}s" |
                Tee-Object -FilePath $log -Append

            break
        }
    }

    if ($newPrimary) {
        break
    }

    $elapsed = [math]::Round(
        $timer.Elapsed.TotalSeconds, 2
    )

    "Checking election... ${elapsed}s" |
        Tee-Object -FilePath $log -Append

    Start-Sleep -Seconds 1
}

$timer.Stop()

if ($newPrimary) {
    "Election detected successfully." |
        Tee-Object -FilePath $log -Append
} else {
    "No new primary detected during monitoring." |
        Tee-Object -FilePath $log -Append
}

"End: $(Get-Date -Format o)" |
    Tee-Object -FilePath $log -Append
