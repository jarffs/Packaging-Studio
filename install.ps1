param(
    [string]$Package = "packaging_studio",
    [switch]$DevMode
)

$ErrorActionPreference = "Stop"

# Resolver o caminho completo do pacote
$sourcePath = Join-Path $PSScriptRoot $Package

if (-not (Test-Path $sourcePath)) {
    Write-Error "Pacote/Pasta de origem '$sourcePath' não encontrado."
}

# Determinar o nome do addon (se for zip, remove a extensão. Se tiver versão no nome, podemos simplificar ou usar o nome real)
$isZip = $sourcePath.EndsWith(".zip")

if ($isZip) {
    # Para zips como "packaging_studio-0.6.1.zip", extrair apenas "packaging_studio" como nome base (se necessário, adapte o regex)
    $addonName = (Get-Item $sourcePath).BaseName -replace "-[\d\.]+$",""
} else {
    $addonName = (Get-Item $sourcePath).Name
}

# Procurar versões do Blender (4.2 ou superior) no AppData
$blenderAppdata = Join-Path $env:APPDATA "Blender Foundation\Blender"
if (-not (Test-Path $blenderAppdata)) {
    Write-Error "Pasta do Blender não encontrada em '$blenderAppdata'."
}

$installedVersions = Get-ChildItem -Path $blenderAppdata -Directory | Where-Object { 
    $_.Name -match "^\d+\.\d+$" -and [version]$_.Name -ge [version]"4.2"
}

if ($installedVersions.Count -eq 0) {
    Write-Error "Nenhuma versão do Blender 4.2 ou superior foi encontrada."
}

foreach ($versionDir in $installedVersions) {
    $targetBase = Join-Path $versionDir.FullName "extensions\user_default"
    
    if (-not (Test-Path $targetBase)) {
        New-Item -Path $targetBase -ItemType Directory -Force | Out-Null
    }
    
    $targetDir = Join-Path $targetBase $addonName
    
    Write-Host "Instalando '$addonName' no Blender $($versionDir.Name)..." -ForegroundColor Cyan
    
    if (Test-Path $targetDir) {
        if ($DevMode -and -not $isZip) {
            $isJunction = (Get-Item $targetDir).Attributes -match "ReparsePoint"
            if ($isJunction) {
                Write-Host "Link simbólico/Junction já existe para a versão $($versionDir.Name)." -ForegroundColor Yellow
                continue
            }
        }
        Remove-Item -Path $targetDir -Recurse -Force
    }
    
    if ($isZip) {
        Write-Host "Extraindo '$sourcePath' para '$targetDir'..." -ForegroundColor Cyan
        # Usa o Expand-Archive para extrair o conteúdo
        Expand-Archive -Path $sourcePath -DestinationPath $targetDir -Force
        Write-Host "Instalação do pacote ZIP concluída em: $targetDir" -ForegroundColor Green
    }
    elseif ($DevMode) {
        # Criar Junction para modo de desenvolvimento
        New-Item -ItemType Junction -Path $targetDir -Target $sourcePath | Out-Null
        Write-Host "Junction criada em: $targetDir" -ForegroundColor Green
    } else {
        # Copiar arquivos
        Copy-Item -Path $sourcePath -Destination $targetDir -Recurse -Force
        Write-Host "Cópia concluída em: $targetDir" -ForegroundColor Green
    }
}

Write-Host "Instalação finalizada!" -ForegroundColor Green
