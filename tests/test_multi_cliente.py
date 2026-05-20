import os
import sys
import tempfile
import time
sys.path.insert(0, os.path.dirname(__file__))
from helper import arrancar_sistema, conectar_cliente, pedir, limpiar

# programa que copia stdin a stdout (cross-platform)
CAT = "import sys; sys.stdout.write(sys.stdin.read())"


def main():
    print("=== Test: Multi-cliente Secuencial ===\n")
    print("ctrllt sirve varios clientes uno tras otro; el aralmac persiste.\n")
    procs = arrancar_sistema()

    print("-- Cliente 1: crea y escribe --")
    con1 = conectar_cliente()
    id_f = pedir(con1, {"servicio": "gesfich", "operacion": "Crear"})["id-fichero"]
    print(f"  creo {id_f}")
    fuente = os.path.join(tempfile.gettempdir(), "fuente_multi.txt")
    with open(fuente, "w", encoding="utf-8") as f:
        f.write("mensaje del cliente 1")
    pedir(con1, {"servicio": "gesfich", "operacion": "Actualizar", "id-fichero": id_f, "ruta": fuente})
    id_p = pedir(con1, {"servicio": "gesprog", "operacion": "Guardar",
                        "ejecutable": sys.executable, "args": ["-c", CAT], "env": []})["id-programa"]
    print(f"  registro {id_p}")
    con1.cerrar()
    time.sleep(0.3)

    print("\n-- Cliente 2: verifica lo de Cliente 1 --")
    con2 = conectar_cliente()
    ficheros = pedir(con2, {"servicio": "gesfich", "operacion": "Leer"}).get("ficheros", [])
    assert id_f in ficheros, f"{id_f} no visible"
    print(f"  [OK  ] ve {id_f}")
    r = pedir(con2, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": id_f})
    assert "cliente 1" in r.get("contenido", "")
    print(f"  [OK  ] contenido: '{r.get('contenido')}'")
    programas = pedir(con2, {"servicio": "gesprog", "operacion": "Leer"}).get("programas", [])
    assert id_p in programas
    print(f"  [OK  ] ve {id_p}")
    con2.cerrar()
    time.sleep(0.3)

    print("\n-- Cliente 3: ejecuta y termina --")
    con3 = conectar_cliente()
    id_salida = pedir(con3, {"servicio": "gesfich", "operacion": "Crear"})["id-fichero"]
    id_e = pedir(con3, {"servicio": "ejecutor", "operacion": "Ejecutar",
                        "id-programa": id_p, "stdin": id_f, "stdout": id_salida})["id-ejecucion"]
    print(f"  ejecucion {id_e}")
    time.sleep(0.5)
    r = pedir(con3, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": id_e})
    print(f"  estado: {r.get('proceso-estado')}, codigo-salida: {r.get('codigo-salida')}")
    r = pedir(con3, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": id_salida})
    print(f"  salida: '{r.get('contenido')}'")
    print(f"  terminar: {pedir(con3, {'servicio': 'ctrllt', 'operacion': 'Terminar'})}")
    con3.cerrar()

    for p in procs:
        p.terminate()
    limpiar()
    print("\n=== Multi-cliente: COMPLETADO ===")


if __name__ == "__main__":
    main()
