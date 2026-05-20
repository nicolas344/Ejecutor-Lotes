import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from helper import arrancar_sistema, conectar_cliente, pedir, apagar

PASS = 0
FAIL = 0


def check(label, r, estado_esp, mensaje_esp=None):
    global PASS, FAIL
    ok = r.get("estado") == estado_esp
    if mensaje_esp:
        ok = ok and mensaje_esp in r.get("mensaje", "")
    if ok:
        PASS += 1
        print(f"  [OK  ] {label}")
    else:
        FAIL += 1
        print(f"  [FALLO] {label} -> {r}")


def main():
    print("=== Test: Transiciones Invalidas ===\n")
    procs = arrancar_sistema()
    con = conectar_cliente()

    print("-- gesfich --")
    check("Reasumir sin suspender", pedir(con, {"servicio": "gesfich", "operacion": "Reasumir"}),
          "error", "transicion invalida")
    pedir(con, {"servicio": "gesfich", "operacion": "Suspender"})
    check("Suspender dos veces", pedir(con, {"servicio": "gesfich", "operacion": "Suspender"}),
          "error", "transicion invalida")
    check("Crear suspendido", pedir(con, {"servicio": "gesfich", "operacion": "Crear"}),
          "error", "servicio suspendido")
    check("Reasumir", pedir(con, {"servicio": "gesfich", "operacion": "Reasumir"}), "ok")
    check("Crear tras reasumir", pedir(con, {"servicio": "gesfich", "operacion": "Crear"}), "ok")

    print("\n-- errores de recursos --")
    check("Leer fichero inexistente",
          pedir(con, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": "f-9999"}),
          "error", "fichero no encontrado")
    check("Borrar fichero inexistente",
          pedir(con, {"servicio": "gesfich", "operacion": "Borrar", "id-fichero": "f-9999"}),
          "error", "fichero no encontrado")
    check("Leer programa inexistente",
          pedir(con, {"servicio": "gesprog", "operacion": "Leer", "id-programa": "p-9999"}),
          "error", "programa no encontrado")
    check("Estado ejecucion inexistente",
          pedir(con, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": "e-9999"}),
          "error", "proceso no encontrado")
    check("Matar ejecucion inexistente",
          pedir(con, {"servicio": "ejecutor", "operacion": "Matar", "id-ejecucion": "e-9999"}),
          "error", "proceso no encontrado")

    print("\n-- errores de protocolo --")
    check("Servicio desconocido",
          pedir(con, {"servicio": "inventado", "operacion": "Crear"}),
          "error", "servicio desconocido")
    check("Operacion desconocida en gesfich",
          pedir(con, {"servicio": "gesfich", "operacion": "Inventar"}),
          "error", "operacion desconocida")
    check("Operacion desconocida en ctrllt",
          pedir(con, {"servicio": "ctrllt", "operacion": "Inventar"}),
          "error", "operacion ctrllt desconocida")

    print(f"\n  Resultado: {PASS} OK, {FAIL} FALLO")
    apagar(con, procs)
    print("=== Transiciones: COMPLETADO ===")


if __name__ == "__main__":
    main()
