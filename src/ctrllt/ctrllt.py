import argparse
import os
import sys
import threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import canal

SERVICIOS = ("gesfich", "gesprog", "ejecutor")


def crear_tuberias(*rutas):
    if sys.platform.startswith("win"):
        return
    for ruta in rutas:
        if not os.path.exists(ruta):
            os.mkfifo(ruta)


def reenviar(con, lock, msg):
    with lock:
        try:
            con.enviar(msg)
            return con.recibir()
        except Exception:
            return {"estado": "error", "mensaje": "error enviando solicitud al servicio"}


def apagar(servicios, locks):
    for nombre in ("gesfich", "gesprog"):
        reenviar(servicios[nombre], locks[nombre], {"servicio": nombre, "operacion": "Terminar"})
    reenviar(servicios["ejecutor"], locks["ejecutor"], {"servicio": "ejecutor", "operacion": "Parar"})


def atender(cli, servicios, locks):
    while True:
        try:
            msg = cli.recibir()
        except (EOFError, ValueError):
            return False

        servicio = msg.get("servicio", "")
        op = msg.get("operacion", "")

        if servicio == "ctrllt":
            if op == "Terminar":
                apagar(servicios, locks)
                cli.enviar({"estado": "ok"})
                return True
            cli.enviar({"estado": "error", "mensaje": "operacion ctrllt desconocida"})
            continue

        if servicio not in servicios:
            cli.enviar({"estado": "error", "mensaje": "servicio desconocido"})
            continue

        cli.enviar(reenviar(servicios[servicio], locks[servicio], msg))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", required=True, help="peticiones del cliente")
    parser.add_argument("-a", required=True, help="respuestas al cliente")
    parser.add_argument("-f", required=True, help="req a gesfich")
    parser.add_argument("-b", required=True, help="res de gesfich")
    parser.add_argument("-p", required=True, help="req a gesprog")
    parser.add_argument("-r", required=True, help="res de gesprog")
    parser.add_argument("-e", required=True, help="req a ejecutor")
    parser.add_argument("-d", required=True, help="res de ejecutor")
    args = parser.parse_args()

    print("[ctrllt] creando tuberias...")
    crear_tuberias(
        args.f, args.b,
        args.p, args.r,
        args.e, args.d,
        args.c, args.a,
    )

    print("[ctrllt] conectando a servicios...")
    servicios = {
        "gesfich": canal.cliente(args.f, args.b),
        "gesprog": canal.cliente(args.p, args.r),
        "ejecutor": canal.cliente(args.e, args.d),
    }
    locks = {nombre: threading.Lock() for nombre in servicios}
    print("[ctrllt] listo")

    shutdown_event = threading.Event()
    threads = []

    def handle_client(cli):
        terminar = atender(cli, servicios, locks)
        cli.cerrar()
        print("[ctrllt] cliente desconectado")
        if terminar:
            shutdown_event.set()

    while not shutdown_event.is_set():
        cli = canal.servidor(args.c, args.a)
        if shutdown_event.is_set():
            cli.cerrar()
            break
        print("[ctrllt] cliente conectado")
        t = threading.Thread(target=handle_client, args=(cli,), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=2)

    for con in servicios.values():
        con.cerrar()
    print("[ctrllt] terminado")


if __name__ == "__main__":
    main()
