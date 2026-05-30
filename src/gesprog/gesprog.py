import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import canal

CORRIENDO, SUSPENDIDO = "Corriendo", "Suspendido"
OPS_CONTROL = {"Suspender", "Reasumir", "Terminar"}


def siguiente_id(aralmac):
    nums = [int(n[2:6]) for n in os.listdir(aralmac)
            if n.startswith("p-") and n.endswith(".json")]
    return max(nums) + 1 if nums else 1


def listar(aralmac):
    return sorted(n[:-5] for n in os.listdir(aralmac)
                  if n.startswith("p-") and n.endswith(".json"))


def despachar(msg, estado, aralmac, contador):
    op = msg.get("operacion", "")

    if estado == SUSPENDIDO and op not in OPS_CONTROL:
        return {"estado": "error", "mensaje": "servicio suspendido"}

    if op == "Guardar":
        if not msg.get("ejecutable"):
            return {"estado": "error", "mensaje": "falta campo: ejecutable"}
        id_p = f"p-{contador[0]:04d}"
        contador[0] += 1
        meta = {
            "ejecutable": msg["ejecutable"],
            "args": msg.get("args", []),
            "env": msg.get("env", []),
        }
        with open(os.path.join(aralmac, f"{id_p}.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f)
        return {"estado": "ok", "id-programa": id_p}

    if op == "Leer":
        id_p = msg.get("id-programa")
        if not id_p:
            return {"estado": "ok", "programas": listar(aralmac)}
        ruta = os.path.join(aralmac, f"{id_p}.json")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "programa no encontrado"}
        meta = json.load(open(ruta, encoding="utf-8"))
        programa = {
            "id-programa": id_p,
            "nombre": os.path.basename(meta["ejecutable"]),
            "args": meta.get("args", []),
            "env": meta.get("env", []),
        }
        return {"estado": "ok", "programa": programa}

    if op == "Actualizar":
        id_p = msg.get("id-programa")
        nueva = msg.get("ruta")
        if not id_p or not nueva:
            return {"estado": "error", "mensaje": "faltan campos: id-programa, ruta"}
        ruta = os.path.join(aralmac, f"{id_p}.json")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "programa no encontrado"}
        meta = json.load(open(ruta, encoding="utf-8"))
        meta["ejecutable"] = nueva
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        return {"estado": "ok"}

    if op == "Borrar":
        id_p = msg.get("id-programa")
        if not id_p:
            return {"estado": "error", "mensaje": "faltan campos: id-programa"}
        ruta = os.path.join(aralmac, f"{id_p}.json")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "programa no encontrado"}
        os.remove(ruta)
        return {"estado": "ok"}

    if op == "Suspender":
        if estado == SUSPENDIDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok"}

    if op == "Reasumir":
        if estado == CORRIENDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok"}

    if op == "Terminar":
        return {"estado": "ok"}

    return {"estado": "error", "mensaje": "operacion desconocida"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", required=True, help="tuberia de peticiones")
    parser.add_argument("-c", required=True, help="tuberia de respuestas")
    parser.add_argument("-x", required=True, help="ruta del aralmac")
    args = parser.parse_args()

    os.makedirs(args.x, exist_ok=True)
    contador = [siguiente_id(args.x)]
    estado = CORRIENDO

    print("[gesprog] esperando conexion...")
    con = canal.servidor(args.p, args.c)
    print("[gesprog] conectado")

    while True:
        try:
            msg = con.recibir()
        except (EOFError, ValueError):
            break

        resp = despachar(msg, estado, args.x, contador)
        try:
            con.enviar(resp)
        except ValueError:
            con.enviar({"estado": "error", "mensaje": "respuesta demasiado grande"})

        if resp["estado"] == "ok":
            op = msg.get("operacion")
            if op == "Suspender":
                estado = SUSPENDIDO
            elif op == "Reasumir":
                estado = CORRIENDO
            elif op == "Terminar":
                break

    con.cerrar()
    print("[gesprog] terminado")


if __name__ == "__main__":
    main()
