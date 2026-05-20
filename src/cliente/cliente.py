import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import canal


def menu_ficheros(con):
    while True:
        print("\n-- Ficheros --")
        print("  1.Crear  2.Leer  3.Listar  4.Actualizar  5.Borrar")
        print("  6.Suspender  7.Reasumir  8.Terminar servicio  0.Volver")
        op = input("> ").strip()

        if op == "0":
            return
        elif op == "1":
            r = con.enviar({"servicio": "gesfich", "operacion": "Crear"})
        elif op == "2":
            idf = input("id-fichero: ").strip()
            r = con.enviar({"servicio": "gesfich", "operacion": "Leer", "id-fichero": idf})
        elif op == "3":
            r = con.enviar({"servicio": "gesfich", "operacion": "Leer"})
        elif op == "4":
            idf = input("id-fichero: ").strip()
            ruta = input("ruta del archivo origen: ").strip()
            r = con.enviar({"servicio": "gesfich", "operacion": "Actualizar",
                            "id-fichero": idf, "ruta": ruta})
        elif op == "5":
            idf = input("id-fichero: ").strip()
            r = con.enviar({"servicio": "gesfich", "operacion": "Borrar", "id-fichero": idf})
        elif op == "6":
            r = con.enviar({"servicio": "gesfich", "operacion": "Suspender"})
        elif op == "7":
            r = con.enviar({"servicio": "gesfich", "operacion": "Reasumir"})
        elif op == "8":
            r = con.enviar({"servicio": "gesfich", "operacion": "Terminar"})
        else:
            print("opcion invalida")
            continue
        print(con.recibir())


def menu_programas(con):
    while True:
        print("\n-- Programas --")
        print("  1.Guardar  2.Leer  3.Listar  4.Actualizar  5.Borrar")
        print("  6.Suspender  7.Reasumir  8.Terminar servicio  0.Volver")
        op = input("> ").strip()

        if op == "0":
            return
        elif op == "1":
            ejec = input("ejecutable (ruta): ").strip()
            args = input("args (separados por espacio): ").split()
            env = input("env (CLAVE=VALOR separados por espacio): ").split()
            r = con.enviar({"servicio": "gesprog", "operacion": "Guardar",
                            "ejecutable": ejec, "args": args, "env": env})
        elif op == "2":
            idp = input("id-programa: ").strip()
            r = con.enviar({"servicio": "gesprog", "operacion": "Leer", "id-programa": idp})
        elif op == "3":
            r = con.enviar({"servicio": "gesprog", "operacion": "Leer"})
        elif op == "4":
            idp = input("id-programa: ").strip()
            ruta = input("nueva ruta del ejecutable: ").strip()
            r = con.enviar({"servicio": "gesprog", "operacion": "Actualizar",
                            "id-programa": idp, "ruta": ruta})
        elif op == "5":
            idp = input("id-programa: ").strip()
            r = con.enviar({"servicio": "gesprog", "operacion": "Borrar", "id-programa": idp})
        elif op == "6":
            r = con.enviar({"servicio": "gesprog", "operacion": "Suspender"})
        elif op == "7":
            r = con.enviar({"servicio": "gesprog", "operacion": "Reasumir"})
        elif op == "8":
            r = con.enviar({"servicio": "gesprog", "operacion": "Terminar"})
        else:
            print("opcion invalida")
            continue
        print(con.recibir())


def menu_ejecuciones(con):
    while True:
        print("\n-- Ejecuciones --")
        print("  1.Ejecutar  2.Estado  3.Listar  4.Matar")
        print("  5.Suspender  6.Reasumir  7.Parar  0.Volver")
        op = input("> ").strip()

        if op == "0":
            return
        elif op == "1":
            msg = {"servicio": "ejecutor", "operacion": "Ejecutar",
                   "id-programa": input("id-programa: ").strip()}
            for campo in ("stdin", "stdout", "stderr"):
                val = input(f"{campo} (id-fichero o vacio): ").strip()
                if val:
                    msg[campo] = val
            r = con.enviar(msg)
        elif op == "2":
            ide = input("id-ejecucion: ").strip()
            r = con.enviar({"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": ide})
        elif op == "3":
            r = con.enviar({"servicio": "ejecutor", "operacion": "Estado"})
        elif op == "4":
            ide = input("id-ejecucion: ").strip()
            r = con.enviar({"servicio": "ejecutor", "operacion": "Matar", "id-ejecucion": ide})
        elif op == "5":
            r = con.enviar({"servicio": "ejecutor", "operacion": "Suspender"})
        elif op == "6":
            r = con.enviar({"servicio": "ejecutor", "operacion": "Reasumir"})
        elif op == "7":
            r = con.enviar({"servicio": "ejecutor", "operacion": "Parar"})
        else:
            print("opcion invalida")
            continue
        print(con.recibir())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", required=True, help="peticiones a ctrllt")
    parser.add_argument("-a", required=True, help="respuestas de ctrllt")
    args = parser.parse_args()

    print(f"[cliente] conectando a {args.c}...")
    con = canal.cliente(args.c, args.a)
    print("[cliente] conectado\n")

    while True:
        print("=== Ejecutor de Lotes ===")
        print("  1.Ficheros  2.Programas  3.Ejecuciones")
        print("  4.Terminar sistema  0.Salir")
        op = input("> ").strip()

        if op == "0":
            break
        elif op == "1":
            menu_ficheros(con)
        elif op == "2":
            menu_programas(con)
        elif op == "3":
            menu_ejecuciones(con)
        elif op == "4":
            con.enviar({"servicio": "ctrllt", "operacion": "Terminar"})
            print(con.recibir())
            break
        else:
            print("opcion invalida")

    con.cerrar()
    print("[cliente] desconectado")


if __name__ == "__main__":
    main()
