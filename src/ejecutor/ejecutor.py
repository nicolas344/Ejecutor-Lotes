import argparse
import json
import os
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.protocolo import leer_mensaje, escribir_mensaje

CORRIENDO, SUSPENDIDO, PARANDO, TERMINADO = "Corriendo", "Suspendido", "Parando", "Terminado"
OPS_CONTROL = {"Suspender", "Reasumir", "Parar"}


def actualizar_estados(procesos):
    for entry in procesos.values():
        if entry["estado"] == "Ejecutando":
            ret = entry["popen"].poll()
            if ret is not None:
                entry["estado"] = "Terminado"
                entry["codigo-salida"] = ret
                for f in entry["archivos"].values():
                    f.close()
                entry["archivos"] = {}


def terminar_todos(procesos):
    for entry in procesos.values():
        if entry["estado"] == "Ejecutando":
            entry["popen"].terminate()
            entry["popen"].wait()
            for f in entry["archivos"].values():
                f.close()
            entry["archivos"] = {}
            entry["estado"] = "Terminado"


def lanzar(msg, aralmac):
    id_p = msg.get("id-programa")
    if not id_p:
        return None, "campo id-programa faltante"

    ruta_meta = os.path.join(aralmac, f"{id_p}.json")
    if not os.path.exists(ruta_meta):
        return None, "programa no encontrado"

    meta = json.load(open(ruta_meta))
    cmd = [meta["ejecutable"]] + meta.get("argumentos", [])
    env = {**os.environ, **meta.get("ambiente", {})}

    archivos = {}
    stdin_f = stdout_f = stderr_f = None

    for campo, modo in [("stdin", "r"), ("stdout", "w"), ("stderr", "w")]:
        if campo in msg:
            ruta = os.path.join(aralmac, f"{msg[campo]}.dat")
            if not os.path.exists(ruta):
                for f in archivos.values():
                    f.close()
                return None, "fichero no encontrado"
            fd = open(ruta, modo)
            archivos[campo] = fd
            if campo == "stdin":
                stdin_f = fd
            elif campo == "stdout":
                stdout_f = fd
            else:
                stderr_f = fd

    try:
        popen = subprocess.Popen(cmd, env=env, stdin=stdin_f, stdout=stdout_f, stderr=stderr_f)
    except FileNotFoundError:
        for f in archivos.values():
            f.close()
        return None, "ejecutable no encontrado"

    return {"popen": popen, "estado": "Ejecutando", "codigo-salida": None, "archivos": archivos}, None


def despachar(msg, estado, aralmac, procesos, contador):
    op = msg.get("operacion", "")

    if estado == SUSPENDIDO and op not in OPS_CONTROL:
        return {"estado": "error", "mensaje": "transicion invalida"}

    if estado == PARANDO and op == "Ejecutar":
        return {"estado": "error", "mensaje": "transicion invalida"}

    if op == "Ejecutar":
        entry, error = lanzar(msg, aralmac)
        if error:
            return {"estado": "error", "mensaje": error}
        id_e = f"e-{contador[0]:04d}"
        contador[0] += 1
        procesos[id_e] = entry
        return {"estado": "ok", "mensaje": "proceso lanzado", "id-ejecucion": id_e}

    if op == "Estado":
        id_e = msg.get("id-ejecucion")
        if not id_e or id_e not in procesos:
            return {"estado": "error", "mensaje": "ejecucion no encontrada"}
        actualizar_estados(procesos)
        entry = procesos[id_e]
        resp = {"estado": "ok", "mensaje": "ok", "id-ejecucion": id_e, "estado-proceso": entry["estado"]}
        if entry["estado"] == "Terminado":
            resp["codigo-salida"] = entry["codigo-salida"]
        return resp

    if op == "Listar":
        actualizar_estados(procesos)
        return {"estado": "ok", "mensaje": "ok", "ejecuciones": list(procesos.keys())}

    if op == "Matar":
        id_e = msg.get("id-ejecucion")
        if not id_e or id_e not in procesos:
            return {"estado": "error", "mensaje": "ejecucion no encontrada"}
        entry = procesos[id_e]
        if entry["estado"] == "Terminado":
            return {"estado": "error", "mensaje": "ejecucion ya terminada"}
        entry["popen"].terminate()
        entry["popen"].wait()
        entry["estado"] = "Terminado"
        entry["codigo-salida"] = entry["popen"].returncode
        for f in entry["archivos"].values():
            f.close()
        entry["archivos"] = {}
        return {"estado": "ok", "mensaje": "proceso terminado", "id-ejecucion": id_e}

    if op == "Suspender":
        if estado == SUSPENDIDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok", "mensaje": "servicio suspendido"}

    if op == "Reasumir":
        if estado == CORRIENDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok", "mensaje": "servicio reanudado"}

    if op == "Parar":
        return {"estado": "ok", "mensaje": "servicio parando"}

    return {"estado": "error", "mensaje": "operacion desconocida"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", required=True, help="Tuberia de peticiones")
    parser.add_argument("-d", required=True, help="Tuberia de respuestas")
    parser.add_argument("-x", required=True, help="Ruta del aralmac")
    args = parser.parse_args()

    os.makedirs(args.x, exist_ok=True)
    procesos = {}
    contador = [1]
    estado = CORRIENDO

    for t in [args.e, args.d]:
        if not os.path.exists(t):
            os.mkfifo(t)

    print(f"[ejecutor] Esperando conexion en {args.e}...")
    with open(args.e, "r") as req, open(args.d, "w") as res:
        print("[ejecutor] Conectado.")
        while True:
            try:
                msg = leer_mensaje(req)
            except (EOFError, ValueError):
                terminar_todos(procesos)
                break

            respuesta = despachar(msg, estado, args.x, procesos, contador)
            escribir_mensaje(res, respuesta)

            op = msg.get("operacion", "")
            if respuesta["estado"] == "ok":
                if op == "Suspender":
                    estado = SUSPENDIDO
                elif op == "Reasumir":
                    estado = CORRIENDO
                elif op == "Parar":
                    terminar_todos(procesos)
                    break

    print("[ejecutor] Terminado.")


if __name__ == "__main__":
    main()
