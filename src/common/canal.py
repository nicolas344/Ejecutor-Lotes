import json
import os
import sys

MSG_MAX_LEN = 4096
_WIN = sys.platform.startswith("win")

if _WIN:
    import time
    import win32pipe
    import win32file
    import pywintypes
    import winerror


def _codificar(datos):
    texto = json.dumps(datos, ensure_ascii=False) + "\n"
    if len(texto.encode("utf-8")) > MSG_MAX_LEN:
        raise ValueError(f"mensaje supera {MSG_MAX_LEN} bytes")
    return texto


def validar_peticion(msg):
    if "servicio" not in msg or "operacion" not in msg:
        raise ValueError("peticion invalida")


# --- Linux: tuberias nombradas half-duplex (dos FIFO) ---
class _CanalFifo:
    def __init__(self, lectura, escritura):
        self.lectura = lectura
        self.escritura = escritura

    def recibir(self):
        linea = self.lectura.readline()
        if not linea:
            raise EOFError("tuberia cerrada")
        return json.loads(linea)

    def enviar(self, datos):
        self.escritura.write(_codificar(datos))
        self.escritura.flush()

    def cerrar(self):
        self.lectura.close()
        self.escritura.close()


# --- Windows: named pipe full-duplex (una sola tuberia) ---
class _CanalWin:
    def __init__(self, handle):
        self.handle = handle
        self.buffer = b""

    def recibir(self):
        while b"\n" not in self.buffer:
            try:
                _, datos = win32file.ReadFile(self.handle, 65536)
            except pywintypes.error:
                raise EOFError("tuberia cerrada")
            if not datos:
                raise EOFError("tuberia cerrada")
            self.buffer += datos
        linea, self.buffer = self.buffer.split(b"\n", 1)
        return json.loads(linea.decode("utf-8"))

    def enviar(self, datos):
        win32file.WriteFile(self.handle, _codificar(datos).encode("utf-8"))

    def cerrar(self):
        try:
            win32file.CloseHandle(self.handle)
        except pywintypes.error:
            pass


def _ruta_win(nombre):
    return r"\\.\pipe\\" + os.path.basename(nombre)


def servidor(req, res=None):
    """Lado servicio: crea la tuberia y espera a que el ctrllt se conecte."""
    if _WIN:
        handle = win32pipe.CreateNamedPipe(
            _ruta_win(req),
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
            win32pipe.PIPE_UNLIMITED_INSTANCES, 65536, 65536, 0, None,
        )
        win32pipe.ConnectNamedPipe(handle, None)
        return _CanalWin(handle)
    for ruta in (req, res):
        if not os.path.exists(ruta):
            os.mkfifo(ruta)
    return _CanalFifo(open(req, "r"), open(res, "w"))


def cliente(req, res=None):
    """Lado que se conecta a una tuberia ya creada."""
    if _WIN:
        ruta = _ruta_win(req)
        while True:
            try:
                handle = win32file.CreateFile(
                    ruta, win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0, None, win32file.OPEN_EXISTING, 0, None,
                )
                break
            except pywintypes.error as e:
                if e.winerror in (winerror.ERROR_FILE_NOT_FOUND, winerror.ERROR_PIPE_BUSY):
                    time.sleep(0.1)
                    continue
                raise
        win32pipe.SetNamedPipeHandleState(handle, win32pipe.PIPE_READMODE_BYTE, None, None)
        return _CanalWin(handle)
    escritura = open(req, "w")
    lectura = open(res, "r")
    return _CanalFifo(lectura, escritura)
