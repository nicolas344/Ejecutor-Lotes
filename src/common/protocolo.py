import json
import os

MSG_MAX_LEN = 4096


def escribir_mensaje(archivo, datos):
    texto = json.dumps(datos, ensure_ascii=False) + "\n"
    if len(texto.encode("utf-8")) > MSG_MAX_LEN:
        raise ValueError(f"Mensaje supera {MSG_MAX_LEN} bytes")
    archivo.write(texto)
    archivo.flush()


def leer_mensaje(archivo):
    linea = archivo.readline()
    if not linea:
        raise EOFError("Tubería cerrada")
    try:
        return json.loads(linea)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido: {e}")


def validar_peticion(msg):
    if "servicio" not in msg:
        raise ValueError("Campo 'servicio' faltante")
    if "operacion" not in msg:
        raise ValueError("Campo 'operacion' faltante")


def crear_tuberias(rutas):
    for ruta in rutas:
        if not os.path.exists(ruta):
            os.mkfifo(ruta)
