import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import canal

CORRIENDO, SUSPENDIDO = "Corriendo", "Suspendido"
OPS_CONTROL = {"Suspender", "Reasumir", "Terminar"}


def siguiente_id(aralmac):
    nums = [int(n[2:6]) for n in os.listdir(aralmac)
            if n.startswith("f-") and n.endswith(".dat")]
    return max(nums) + 1 if nums else 1


def listar(aralmac):
    return sorted(n[:-4] for n in os.listdir(aralmac)
                  if n.startswith("f-") and n.endswith(".dat"))


def despachar(msg, estado, aralmac, contador):
    op = msg.get("operacion", "")

    if estado == SUSPENDIDO and op not in OPS_CONTROL:
        return {"estado": "error", "mensaje": "servicio suspendido"}

    if op == "Crear":
        id_f = f"f-{contador[0]:04d}"
        contador[0] += 1
        open(os.path.join(aralmac, f"{id_f}.dat"), "w").close()
        return {"estado": "ok", "id-fichero": id_f}

    if op == "Leer":
        id_f = msg.get("id-fichero")
        if not id_f:
            return {"estado": "ok", "ficheros": listar(aralmac)}
        ruta = os.path.join(aralmac, f"{id_f}.dat")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "fichero no encontrado"}
        return {"estado": "ok", "contenido": open(ruta, encoding="utf-8").read()}

    if op == "Actualizar":
        id_f = msg.get("id-fichero")
        origen = msg.get("ruta")
        if not id_f or not origen:
            return {"estado": "error", "mensaje": "faltan campos: id-fichero, ruta"}
        destino = os.path.join(aralmac, f"{id_f}.dat")
        if not os.path.exists(destino):
            return {"estado": "error", "mensaje": "fichero no encontrado"}
        if not os.path.exists(origen):
            return {"estado": "error", "mensaje": "ruta no encontrada"}
        with open(origen, encoding="utf-8") as src, open(destino, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        return {"estado": "ok"}

    if op == "Borrar":
        id_f = msg.get("id-fichero")
        if not id_f:
            return {"estado": "error", "mensaje": "faltan campos: id-fichero"}
        ruta = os.path.join(aralmac, f"{id_f}.dat")
        if not os.path.exists(ruta):
            return {"estado": "error", "mensaje": "fichero no encontrado"}
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
    parser.add_argument("-f", required=True, help="tuberia de peticiones")
    parser.add_argument("-b", required=True, help="tuberia de respuestas")
    parser.add_argument("-x", required=True, help="ruta del aralmac")
    args = parser.parse_args()

    os.makedirs(args.x, exist_ok=True)
    contador = [siguiente_id(args.x)]
    estado = CORRIENDO

    print("[gesfich] esperando conexion...")
    con = canal.servidor(args.f, args.b)
    print("[gesfich] conectado")

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
    print("[gesfich] terminado")


if __name__ == "__main__":
    main()
