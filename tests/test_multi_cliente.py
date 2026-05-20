import sys
import os
import time
sys.path.insert(0, os.path.dirname(__file__))
from helper import arrancar_sistema, conectar_cliente, enviar, PIPES


def main():
    print("=== Test: Multi-cliente Secuencial ===\n")
    print("Demuestra que ctrllt sirve múltiples clientes uno tras otro.")
    print("El estado del aralmac persiste entre conexiones.\n")

    procs = arrancar_sistema()

    # --- Cliente 1 ---
    print("── Cliente 1: crea y escribe un fichero ──")
    req1, res1 = conectar_cliente()

    r = enviar(req1, res1, {"servicio": "gesfich", "operacion": "Crear"})
    id_f = r["id-fichero"]
    print(f"  Creó fichero: {id_f}")

    enviar(req1, res1, {"servicio": "gesfich", "operacion": "Actualizar",
                         "id-fichero": id_f, "contenido": "mensaje del cliente 1"})
    print(f"  Escribió contenido en {id_f}")

    r = enviar(req1, res1, {"servicio": "gesprog", "operacion": "Guardar",
                             "ejecutable": "/usr/bin/cat", "argumentos": [], "ambiente": {}})
    id_p = r["id-programa"]
    print(f"  Registró programa: {id_p} (/usr/bin/cat)")

    req1.close()
    res1.close()
    print("  Cliente 1 desconectado.\n")
    time.sleep(0.3)

    # --- Cliente 2 ---
    print("── Cliente 2: verifica lo que dejó Cliente 1 ──")
    req2, res2 = conectar_cliente()

    r = enviar(req2, res2, {"servicio": "gesfich", "operacion": "Listar"})
    ficheros = r.get("ficheros", [])
    print(f"  Ficheros visibles: {ficheros}")
    assert id_f in ficheros, f"ERROR: {id_f} no visible para Cliente 2"
    print(f"  [OK  ] Cliente 2 ve {id_f} creado por Cliente 1")

    r = enviar(req2, res2, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": id_f})
    print(f"  Contenido de {id_f}: '{r.get('contenido')}'")
    assert "cliente 1" in r.get("contenido", "")
    print(f"  [OK  ] Contenido correcto")

    r = enviar(req2, res2, {"servicio": "gesprog", "operacion": "Listar"})
    print(f"  Programas visibles: {r.get('programas')}")
    assert id_p in r.get("programas", [])
    print(f"  [OK  ] Programa {id_p} visible para Cliente 2")

    req2.close()
    res2.close()
    print("  Cliente 2 desconectado.\n")
    time.sleep(0.3)

    # --- Cliente 3: ejecuta el programa y termina ---
    print("── Cliente 3: ejecuta programa y termina el sistema ──")
    req3, res3 = conectar_cliente()

    r = enviar(req3, res3, {"servicio": "gesfich", "operacion": "Crear"})
    id_salida = r["id-fichero"]

    r = enviar(req3, res3, {"servicio": "ejecutor", "operacion": "Ejecutar",
                             "id-programa": id_p, "stdin": id_f, "stdout": id_salida})
    id_e = r["id-ejecucion"]
    print(f"  Ejecutó {id_p}: ejecucion {id_e}")

    time.sleep(0.5)
    r = enviar(req3, res3, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": id_e})
    print(f"  Estado: {r.get('estado-proceso')}, codigo-salida: {r.get('codigo-salida')}")

    r = enviar(req3, res3, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": id_salida})
    print(f"  Salida de cat: '{r.get('contenido')}'")

    print("\n  Terminando sistema...")
    r = enviar(req3, res3, {"servicio": "ctrllt", "operacion": "Terminar"})
    print(f"  Respuesta: {r}")
    req3.close()
    res3.close()

    for p in procs:
        p.terminate()
    for pipe in PIPES.values():
        if os.path.exists(pipe):
            os.unlink(pipe)

    print("\n=== Multi-cliente: COMPLETADO ===")
    print("  3 clientes distintos usaron el mismo sistema.")
    print("  El estado persistió entre conexiones (ficheros/programas en aralmac).")


if __name__ == "__main__":
    main()
