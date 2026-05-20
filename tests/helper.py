import os
import subprocess
import sys
import time

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from common.protocolo import leer_mensaje, escribir_mensaje

ARALMAC = "/tmp/aralmac_test"
PIPES = {
    "gf_req": "/tmp/t_gf_req", "gf_res": "/tmp/t_gf_res",
    "gp_req": "/tmp/t_gp_req", "gp_res": "/tmp/t_gp_res",
    "ej_req": "/tmp/t_ej_req", "ej_res": "/tmp/t_ej_res",
    "cl_req": "/tmp/t_cl_req", "cl_res": "/tmp/t_cl_res",
}


def limpiar_pipes():
    for p in PIPES.values():
        if os.path.exists(p):
            os.unlink(p)


def limpiar_aralmac():
    if os.path.exists(ARALMAC):
        for f in os.listdir(ARALMAC):
            os.unlink(os.path.join(ARALMAC, f))


def arrancar_sistema():
    limpiar_pipes()
    os.makedirs(ARALMAC, exist_ok=True)
    limpiar_aralmac()

    P = PIPES
    procs = []

    procs.append(subprocess.Popen(
        [sys.executable, "src/gesfich/gesfich.py", "-f", P["gf_req"], "-b", P["gf_res"], "-x", ARALMAC],
        cwd=ROOT
    ))
    procs.append(subprocess.Popen(
        [sys.executable, "src/gesprog/gesprog.py", "-p", P["gp_req"], "-q", P["gp_res"], "-x", ARALMAC],
        cwd=ROOT
    ))
    procs.append(subprocess.Popen(
        [sys.executable, "src/ejecutor/ejecutor.py", "-e", P["ej_req"], "-d", P["ej_res"], "-x", ARALMAC],
        cwd=ROOT
    ))
    time.sleep(0.5)

    procs.append(subprocess.Popen(
        [sys.executable, "src/ctrllt/ctrllt.py",
         "-c", P["cl_req"], "-a", P["cl_res"],
         "-f", P["gf_req"], "-b", P["gf_res"],
         "-p", P["gp_req"], "-q", P["gp_res"],
         "-e", P["ej_req"], "-d", P["ej_res"],
         ],
        cwd=ROOT
    ))
    time.sleep(0.5)
    return procs


def conectar_cliente():
    req = open(PIPES["cl_req"], "w")
    res = open(PIPES["cl_res"], "r")
    return req, res


def enviar(req, res, msg):
    escribir_mensaje(req, msg)
    return leer_mensaje(res)


def apagar(req, res, procs):
    try:
        enviar(req, res, {"servicio": "ctrllt", "operacion": "Terminar"})
    except Exception:
        pass
    req.close()
    res.close()
    for p in procs:
        p.terminate()
    limpiar_pipes()
