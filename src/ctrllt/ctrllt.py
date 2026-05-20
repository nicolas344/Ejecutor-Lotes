import argparse
import os
import sys
import threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.protocolo import leer_mensaje, escribir_mensaje

SERVICIOS_VALIDOS = {"gesfich", "gesprog", "ejecutor"}


def enviar_a_servicio(req, res, lock, msg):
    with lock:
        try:
            escribir_mensaje(req, msg)
            return leer_mensaje(res)
        except Exception:
            return {"estado": "error", "mensaje": "error enviando solicitud al servicio"}


def apagar_sistema(pipes, locks):
    for nombre in ["gesfich", "gesprog"]:
        req, res = pipes[nombre]
        enviar_a_servicio(req, res, locks[nombre], {"servicio": nombre, "operacion": "Terminar"})

    req, res = pipes["ejecutor"]
    enviar_a_servicio(req, res, locks["ejecutor"], {"servicio": "ejecutor", "operacion": "Parar"})


def manejar_cliente(cliente_req, cliente_res, pipes, locks):
    while True:
        try:
            msg = leer_mensaje(cliente_req)
        except (EOFError, ValueError):
            break

        servicio = msg.get("servicio", "")
        op = msg.get("operacion", "")

        if servicio == "ctrllt":
            if op == "Terminar":
                apagar_sistema(pipes, locks)
                escribir_mensaje(cliente_res, {"estado": "ok", "mensaje": "sistema terminando"})
                return True  # señal de apagado
            else:
                escribir_mensaje(cliente_res, {"estado": "error", "mensaje": "operacion ctrllt desconocida"})
                continue

        if servicio not in SERVICIOS_VALIDOS:
            escribir_mensaje(cliente_res, {"estado": "error", "mensaje": "servicio desconocido"})
            continue

        req, res = pipes[servicio]
        respuesta = enviar_a_servicio(req, res, locks[servicio], msg)
        escribir_mensaje(cliente_res, respuesta)

    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", required=True, help="Tuberia peticiones del cliente")
    parser.add_argument("-a", required=True, help="Tuberia respuestas al cliente")
    parser.add_argument("-f", required=True, help="Tuberia req a gesfich")
    parser.add_argument("-b", required=True, help="Tuberia res de gesfich")
    parser.add_argument("-p", required=True, help="Tuberia req a gesprog")
    parser.add_argument("-q", required=True, help="Tuberia res de gesprog")
    parser.add_argument("-e", required=True, help="Tuberia req a ejecutor")
    parser.add_argument("-d", required=True, help="Tuberia res de ejecutor")
    args = parser.parse_args()

    print("[ctrllt] Conectando a servicios...")
    gesfich_req = open(args.f, "w")
    gesfich_res = open(args.b, "r")
    gesprog_req = open(args.p, "w")
    gesprog_res = open(args.q, "r")
    ejecutor_req = open(args.e, "w")
    ejecutor_res = open(args.d, "r")

    pipes = {
        "gesfich": (gesfich_req, gesfich_res),
        "gesprog": (gesprog_req, gesprog_res),
        "ejecutor": (ejecutor_req, ejecutor_res),
    }
    locks = {nombre: threading.Lock() for nombre in pipes}

    for t in [args.c, args.a]:
        if not os.path.exists(t):
            os.mkfifo(t)

    print(f"[ctrllt] Listo. Aceptando clientes en {args.c}...")
    while True:
        with open(args.c, "r") as cliente_req, open(args.a, "w") as cliente_res:
            print("[ctrllt] Cliente conectado.")
            debe_terminar = manejar_cliente(cliente_req, cliente_res, pipes, locks)
        print("[ctrllt] Cliente desconectado.")
        if debe_terminar:
            break

    for f in [gesfich_req, gesfich_res, gesprog_req, gesprog_res, ejecutor_req, ejecutor_res]:
        f.close()

    print("[ctrllt] Terminado.")


if __name__ == "__main__":
    main()
