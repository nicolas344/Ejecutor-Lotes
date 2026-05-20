import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.protocolo import leer_mensaje, escribir_mensaje

CORRIENDO, SUSPENDIDO, TERMINADO = "Corriendo", "Suspendido", "Terminado"
OPS_CONTROL = {"Suspender", "Reasumir", "Terminar"}


def siguiente_id(aralmac):
    nums = []
    for n in os.listdir(aralmac):
        if n.startswith("f-") and n.endswith(".dat"):
            try:
                nums.append(int(n[2:6]))
            except ValueError:
                pass
    return max(nums) + 1 if nums else 1


def despachar(msg, estado, aralmac, contador):
    op = msg.get("operacion", "")

    if estado == SUSPENDIDO and op not in OPS_CONTROL:
        return {"estado": "error", "mensaje": "transicion invalida"}

    if op == "Crear":
        id_f = f"f-{contador[0]:04d}"
        contador[0] += 1
        open(os.path.join(aralmac, f"{id_f}.dat"), "w").close()
        return {"estado": "ok", "mensaje": "fichero creado", "id-fichero": id_f}

    if op == "Leer":
        id_f = msg.get("id-fichero")
        if not id_f:
            return {"estado": "error", "mensaje": "campo id-fichero faltante"}
        ruta = os.path.join(aralmac, f"{id_f}.dat")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "fichero no encontrado"}
        return {"estado": "ok", "mensaje": "ok", "id-fichero": id_f, "contenido": open(ruta).read()}

    if op == "Actualizar":
        id_f = msg.get("id-fichero")
        if not id_f:
            return {"estado": "error", "mensaje": "campo id-fichero faltante"}
        ruta = os.path.join(aralmac, f"{id_f}.dat")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "fichero no encontrado"}
        open(ruta, "w").write(msg.get("contenido", ""))
        return {"estado": "ok", "mensaje": "fichero actualizado", "id-fichero": id_f}

    if op == "Borrar":
        id_f = msg.get("id-fichero")
        if not id_f:
            return {"estado": "error", "mensaje": "campo id-fichero faltante"}
        ruta = os.path.join(aralmac, f"{id_f}.dat")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "fichero no encontrado"}
        os.remove(ruta)
        return {"estado": "ok", "mensaje": "fichero borrado", "id-fichero": id_f}

    if op == "Listar":
        ficheros = sorted(
            n[:-4] for n in os.listdir(aralmac)
            if n.startswith("f-") and n.endswith(".dat")
        )
        return {"estado": "ok", "mensaje": "ok", "ficheros": ficheros}

    if op == "Suspender":
        if estado == SUSPENDIDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok", "mensaje": "servicio suspendido"}

    if op == "Reasumir":
        if estado == CORRIENDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok", "mensaje": "servicio reanudado"}

    if op == "Terminar":
        return {"estado": "ok", "mensaje": "servicio terminado"}

    return {"estado": "error", "mensaje": "operacion desconocida"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", required=True, help="Tuberia de peticiones")
    parser.add_argument("-b", required=True, help="Tuberia de respuestas")
    parser.add_argument("-x", required=True, help="Ruta del aralmac")
    args = parser.parse_args()

    os.makedirs(args.x, exist_ok=True)
    contador = [siguiente_id(args.x)]
    estado = CORRIENDO

    for t in [args.f, args.b]:
        if not os.path.exists(t):
            os.mkfifo(t)

    print(f"[gesfich] Esperando conexion en {args.f}...")
    with open(args.f, "r") as req, open(args.b, "w") as res:
        print("[gesfich] Conectado.")
        while True:
            try:
                msg = leer_mensaje(req)
            except (EOFError, ValueError):
                break

            respuesta = despachar(msg, estado, args.x, contador)
            escribir_mensaje(res, respuesta)

            op = msg.get("operacion", "")
            if respuesta["estado"] == "ok":
                if op == "Suspender":
                    estado = SUSPENDIDO
                elif op == "Reasumir":
                    estado = CORRIENDO
                elif op == "Terminar":
                    break

    print("[gesfich] Terminado.")


if __name__ == "__main__":
    main()
