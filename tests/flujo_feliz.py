import sys
import os
import time
sys.path.insert(0, os.path.dirname(__file__))
from helper import arrancar_sistema, conectar_cliente, enviar, apagar


def check(label, r, estado_esperado="ok"):
    bien = r.get("estado") == estado_esperado
    marca = "OK  " if bien else "FALLO"
    print(f"  [{marca}] {label}: {r}")
    return bien


def main():
    print("=== Test: Flujo Feliz Completo ===\n")
    procs = arrancar_sistema()
    req, res = conectar_cliente()

    # 1. Crear fichero de entrada
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Crear"})
    check("Crear fichero entrada", r)
    id_entrada = r["id-fichero"]

    # 2. Escribir contenido desordenado en el fichero de entrada
    contenido = "banana\nmanzana\ncereza\narándano\n"
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Actualizar",
                           "id-fichero": id_entrada, "contenido": contenido})
    check("Escribir contenido en entrada", r)

    # 3. Crear fichero de salida vacío
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Crear"})
    check("Crear fichero salida", r)
    id_salida = r["id-fichero"]

    # 4. Registrar programa /usr/bin/sort
    r = enviar(req, res, {"servicio": "gesprog", "operacion": "Guardar",
                           "ejecutable": "/usr/bin/sort", "argumentos": [], "ambiente": {}})
    check("Guardar programa sort", r)
    id_prog = r["id-programa"]

    # 5. Listar para verificar que están registrados
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Listar"})
    check("Listar ficheros", r)
    print(f"         Ficheros: {r.get('ficheros')}")

    r = enviar(req, res, {"servicio": "gesprog", "operacion": "Listar"})
    check("Listar programas", r)
    print(f"         Programas: {r.get('programas')}")

    # 6. Ejecutar: sort lee de entrada y escribe en salida
    r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Ejecutar",
                           "id-programa": id_prog, "stdin": id_entrada, "stdout": id_salida})
    check("Ejecutar proceso", r)
    id_e = r["id-ejecucion"]
    print(f"         ID ejecucion: {id_e}")

    # 7. Consultar estado inmediato (puede ser Ejecutando o Terminado)
    r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": id_e})
    check("Estado inmediato", r)
    print(f"         Estado: {r.get('estado-proceso')}")

    # 8. Esperar y volver a consultar
    time.sleep(1)
    r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": id_e})
    check("Estado tras 1s (esperado: Terminado)", r)
    print(f"         Estado: {r.get('estado-proceso')}, codigo-salida: {r.get('codigo-salida')}")

    # 9. Leer fichero de salida y verificar que está ordenado
    r = enviar(req, res, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": id_salida})
    check("Leer fichero salida", r)
    salida = r.get("contenido", "")
    print(f"\n  Entrada:  {contenido.strip()}")
    print(f"  Salida:   {salida.strip()}")
    esperado = "arándano\nbanana\ncereza\nmanzana"
    if salida.strip() == esperado:
        print("  [OK  ] Salida correctamente ordenada")
    else:
        print(f"  [FALLO] Salida inesperada. Esperado: {esperado}")

    # 10. Terminar sistema
    print("\n  Terminando sistema...")
    apagar(req, res, procs)
    print("\n=== Flujo Feliz: COMPLETADO ===")


if __name__ == "__main__":
    main()
