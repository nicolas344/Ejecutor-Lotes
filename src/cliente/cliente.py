import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.protocolo import leer_mensaje, escribir_mensaje


def enviar(req, res, msg):
    escribir_mensaje(req, msg)
    return leer_mensaje(res)


def menu_ficheros(req, res):
    opciones = {
        "1": "Crear",
        "2": "Leer",
        "3": "Actualizar",
        "4": "Borrar",
        "5": "Listar",
        "6": "Suspender",
        "7": "Reasumir",
        "8": "Terminar servicio",
    }
    while True:
        print("\n-- Ficheros --")
        for k, v in opciones.items():
            print(f"  {k}. {v}")
        print("  0. Volver")
        opcion = input("> ").strip()

        if opcion == "0":
            break
        elif opcion == "1":
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Crear"})
        elif opcion == "2":
            id_f = input("id-fichero: ").strip()
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Leer", "id-fichero": id_f})
        elif opcion == "3":
            id_f = input("id-fichero: ").strip()
            contenido = input("contenido: ")
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Actualizar", "id-fichero": id_f, "contenido": contenido})
        elif opcion == "4":
            id_f = input("id-fichero: ").strip()
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Borrar", "id-fichero": id_f})
        elif opcion == "5":
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Listar"})
        elif opcion == "6":
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Suspender"})
        elif opcion == "7":
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Reasumir"})
        elif opcion == "8":
            r = enviar(req, res, {"servicio": "gesfich", "operacion": "Terminar"})
        else:
            print("Opcion invalida")
            continue
        print(f"Respuesta: {r}")


def menu_programas(req, res):
    while True:
        print("\n-- Programas --")
        print("  1. Guardar  2. Leer  3. Actualizar  4. Borrar  5. Listar")
        print("  6. Suspender  7. Reasumir  8. Terminar servicio  0. Volver")
        opcion = input("> ").strip()

        if opcion == "0":
            break
        elif opcion == "1":
            ejecutable = input("ejecutable (ruta): ").strip()
            args_str = input("argumentos (separados por espacio, o vacio): ").strip()
            argumentos = args_str.split() if args_str else []
            r = enviar(req, res, {
                "servicio": "gesprog", "operacion": "Guardar",
                "ejecutable": ejecutable, "argumentos": argumentos, "ambiente": {}
            })
        elif opcion == "2":
            id_p = input("id-programa: ").strip()
            r = enviar(req, res, {"servicio": "gesprog", "operacion": "Leer", "id-programa": id_p})
        elif opcion == "3":
            id_p = input("id-programa: ").strip()
            ejecutable = input("nuevo ejecutable: ").strip()
            args_str = input("nuevos argumentos: ").strip()
            argumentos = args_str.split() if args_str else []
            r = enviar(req, res, {
                "servicio": "gesprog", "operacion": "Actualizar",
                "id-programa": id_p, "ejecutable": ejecutable, "argumentos": argumentos, "ambiente": {}
            })
        elif opcion == "4":
            id_p = input("id-programa: ").strip()
            r = enviar(req, res, {"servicio": "gesprog", "operacion": "Borrar", "id-programa": id_p})
        elif opcion == "5":
            r = enviar(req, res, {"servicio": "gesprog", "operacion": "Listar"})
        elif opcion == "6":
            r = enviar(req, res, {"servicio": "gesprog", "operacion": "Suspender"})
        elif opcion == "7":
            r = enviar(req, res, {"servicio": "gesprog", "operacion": "Reasumir"})
        elif opcion == "8":
            r = enviar(req, res, {"servicio": "gesprog", "operacion": "Terminar"})
        else:
            print("Opcion invalida")
            continue
        print(f"Respuesta: {r}")


def menu_ejecuciones(req, res):
    while True:
        print("\n-- Ejecuciones --")
        print("  1. Ejecutar  2. Estado  3. Listar  4. Matar")
        print("  5. Suspender servicio  6. Reasumir servicio  0. Volver")
        opcion = input("> ").strip()

        if opcion == "0":
            break
        elif opcion == "1":
            id_p = input("id-programa: ").strip()
            msg = {"servicio": "ejecutor", "operacion": "Ejecutar", "id-programa": id_p}
            stdin_f = input("stdin (id-fichero o vacio): ").strip()
            stdout_f = input("stdout (id-fichero o vacio): ").strip()
            stderr_f = input("stderr (id-fichero o vacio): ").strip()
            if stdin_f:
                msg["stdin"] = stdin_f
            if stdout_f:
                msg["stdout"] = stdout_f
            if stderr_f:
                msg["stderr"] = stderr_f
            r = enviar(req, res, msg)
        elif opcion == "2":
            id_e = input("id-ejecucion: ").strip()
            r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": id_e})
        elif opcion == "3":
            r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Listar"})
        elif opcion == "4":
            id_e = input("id-ejecucion: ").strip()
            r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Matar", "id-ejecucion": id_e})
        elif opcion == "5":
            r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Suspender"})
        elif opcion == "6":
            r = enviar(req, res, {"servicio": "ejecutor", "operacion": "Reasumir"})
        else:
            print("Opcion invalida")
            continue
        print(f"Respuesta: {r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", required=True, help="Tuberia de peticiones a ctrllt")
    parser.add_argument("-a", required=True, help="Tuberia de respuestas de ctrllt")
    args = parser.parse_args()

    print(f"[cliente] Conectando a {args.c}...")
    with open(args.c, "w") as req, open(args.a, "r") as res:
        print("[cliente] Conectado.\n")
        while True:
            print("=== Ejecutor de Lotes ===")
            print("  1. Ficheros (gesfich)")
            print("  2. Programas (gesprog)")
            print("  3. Ejecuciones (ejecutor)")
            print("  4. Terminar sistema")
            print("  0. Salir sin terminar")
            opcion = input("> ").strip()

            if opcion == "0":
                break
            elif opcion == "1":
                menu_ficheros(req, res)
            elif opcion == "2":
                menu_programas(req, res)
            elif opcion == "3":
                menu_ejecuciones(req, res)
            elif opcion == "4":
                r = enviar(req, res, {"servicio": "ctrllt", "operacion": "Terminar"})
                print(f"Respuesta: {r}")
                break
            else:
                print("Opcion invalida")

    print("[cliente] Desconectado.")


if __name__ == "__main__":
    main()
