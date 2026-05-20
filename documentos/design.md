# Diseño del Sistema - Ejecutor de Lotes

**Curso:** Sistemas Operativos (ST0257)
**Práctica:** Ejecutor de Lotes
**Entrega:** Segunda Entrega - Implementación
**Integrantes del grupo:** 
- Nicolas Rico Montesino 
- Santiago Alvarez Diaz

---

## Tabla de Contenidos
1. [Anexos](#1-anexos)
2. [Introducción](#2-introducción)
3. [Descripción General del Sistema](#3-descripción-general-del-sistema)
4. [Arquitectura](#4-arquitectura)
5. [Componentes del Sistema](#5-componentes-del-sistema)
6. [Comunicación entre Componentes](#6-comunicación-entre-componentes)
7. [Formato de Mensajes (JSON)](#7-formato-de-mensajes-json)
8. [API - Operaciones Detalladas](#8-api---operaciones-detalladas)
9. [Máquinas de Estado](#9-máquinas-de-estado)
10. [Mensajes de Error](#10-mensajes-de-error)

---

## 1. Anexos

### 1.1 Anexo A: Convenciones de Nomenclatura

| Elemento | Formato | Ejemplo |
|----------|---------|---------|
| ID Fichero | `f-XXXX` | `f-0001` |
| ID Programa | `p-XXXX` | `p-0001` |
| ID Ejecución (proceso) | `e-XXXX` | `e-0001` |

### 1.2 Constantes del protocolo

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `MSG_MAX_LEN` | 4096 bytes | Tamaño máximo de un mensaje JSON |
| Terminador | `\n` | Cada mensaje termina con un carácter newline |

---

## 2. Introducción

El presente documento describe el diseño del sistema **Ejecutor de Lotes**, una simulación de un sistema de ejecución similar al encontrado en sistemas operativos de mainframe. El sistema permite registrar imágenes de programas (ejecutables, argumentos, ambiente) y ficheros, para luego ejecutarlos como procesos de lotes que redirigen su entrada/salida estándar a ficheros registrados en el almacenamiento.

El sistema está diseñado siguiendo una **arquitectura de microservicios**, donde cada componente tiene una responsabilidad específica y se comunica con los demás a través de **tuberías nombradas (named pipes)** utilizando mensajes en formato **JSON terminados en `\n`**.

La implementación corre en **Linux y Windows 11**. La capa de transporte (`src/common/canal.py`) abstrae la tubería: en Linux usa FIFOs half-duplex (dos tuberías por conexión) y en Windows usa named pipes full-duplex (una sola tubería). El resto del código es idéntico en ambos sistemas.

---

## 3. Descripción General del Sistema

El sistema simula la ejecución de procesos por lotes en un mainframe. El flujo general es:

1. Un **cliente** se conecta al controlador (`ctrllt`).
2. El cliente registra **ficheros** (entrada/salida) usando `gesfich`.
3. El cliente registra **programas** (ejecutables) usando `gesprog`.
4. El cliente solicita la **ejecución** de un proceso de lotes a través del `ejecutor`, indicando opcionalmente qué ficheros usar como stdin, stdout y stderr.
5. El `ejecutor` lanza el programa del `aralmac` redirigiendo sus descriptores según lo indicado.
6. El cliente puede consultar el estado o terminar los procesos en ejecución.

El sistema soporta **múltiples clientes** conectados simultáneamente a `ctrllt`.

---

## 4. Arquitectura

### 4.1 Diagrama General

```
                    ┌─────────────────────────────────────┐
                    │             aralmac                 │
                    │         (Almacenamiento)            │
                    └──────┬──────────────┬──────┬───────┘
                           │              │      │
                    acceso │       acceso │      │ acceso
                    directo│       directo│      │ directo
                           │              │      │
                    ┌──────▼──┐    ┌──────▼──┐  ┌▼─────────┐
                    │ gesfich │    │ gesprog │  │ ejecutor │
                    │(Ficheros)│   │(Programas)│ │(Procesos)│
                    └──────┬──┘    └──────┬──┘  └────┬─────┘
                           │              │           │
                           │   Tuberías Nombradas (JSON + \n)
                           └──────────────┬───────────┘
                                          │
                                          ▼
                                    ┌──────────┐
                                    │  ctrllt  │
                                    │ (Control)│
                                    │ Pasarela │
                                    └─────┬────┘
                                          │
                                   Tuberías Nombradas (JSON + \n)
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                        ┌──────────┐           ┌──────────┐
                        │cliente 1 │           │cliente 2 │
                        └──────────┘           └──────────┘
```

### 4.2 Patrón Arquitectónico

- **`ctrllt`** actúa como **pasarela**: recibe peticiones de los clientes y las dirige al servicio apropiado según el campo `servicio` del mensaje.
- Cada servicio (**`gesfich`**, **`gesprog`**, **`ejecutor`**) es independiente y accede **directamente** a `aralmac`.
- `ctrllt` **no accede** a `aralmac`.
- `ctrllt` mantiene **un hilo por cliente** para soportar múltiples clientes simultáneos.

---

## 5. Componentes del Sistema

### 5.1 cliente

**Responsabilidad:** Interfaz de usuario que envía peticiones al sistema.

**Sinopsis:**
```
cliente -c <tuberia-nombrada> [-a <tuberia-nombrada>]
```

| Parámetro | Descripción | Obligatorio |
|-----------|-------------|-------------|
| `-c <tuberia-nombrada>` | Tubería para enviar peticiones a `ctrllt` | Sí |
| `-a <tuberia-nombrada>` | Tubería para recibir respuestas (solo en sistemas half-duplex) | Opcional |

---

### 5.2 ctrllt (Control de Lotes)

**Responsabilidad:** Pasarela que recibe peticiones de los clientes, las analiza según el campo `servicio` y las dirige al servicio apropiado, esperando la respuesta y redirigiéndola al cliente.

**Sinopsis:**
```
ctrllt -c <tuberia-nombrada> [-a <tuberia-nombrada>]
       -f <tuberia-nombrada> [-b <tuberia-nombrada>]
       -p <tuberia-nombrada> [-r <tuberia-nombrada>]
       -e <tuberia-nombrada> [-d <tuberia-nombrada>]
```

| Parámetro | Descripción |
|-----------|-------------|
| `-c` / `-a` | Tubería cliente → ctrllt / ctrllt → cliente |
| `-f` / `-b` | Tubería ctrllt → gesfich / gesfich → ctrllt |
| `-p` / `-r` | Tubería ctrllt → gesprog / gesprog → ctrllt |
| `-e` / `-d` | Tubería ctrllt → ejecutor / ejecutor → ctrllt |

> En Windows solo se usa la primera tubería de cada par (full-duplex); la segunda se ignora.

**Operación propia de ctrllt:** `Terminar`

---

### 5.3 gesfich (Gestor de Ficheros)

**Responsabilidad:** Crear, actualizar, borrar y leer ficheros almacenados en `aralmac`.

**Sinopsis:**
```
gesfich -f <tuberia-nombrada> [-b <tuberia-nombrada>] -x <ruta-aralmac>
```

**Identificadores:** `f-XXXX` (ej: `f-0001`)

---

### 5.4 gesprog (Gestor de Programas)

**Responsabilidad:** Guardar, actualizar, borrar y mostrar programas almacenados en `aralmac`.

**Sinopsis:**
```
gesprog -p <tuberia-nombrada> [-c <tuberia-nombrada>] -x <ruta-aralmac>
```

**Identificadores:** `p-XXXX` (ej: `p-0001`)

---

### 5.5 ejecutor

**Responsabilidad:** Ejecutar procesos de lotes a partir de programas y ficheros almacenados en `aralmac`.

**Sinopsis:**
```
ejecutor -e <tuberia-nombrada> [-d <tuberia-nombrada>] -x <ruta-aralmac>
```

**Identificadores de ejecución:** `e-XXXX` (ej: `e-0001`)

---

### 5.6 aralmac (Área de Almacenamiento)

**Responsabilidad:** Región de almacenamiento compartida donde se persisten programas y ficheros.

Implementación: **directorio en el sistema de ficheros**.

- Ficheros: `f-0001.dat`, `f-0002.dat`, ...
- Programas: `p-0001.json`, `p-0002.json`, ... (metadatos: `ejecutable`, `args`, `env`)

---

## 6. Comunicación entre Componentes

### 6.1 Tipo de Comunicación

La comunicación entre componentes se realiza mediante **tuberías nombradas (named pipes)**:

- **Sistemas full-duplex (Windows):** Una sola tubería por conexión.
- **Sistemas half-duplex (Linux):** Dos tuberías nombradas por conexión (una para envío, otra para recepción).

> Cada tubería utilizada debe tener un **nombre único** dentro del sistema.

### 6.2 Flujo de Comunicación

```
cliente ──petición──► ctrllt ──petición──► servicio (gesfich/gesprog/ejecutor)
                                                          │
cliente ◄─respuesta── ctrllt ◄─respuesta──                ┘
```

### 6.3 Concurrencia y Múltiples Clientes

- `ctrllt` mantiene **un hilo por cliente conectado**.
- Cada hilo lee peticiones del cliente y reenvía al servicio correspondiente de forma sincrónica (espera la respuesta antes de leer la siguiente petición).
- Las escrituras en tuberías son atómicas a nivel del SO para mensajes ≤ `PIPE_BUF`, por lo que los mensajes no se mezclan.

---

## 7. Formato de Mensajes (JSON)

Todos los mensajes usan **JSON terminado en `\n`** con un tamaño máximo de **4096 bytes** (`MSG_MAX_LEN`).

### 7.1 Estructura de Petición

Los campos son **planos** (no hay objeto `params` anidado). El campo `servicio` indica el destino; `operacion` indica la acción.

```json
{"servicio": "gesfich", "operacion": "Crear"}
```

```json
{"servicio": "gesprog", "operacion": "Guardar", "ejecutable": "/usr/bin/sort", "args": ["-r"], "env": ["LANG=es_ES.UTF-8"]}
```

```json
{"servicio": "ejecutor", "operacion": "Ejecutar", "id-programa": "p-0001", "stdin": "f-0001", "stdout": "f-0002"}
```

### 7.2 Estructura de Respuesta

El único campo obligatorio es `estado`. En caso de éxito se acompañan los datos de la operación (planos); en caso de error se incluye `mensaje`.

**Respuesta exitosa:**
```json
{"estado": "ok", "id-fichero": "f-0001"}
```

**Respuesta de error:**
```json
{"estado": "error", "mensaje": "fichero no encontrado"}
```

| Campo | Tipo | Valores | Descripción |
|-------|------|---------|-------------|
| `estado` | string | `"ok"` / `"error"` | Resultado de la operación |
| `mensaje` | string | — | Descripción del error (solo cuando `estado` es `"error"`) |
| (otros) | — | — | Campos de datos planos según la operación |

---

## 8. API - Operaciones Detalladas

### 8.1 Operaciones de gesfich

#### 8.1.1 Crear

Crea un fichero vacío en `aralmac` y retorna su identificador.

```json
{"servicio": "gesfich", "operacion": "Crear"}
```
```json
{"estado": "ok", "id-fichero": "f-0001"}
```

---

#### 8.1.2 Leer (por identificador)

Retorna el contenido de un fichero existente.

```json
{"servicio": "gesfich", "operacion": "Leer", "id-fichero": "f-0001"}
```
```json
{"estado": "ok", "contenido": "datos del fichero"}
```

Error:
```json
{"estado": "error", "mensaje": "fichero no encontrado"}
```

---

#### 8.1.3 Leer (listar todos)

Si la petición no incluye `id-fichero`, retorna la lista de todos los ficheros registrados.

```json
{"servicio": "gesfich", "operacion": "Leer"}
```
```json
{"estado": "ok", "ficheros": ["f-0001", "f-0002"]}
```

---

#### 8.1.4 Actualizar

Copia el contenido de un archivo del disco (campo `ruta`) dentro del fichero indicado.

```json
{"servicio": "gesfich", "operacion": "Actualizar", "id-fichero": "f-0001", "ruta": "/ruta/al/archivo"}
```
```json
{"estado": "ok"}
```

Errores: `"faltan campos: id-fichero, ruta"`, `"fichero no encontrado"`, `"ruta no encontrada"`.

---

#### 8.1.5 Borrar

Elimina un fichero de `aralmac`.

```json
{"servicio": "gesfich", "operacion": "Borrar", "id-fichero": "f-0001"}
```
```json
{"estado": "ok"}
```

Error:
```json
{"estado": "error", "mensaje": "fichero no encontrado"}
```

---

#### 8.1.6 Control de gesfich

| Operación | Petición | Efecto |
|-----------|----------|--------|
| `Suspender` | `{"servicio":"gesfich","operacion":"Suspender"}` | Pausa el servicio |
| `Reasumir` | `{"servicio":"gesfich","operacion":"Reasumir"}` | Reanuda el servicio |
| `Terminar` | `{"servicio":"gesfich","operacion":"Terminar"}` | Termina el servicio |

Las tres responden `{"estado": "ok"}`. Una transición inválida (p.ej. `Suspender` estando suspendido) responde `{"estado": "error", "mensaje": "transicion invalida"}`.

---

### 8.2 Operaciones de gesprog

#### 8.2.1 Guardar

Registra un nuevo programa en `aralmac`. `args` y `env` son opcionales; `env` es una lista de cadenas `"CLAVE=VALOR"`.

```json
{"servicio": "gesprog", "operacion": "Guardar", "ejecutable": "/usr/bin/sort", "args": ["-r"], "env": ["LANG=es_ES.UTF-8"]}
```
```json
{"estado": "ok", "id-programa": "p-0001"}
```

Error: `{"estado": "error", "mensaje": "falta campo: ejecutable"}`

---

#### 8.2.2 Leer (por identificador)

Retorna los metadatos del programa bajo la clave `programa`. El campo `nombre` es el nombre base del ejecutable.

```json
{"servicio": "gesprog", "operacion": "Leer", "id-programa": "p-0001"}
```
```json
{"estado": "ok", "programa": {"id-programa": "p-0001", "nombre": "sort", "args": ["-r"], "env": ["LANG=es_ES.UTF-8"]}}
```

Error:
```json
{"estado": "error", "mensaje": "programa no encontrado"}
```

---

#### 8.2.3 Leer (listar todos)

Si la petición no incluye `id-programa`, retorna la lista de todos los programas registrados.

```json
{"servicio": "gesprog", "operacion": "Leer"}
```
```json
{"estado": "ok", "programas": ["p-0001", "p-0002"]}
```

---

#### 8.2.4 Actualizar

Reemplaza la ruta del ejecutable de un programa (campo `ruta`).

```json
{"servicio": "gesprog", "operacion": "Actualizar", "id-programa": "p-0001", "ruta": "/nueva/ruta"}
```
```json
{"estado": "ok"}
```

Errores: `"faltan campos: id-programa, ruta"`, `"programa no encontrado"`.

---

#### 8.2.5 Borrar

Elimina un programa de `aralmac`.

```json
{"servicio": "gesprog", "operacion": "Borrar", "id-programa": "p-0001"}
```
```json
{"estado": "ok"}
```

Error:
```json
{"estado": "error", "mensaje": "programa no encontrado"}
```

---

#### 8.2.6 Control de gesprog

`Suspender`, `Reasumir` y `Terminar`, con el mismo comportamiento que en gesfich.

---

### 8.3 Operaciones de ejecutor

#### 8.3.1 Ejecutar

Lanza un proceso de lotes a partir de un programa registrado. Los campos `stdin`, `stdout` y `stderr` son opcionales (IDs de fichero); si se omiten, el proceso hereda los descriptores del servicio.

La operación es **no bloqueante**: el ejecutor valida, lanza el proceso y responde de inmediato con el `id-ejecucion`.

```json
{"servicio": "ejecutor", "operacion": "Ejecutar", "id-programa": "p-0001", "stdin": "f-0001", "stdout": "f-0002", "stderr": "f-0003"}
```
```json
{"estado": "ok", "id-ejecucion": "e-0001"}
```

Errores: `"falta campo: id-programa"`, `"programa no encontrado"`, `"fichero no encontrado"`, `"no se pudo ejecutar el programa"`.

---

#### 8.3.2 Estado (por identificador)

Consulta el estado actual de un proceso.

```json
{"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": "e-0001"}
```

Proceso en ejecución:
```json
{"estado": "ok", "id-ejecucion": "e-0001", "id-programa": "p-0001", "proceso-estado": "Ejecutando"}
```

Proceso terminado:
```json
{"estado": "ok", "id-ejecucion": "e-0001", "id-programa": "p-0001", "proceso-estado": "Terminado", "codigo-salida": 0}
```

**Estados posibles de un proceso:** `"Ejecutando"`, `"Suspendido"`, `"Terminado"`.

El campo `codigo-salida` solo aparece cuando el estado es `"Terminado"`.

---

#### 8.3.3 Estado (todos los procesos)

Si la petición no incluye `id-ejecucion`, retorna el estado de todos los procesos bajo la clave `procesos`.

```json
{"servicio": "ejecutor", "operacion": "Estado"}
```
```json
{"estado": "ok", "procesos": [
  {"id-ejecucion": "e-0001", "id-programa": "p-0001", "proceso-estado": "Ejecutando"},
  {"id-ejecucion": "e-0002", "id-programa": "p-0002", "proceso-estado": "Terminado", "codigo-salida": 1}
]}
```

---

#### 8.3.4 Matar

Termina forzadamente un proceso en ejecución.

```json
{"servicio": "ejecutor", "operacion": "Matar", "id-ejecucion": "e-0001"}
```
```json
{"estado": "ok"}
```

Errores: `"proceso no encontrado"`, `"proceso no encontrado o ya terminado"`.

---

#### 8.3.5 Control de ejecutor

| Operación | Efecto |
|-----------|--------|
| `Suspender` | Pausa el servicio (no acepta nuevas peticiones; los procesos activos continúan) |
| `Reasumir` | Reanuda el servicio |
| `Parar` | Cierre ordenado: no acepta nuevos lotes, espera a que los activos terminen |

> **Nota:** `ctrllt` envía `Parar` al ejecutor (no `Terminar`) cuando recibe la operación `Terminar` propia.

---

### 8.4 Operación propia de ctrllt

#### 8.4.1 Terminar

Propagación ordenada de apagado del sistema.

```json
{"servicio": "ctrllt", "operacion": "Terminar"}
```

`ctrllt` ejecuta en orden:
1. Envía `Terminar` a `gesfich` y `gesprog`
2. Envía `Parar` a `ejecutor`
3. Se apaga

Respuesta al cliente:
```json
{"estado": "ok"}
```

---

## 9. Máquinas de Estado

### 9.1 ctrllt

```
┌────────┐  iniciar  ┌──────────┐  Terminar  ┌────────────┐  todos OK  ┌───────────┐
│ Inicio │ ─────────►│ Corriendo│ ──────────►│ Terminando │ ──────────►│ Terminado │
└────────┘           └──────────┘            └────────────┘            └───────────┘
```

| Estado | Descripción |
|--------|-------------|
| `Inicio` | Estado inicial |
| `Corriendo` | Aceptando y enrutando peticiones de clientes |
| `Terminando` | Esperando confirmación de gesfich, gesprog y ejecutor |
| `Terminado` | Todos los servicios finalizaron; ctrllt se apaga |

---

### 9.2 gesfich y gesprog

```
┌────────┐  iniciar  ┌──────────┐  Suspender  ┌────────────┐
│ Inicio │ ─────────►│ Corriendo│ ───────────►│ Suspendido │
└────────┘           └────┬─────┘ ◄─────────── └─────┬──────┘
                          │        Reasumir           │
                          │ Terminar         Terminar │
                          ▼                           ▼
                     ┌───────────┐
                     │ Terminado │
                     └───────────┘
```

| Estado | Descripción |
|--------|-------------|
| `Inicio` | Estado inicial |
| `Corriendo` | Procesando operaciones CRUD |
| `Suspendido` | Pausado; rechaza peticiones con `"transicion invalida"` |
| `Terminado` | Servicio finalizado |

---

### 9.3 ejecutor (servicio)

```
┌────────┐  iniciar  ┌──────────┐  Suspender  ┌────────────┐
│ Inicio │ ─────────►│ Corriendo│ ───────────►│ Suspendido │
└────────┘           └────┬─────┘ ◄─────────── └────────────┘
                          │        Reasumir
                          │ Parar
                          ▼
                     ┌──────────┐  /procesos=0  ┌───────────┐
                     │  Parando │ ─────────────►│ Terminado │
                     └──────────┘               └───────────┘
```

| Estado | Descripción |
|--------|-------------|
| `Corriendo` | Acepta `Ejecutar`, `Estado`, `Matar` |
| `Suspendido` | No acepta nuevas peticiones; los procesos activos continúan |
| `Parando` | No acepta nuevos lotes; espera a que los activos terminen |
| `Terminado` | Todos los procesos terminaron; servicio finalizado |

### 9.4 Proceso individual (dentro del ejecutor)

```
┌──────────┐  lanzar  ┌────────────┐  termina/Matar  ┌───────────┐
│  (nuevo) │ ────────►│ Ejecutando │ ───────────────►│ Terminado │
└──────────┘          └─────┬──────┘                 └───────────┘
                            │ Suspender
                            ▼
                      ┌────────────┐
                      │ Suspendido │
                      └─────┬──────┘
                            │ Reasumir
                            └──────────► Ejecutando
```

---

## 10. Mensajes de Error

Los errores se devuelven siempre con `"estado": "error"` y un `"mensaje"` en español.

### Errores de gesfich

| Situación | `mensaje` |
|-----------|-----------|
| Fichero no existe | `"fichero no encontrado"` |
| Archivo origen no existe (Actualizar) | `"ruta no encontrada"` |
| Faltan campos obligatorios | `"faltan campos: ..."` |
| Operación con el servicio suspendido | `"servicio suspendido"` |
| Suspender/Reasumir en estado inválido | `"transicion invalida"` |
| Operación desconocida | `"operacion desconocida"` |

### Errores de gesprog

| Situación | `mensaje` |
|-----------|-----------|
| Programa no existe | `"programa no encontrado"` |
| Falta el ejecutable (Guardar) | `"falta campo: ejecutable"` |
| Faltan campos obligatorios | `"faltan campos: ..."` |
| Operación con el servicio suspendido | `"servicio suspendido"` |
| Suspender/Reasumir en estado inválido | `"transicion invalida"` |
| Operación desconocida | `"operacion desconocida"` |

### Errores de ejecutor

| Situación | `mensaje` |
|-----------|-----------|
| Programa no existe | `"programa no encontrado"` |
| Fichero referenciado no existe | `"fichero no encontrado"` |
| Proceso no existe | `"proceso no encontrado"` |
| No se pudo lanzar el programa | `"no se pudo ejecutar el programa"` |
| Operación con el servicio suspendido | `"servicio suspendido"` |
| `Ejecutar` con el servicio parando | `"servicio parando"` |
| Operación desconocida | `"operacion desconocida"` |

### Errores de ctrllt

| Situación | `mensaje` |
|-----------|-----------|
| Campo `servicio` desconocido | `"servicio desconocido"` |
| Operación propia desconocida | `"operacion ctrllt desconocida"` |
| Error de comunicación con el servicio | `"error enviando solicitud al servicio"` |
