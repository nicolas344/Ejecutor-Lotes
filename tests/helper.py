import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from common import canal

BASE = tempfile.gettempdir()
ARALMAC = os.path.join(BASE, "aralmac_test")
PIPES = {
    "gf_req": os.path.join(BASE, "t_gf_req"), "gf_res": os.path.join(BASE, "t_gf_res"),
    "gp_req": os.path.join(BASE, "t_gp_req"), "gp_res": os.path.join(BASE, "t_gp_res"),
    "ej_req": os.path.join(BASE, "t_ej_req"), "ej_res": os.path.join(BASE, "t_ej_res"),
    "cl_req": os.path.join(BASE, "t_cl_req"), "cl_res": os.path.join(BASE, "t_cl_res"),
}


def limpiar():
    for p in PIPES.values():
        if not sys.platform.startswith("win") and os.path.exists(p):
            os.unlink(p)
    os.makedirs(ARALMAC, exist_ok=True)
    for f in os.listdir(ARALMAC):
        os.unlink(os.path.join(ARALMAC, f))


def arrancar_sistema():
    limpiar()
    P = PIPES
    procs = [
        subprocess.Popen([sys.executable, "src/gesfich/gesfich.py",
                          "-f", P["gf_req"], "-b", P["gf_res"], "-x", ARALMAC], cwd=ROOT),
        subprocess.Popen([sys.executable, "src/gesprog/gesprog.py",
                          "-p", P["gp_req"], "-c", P["gp_res"], "-x", ARALMAC], cwd=ROOT),
        subprocess.Popen([sys.executable, "src/ejecutor/ejecutor.py",
                          "-e", P["ej_req"], "-d", P["ej_res"], "-x", ARALMAC], cwd=ROOT),
    ]
    time.sleep(0.5)
    procs.append(subprocess.Popen([sys.executable, "src/ctrllt/ctrllt.py",
                                   "-c", P["cl_req"], "-a", P["cl_res"],
                                   "-f", P["gf_req"], "-b", P["gf_res"],
                                   "-p", P["gp_req"], "-r", P["gp_res"],
                                   "-e", P["ej_req"], "-d", P["ej_res"]], cwd=ROOT))
    time.sleep(0.5)
    return procs


def conectar_cliente():
    return canal.cliente(PIPES["cl_req"], PIPES["cl_res"])


def pedir(con, msg):
    con.enviar(msg)
    return con.recibir()


def apagar(con, procs):
    try:
        pedir(con, {"servicio": "ctrllt", "operacion": "Terminar"})
    except Exception:
        pass
    con.cerrar()
    for p in procs:
        p.terminate()
    limpiar()
