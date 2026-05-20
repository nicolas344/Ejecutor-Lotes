import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.protocolo import leer_mensaje, escribir_mensaje, validar_peticion, crear_tuberias

TUBERIA_REQ = "/tmp/tb_peticion"
TUBERIA_RES = "/tmp/tb_respuesta"


def main():
    crear_tuberias([TUBERIA_REQ, TUBERIA_RES])
    print("[servidor] Esperando cliente...")

    with open(TUBERIA_REQ, "r") as req, open(TUBERIA_RES, "w") as res:
        print("[servidor] Cliente conectado.")

        msg = leer_mensaje(req)
        print(f"[servidor] Recibido: {msg}")

        try:
            validar_peticion(msg)
        except ValueError as e:
            escribir_mensaje(res, {"estado": "error", "mensaje": str(e)})
            return

        if msg["operacion"] == "ping":
            escribir_mensaje(res, {"estado": "ok", "mensaje": "pong"})
            print("[servidor] Respondido: pong")
        else:
            escribir_mensaje(res, {"estado": "error", "mensaje": "operacion desconocida"})


if __name__ == "__main__":
    main()
