# Arranque del sistema en Windows (named pipes full-duplex)
# En Windows cada conexion usa una sola tuberia, asi que el segundo
# nombre (respuestas) no se usa; se pasa "_" para cumplir los argumentos.
$root = $PSScriptRoot
$aralmac = Join-Path $root "aralmac"
$py = "python"

Write-Host "Arrancando servicios..."
Start-Process $py -WorkingDirectory $root -ArgumentList "src/gesfich/gesfich.py -f ejlotes_gesfich -b _ -x `"$aralmac`""
Start-Process $py -WorkingDirectory $root -ArgumentList "src/gesprog/gesprog.py -p ejlotes_gesprog -c _ -x `"$aralmac`""
Start-Process $py -WorkingDirectory $root -ArgumentList "src/ejecutor/ejecutor.py -e ejlotes_ejecutor -d _ -x `"$aralmac`""

Start-Sleep -Milliseconds 500
Start-Process $py -WorkingDirectory $root -ArgumentList "src/ctrllt/ctrllt.py -c ejlotes_cliente -a _ -f ejlotes_gesfich -b _ -p ejlotes_gesprog -r _ -e ejlotes_ejecutor -d _"

Start-Sleep -Milliseconds 500
Write-Host "Arrancando cliente..."
& $py src/cliente/cliente.py -c ejlotes_cliente -a _
