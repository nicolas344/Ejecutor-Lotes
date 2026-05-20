import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.protocolo import escribir_mensaje, leer_mensaje

TUBERIA_REQ = "/tmp/tb_peticion"
TUBERIA_RES = "/tmp/tb_respuesta"


def main():
    print("[cliente] Conectando...")

    with open(TUBERIA_REQ, "w") as req, open(TUBERIA_RES, "r") as res:
        print("[cliente] Conectado.")

        peticion = {"servicio": "test", "operacion": "ping"}
        escribir_mensaje(req, peticion)
        print(f"[cliente] Enviado: {peticion}")

        respuesta = leer_mensaje(res)
        print(f"[cliente] Respuesta: {respuesta}")

        if respuesta.get("estado") == "ok" and respuesta.get("mensaje") == "pong":
            print("[cliente] OK - capa de mensajes funciona")
        else:
            print(f"[cliente] FALLO - respuesta inesperada")


if __name__ == "__main__":
    main()
