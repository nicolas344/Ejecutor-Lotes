import argparse
import json
import os
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import canal

CORRIENDO, SUSPENDIDO, PARANDO = "Corriendo", "Suspendido", "Parando"
OPS_CONTROL = {"Suspender", "Reasumir", "Parar"}


def actualizar_estados(procesos):
    for entry in procesos.values():
        if entry["estado"] == "Ejecutando":
            ret = entry["popen"].poll()
            if ret is not None:
                entry["estado"] = "Terminado"
                entry["codigo-salida"] = ret
                cerrar_archivos(entry)


def cerrar_archivos(entry):
    for f in entry["archivos"].values():
        f.close()
    entry["archivos"] = {}


def terminar_todos(procesos):
    for entry in procesos.values():
        if entry["estado"] == "Ejecutando":
            entry["popen"].terminate()
            entry["popen"].wait()
            entry["estado"] = "Terminado"
            entry["codigo-salida"] = entry["popen"].returncode
            cerrar_archivos(entry)


def resumen(id_e, entry):
    r = {"id-ejecucion": id_e, "id-programa": entry["id-programa"],
         "proceso-estado": entry["estado"]}
    if entry["estado"] == "Terminado":
        r["codigo-salida"] = entry["codigo-salida"]
    return r


def lanzar(msg, aralmac):
    id_p = msg.get("id-programa")
    if not id_p:
        return None, "falta campo: id-programa"

    ruta_meta = os.path.join(aralmac, f"{id_p}.json")
    if not os.path.exists(ruta_meta):
        return None, "programa no encontrado"

    meta = json.load(open(ruta_meta, encoding="utf-8"))
    cmd = [meta["ejecutable"]] + meta.get("args", [])
    env = dict(os.environ)
    for par in meta.get("env", []):
        if "=" in par:
            clave, valor = par.split("=", 1)
            env[clave] = valor

    archivos = {}
    fds = {"stdin": None, "stdout": None, "stderr": None}
    for campo, modo in (("stdin", "r"), ("stdout", "w"), ("stderr", "w")):
        if campo in msg:
            ruta = os.path.join(aralmac, f"{msg[campo]}.dat")
            if not os.path.exists(ruta):
                for f in archivos.values():
                    f.close()
                return None, "fichero no encontrado"
            archivos[campo] = open(ruta, modo)
            fds[campo] = archivos[campo]

    try:
        popen = subprocess.Popen(cmd, env=env, stdin=fds["stdin"],
                                 stdout=fds["stdout"], stderr=fds["stderr"])
    except (FileNotFoundError, OSError):
        for f in archivos.values():
            f.close()
        return None, "no se pudo ejecutar el programa"

    return {"popen": popen, "id-programa": id_p, "estado": "Ejecutando",
            "codigo-salida": None, "archivos": archivos}, None


def despachar(msg, estado, aralmac, procesos, contador):
    op = msg.get("operacion", "")

    if estado == SUSPENDIDO and op not in OPS_CONTROL:
        return {"estado": "error", "mensaje": "servicio suspendido"}
    if estado == PARANDO and op == "Ejecutar":
        return {"estado": "error", "mensaje": "servicio parando"}

    if op == "Ejecutar":
        entry, error = lanzar(msg, aralmac)
        if error:
            return {"estado": "error", "mensaje": error}
        id_e = f"e-{contador[0]:04d}"
        contador[0] += 1
        procesos[id_e] = entry
        return {"estado": "ok", "id-ejecucion": id_e}

    if op == "Estado":
        actualizar_estados(procesos)
        id_e = msg.get("id-ejecucion")
        if not id_e:
            return {"estado": "ok", "procesos": [resumen(e, procesos[e]) for e in procesos]}
        if id_e not in procesos:
            return {"estado": "error", "mensaje": "proceso no encontrado"}
        return {"estado": "ok", **resumen(id_e, procesos[id_e])}

    if op == "Matar":
        id_e = msg.get("id-ejecucion")
        if not id_e or id_e not in procesos:
            return {"estado": "error", "mensaje": "proceso no encontrado"}
        entry = procesos[id_e]
        if entry["estado"] == "Terminado":
            return {"estado": "error", "mensaje": "proceso no encontrado o ya terminado"}
        entry["popen"].terminate()
        entry["popen"].wait()
        entry["estado"] = "Terminado"
        entry["codigo-salida"] = entry["popen"].returncode
        cerrar_archivos(entry)
        return {"estado": "ok"}

    if op == "Suspender":
        if estado == SUSPENDIDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok"}

    if op == "Reasumir":
        if estado == CORRIENDO:
            return {"estado": "error", "mensaje": "transicion invalida"}
        return {"estado": "ok"}

    if op == "Parar":
        return {"estado": "ok"}

    return {"estado": "error", "mensaje": "operacion desconocida"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", required=True, help="tuberia de peticiones")
    parser.add_argument("-d", required=True, help="tuberia de respuestas")
    parser.add_argument("-x", required=True, help="ruta del aralmac")
    args = parser.parse_args()

    os.makedirs(args.x, exist_ok=True)
    procesos = {}
    contador = [1]
    estado = CORRIENDO

    print("[ejecutor] esperando conexion...")
    con = canal.servidor(args.e, args.d)
    print("[ejecutor] conectado")

    while True:
        try:
            msg = con.recibir()
        except (EOFError, ValueError):
            terminar_todos(procesos)
            break

        resp = despachar(msg, estado, args.x, procesos, contador)
        con.enviar(resp)

        if resp["estado"] == "ok":
            op = msg.get("operacion")
            if op == "Suspender":
                estado = SUSPENDIDO
            elif op == "Reasumir":
                estado = CORRIENDO
            elif op == "Parar":
                terminar_todos(procesos)
                break

    con.cerrar()
    print("[ejecutor] terminado")


if __name__ == "__main__":
    main()
