import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from helper import arrancar_sistema, conectar_cliente, enviar, apagar

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
        print(f"  [FALLO] {label} → got: {r}")


def main():
    print("=== Test: Transiciones Inválidas ===\n")
    procs = arrancar_sistema()
    req, res = conectar_cliente()

    print("-- gesfich --")
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Reasumir"})
    check("Reasumir sin estar suspendido", r, "error", "transicion invalida")

    enviar(req, res, {"servicio": "gesfich", "operacion": "Suspender"})
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Suspender"})
    check("Suspender dos veces", r, "error", "transicion invalida")

    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Crear"})
    check("Crear estando suspendido", r, "error", "transicion invalida")

    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Reasumir"})
    check("Reasumir correctamente", r, "ok")

    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Crear"})
    check("Crear tras reasumir", r, "ok")

    print("\n-- errores de recursos --")
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": "f-9999"})
    check("Leer fichero inexistente", r, "error", "fichero no encontrado")

    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Borrar", "id-fichero": "f-9999"})
    check("Borrar fichero inexistente", r, "error", "fichero no encontrado")

    r = enviar(req, res, {"servicio": "gesprog", "operacion": "Leer", "id-programa": "p-9999"})
    check("Leer programa inexistente", r, "error", "programa no encontrado")

    r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": "e-9999"})
    check("Estado de ejecucion inexistente", r, "error", "ejecucion no encontrada")

    r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Matar", "id-ejecucion": "e-9999"})
    check("Matar ejecucion inexistente", r, "error", "ejecucion no encontrada")

    print("\n-- errores de protocolo --")
    r = enviar(req, res, {"servicio": "inventado", "operacion": "Crear"})
    check("Servicio desconocido", r, "error", "servicio desconocido")

    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Inventar"})
    check("Operacion desconocida en gesfich", r, "error", "operacion desconocida")

    r = enviar(req, res, {"servicio": "ctrllt", "operacion": "Inventar"})
    check("Operacion desconocida en ctrllt", r, "error", "operacion ctrllt desconocida")

    print(f"\n  Resultado: {PASS} OK, {FAIL} FALLO")
    apagar(req, res, procs)
    print("=== Transiciones: COMPLETADO ===")


if __name__ == "__main__":
    main()
