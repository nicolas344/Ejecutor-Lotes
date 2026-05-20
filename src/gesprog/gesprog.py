import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.protocolo import leer_mensaje, escribir_mensaje

CORRIENDO, SUSPENDIDO, TERMINADO = "Corriendo", "Suspendido", "Terminado"
OPS_CONTROL = {"Suspender", "Reasumir", "Terminar"}


def siguiente_id(aralmac):
    nums = []
    for n in os.listdir(aralmac):
        if n.startswith("p-") and n.endswith(".json"):
            try:
                nums.append(int(n[2:6]))
            except ValueError:
                pass
    return max(nums) + 1 if nums else 1


def despachar(msg, estado, aralmac, contador):
    op = msg.get("operacion", "")

    if estado == SUSPENDIDO and op not in OPS_CONTROL:
        return {"estado": "error", "mensaje": "transicion invalida"}

    if op == "Guardar":
        id_p = f"p-{contador[0]:04d}"
        contador[0] += 1
        metadata = {
            "ejecutable": msg.get("ejecutable", ""),
            "argumentos": msg.get("argumentos", []),
            "ambiente": msg.get("ambiente", {}),
        }
        with open(os.path.join(aralmac, f"{id_p}.json"), "w") as f:
            json.dump(metadata, f)
        return {"estado": "ok", "mensaje": "programa guardado", "id-programa": id_p}

    if op == "Leer":
        id_p = msg.get("id-programa")
        if not id_p:
            return {"estado": "error", "mensaje": "campo id-programa faltante"}
        ruta = os.path.join(aralmac, f"{id_p}.json")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "programa no encontrado"}
        meta = json.load(open(ruta))
        return {"estado": "ok", "mensaje": "ok", "id-programa": id_p, **meta}

    if op == "Actualizar":
        id_p = msg.get("id-programa")
        if not id_p:
            return {"estado": "error", "mensaje": "campo id-programa faltante"}
        ruta = os.path.join(aralmac, f"{id_p}.json")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "programa no encontrado"}
        metadata = {
            "ejecutable": msg.get("ejecutable", ""),
            "argumentos": msg.get("argumentos", []),
            "ambiente": msg.get("ambiente", {}),
        }
        with open(ruta, "w") as f:
            json.dump(metadata, f)
        return {"estado": "ok", "mensaje": "programa actualizado", "id-programa": id_p}

    if op == "Borrar":
        id_p = msg.get("id-programa")
        if not id_p:
            return {"estado": "error", "mensaje": "campo id-programa faltante"}
        ruta = os.path.join(aralmac, f"{id_p}.json")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "programa no encontrado"}
        os.remove(ruta)
        return {"estado": "ok", "mensaje": "programa borrado", "id-programa": id_p}

    if op == "Listar":
        programas = sorted(
            n[:-5] for n in os.listdir(aralmac)
            if n.startswith("p-") and n.endswith(".json")
        )
        return {"estado": "ok", "mensaje": "ok", "programas": programas}

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
    parser.add_argument("-p", required=True, help="Tuberia de peticiones")
    parser.add_argument("-q", required=True, help="Tuberia de respuestas")
    parser.add_argument("-x", required=True, help="Ruta del aralmac")
    args = parser.parse_args()

    os.makedirs(args.x, exist_ok=True)
    contador = [siguiente_id(args.x)]
    estado = CORRIENDO

    for t in [args.p, args.q]:
        if not os.path.exists(t):
            os.mkfifo(t)

    print(f"[gesprog] Esperando conexion en {args.p}...")
    with open(args.p, "r") as req, open(args.q, "w") as res:
        print("[gesprog] Conectado.")
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

    print("[gesprog] Terminado.")


if __name__ == "__main__":
    main()
