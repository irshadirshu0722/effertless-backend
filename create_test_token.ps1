$apiKey = $env:GCP_IDENTITY_WEB_API_KEY
$email = $env:GCP_TEST_USER_EMAIL

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Error "Set GCP_IDENTITY_WEB_API_KEY in this PowerShell session or your environment."
    exit 1
}

if ([string]::IsNullOrWhiteSpace($email)) {
    $email = Read-Host "Test user email"
}

$password = Read-Host "Test user password" -AsSecureString
$plainPassword = [System.Net.NetworkCredential]::new("", $password).Password

$body = @{
    email = $email
    password = $plainPassword
    returnSecureToken = $true
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=$apiKey" `
        -ContentType "application/json" `
        -Body $body
}
catch {
    Write-Error "Token request failed."

    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message
    }
    elseif ($_.Exception.Response) {
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        Write-Host $reader.ReadToEnd()
    }
    else {
        Write-Host $_.Exception.Message
    }

    exit 1
}

$idToken = $response.idToken

Write-Host "User ID: $($response.localId)"
Write-Host "Expires in: $($response.expiresIn) seconds"
Write-Host "ID token: $idToken"
