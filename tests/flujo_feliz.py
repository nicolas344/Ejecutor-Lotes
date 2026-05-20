import os
import sys
import tempfile
import time
sys.path.insert(0, os.path.dirname(__file__))
from helper import arrancar_sistema, conectar_cliente, pedir, apagar

# programa que ordena las lineas de stdin (cross-platform)
SORT = "import sys; sys.stdout.write(''.join(sorted(sys.stdin.readlines())))"


def check(label, r, esperado="ok"):
    marca = "OK  " if r.get("estado") == esperado else "FALLO"
    print(f"  [{marca}] {label}: {r}")


def main():
    print("=== Test: Flujo Feliz Completo ===\n")
    procs = arrancar_sistema()
    con = conectar_cliente()

    # 1. fichero de entrada
    r = pedir(con, {"servicio": "gesfich", "operacion": "Crear"})
    check("Crear fichero entrada", r)
    id_entrada = r["id-fichero"]

    # 2. volcar contenido desordenado desde un archivo del disco
    fuente = os.path.join(tempfile.gettempdir(), "fuente_flujo.txt")
    with open(fuente, "w", encoding="utf-8") as f:
        f.write("banana\nmanzana\ncereza\narandano\n")
    r = pedir(con, {"servicio": "gesfich", "operacion": "Actualizar",
                    "id-fichero": id_entrada, "ruta": fuente})
    check("Actualizar entrada desde archivo", r)

    # 3. fichero de salida
    r = pedir(con, {"servicio": "gesfich", "operacion": "Crear"})
    check("Crear fichero salida", r)
    id_salida = r["id-fichero"]

    # 4. registrar el programa de ordenamiento
    r = pedir(con, {"servicio": "gesprog", "operacion": "Guardar",
                    "ejecutable": sys.executable, "args": ["-c", SORT], "env": []})
    check("Guardar programa sort", r)
    id_prog = r["id-programa"]

    # 5. listar (Leer/Estado sin id)
    r = pedir(con, {"servicio": "gesfich", "operacion": "Leer"})
    check("Listar ficheros", r)
    print(f"         Ficheros: {r.get('ficheros')}")
    r = pedir(con, {"servicio": "gesprog", "operacion": "Leer"})
    check("Listar programas", r)
    print(f"         Programas: {r.get('programas')}")

    # 6. ejecutar
    r = pedir(con, {"servicio": "ejecutor", "operacion": "Ejecutar",
                    "id-programa": id_prog, "stdin": id_entrada, "stdout": id_salida})
    check("Ejecutar proceso", r)
    id_e = r["id-ejecucion"]

    # 7-8. estado
    r = pedir(con, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": id_e})
    print(f"         Estado inmediato: {r.get('proceso-estado')}")
    time.sleep(1)
    r = pedir(con, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": id_e})
    check("Estado tras 1s", r)
    print(f"         Estado: {r.get('proceso-estado')}, codigo-salida: {r.get('codigo-salida')}")

    # 9. leer salida ordenada
    r = pedir(con, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": id_salida})
    salida = r.get("contenido", "").strip()
    print(f"\n  Salida:   {salida!r}")
    esperado = "arandano\nbanana\ncereza\nmanzana"
    print("  [OK  ] Salida ordenada" if salida == esperado else f"  [FALLO] esperado {esperado!r}")

    print("\n  Terminando sistema...")
    apagar(con, procs)
    print("\n=== Flujo Feliz: COMPLETADO ===")


if __name__ == "__main__":
    main()
