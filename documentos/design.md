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
       -p <tuberia-nombrada> [-q <tuberia-nombrada>]
       -e <tuberia-nombrada> [-d <tuberia-nombrada>]
```

| Parámetro | Descripción |
|-----------|-------------|
| `-c` / `-a` | Tubería cliente → ctrllt / ctrllt → cliente |
| `-f` / `-b` | Tubería ctrllt → gesfich / gesfich → ctrllt |
| `-p` / `-q` | Tubería ctrllt → gesprog / gesprog → ctrllt |
| `-e` / `-d` | Tubería ctrllt → ejecutor / ejecutor → ctrllt |

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
gesprog -p <tuberia-nombrada> [-q <tuberia-nombrada>] -x <ruta-aralmac>
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
- Programas: `p-0001.json`, `p-0002.json`, ... (metadatos: ejecutable, argumentos, ambiente)

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
{"servicio": "gesprog", "operacion": "Guardar", "ejecutable": "/usr/bin/sort", "argumentos": ["-r"], "ambiente": {"LANG": "es_ES.UTF-8"}}
```

```json
{"servicio": "ejecutor", "operacion": "Ejecutar", "id-programa": "p-0001", "stdin": "f-0001", "stdout": "f-0002"}
```

### 7.2 Estructura de Respuesta

Solo dos campos obligatorios: `estado` y `mensaje`. El resto de campos son planos y opcionales según la operación.

**Respuesta exitosa:**
```json
{"estado": "ok", "mensaje": "fichero creado", "id-fichero": "f-0001"}
```

**Respuesta de error:**
```json
{"estado": "error", "mensaje": "fichero no encontrado"}
```

| Campo | Tipo | Valores | Descripción |
|-------|------|---------|-------------|
| `estado` | string | `"ok"` / `"error"` | Resultado de la operación |
| `mensaje` | string | — | Descripción del resultado o del error |
| (otros) | — | — | Campos adicionales planos según la operación |

---

## 8. API - Operaciones Detalladas

### 8.1 Operaciones de gesfich

#### 8.1.1 Crear

Crea un fichero vacío en `aralmac` y retorna su identificador.

```json
{"servicio": "gesfich", "operacion": "Crear"}
```
```json
{"estado": "ok", "mensaje": "fichero creado", "id-fichero": "f-0001"}
```

---

#### 8.1.2 Leer

Retorna el contenido de un fichero existente.

```json
{"servicio": "gesfich", "operacion": "Leer", "id-fichero": "f-0001"}
```
```json
{"estado": "ok", "mensaje": "ok", "id-fichero": "f-0001", "contenido": "datos del fichero"}
```

Error:
```json
{"estado": "error", "mensaje": "fichero no encontrado"}
```

---

#### 8.1.3 Actualizar

Reemplaza el contenido de un fichero con datos provistos por el cliente.

```json
{"servicio": "gesfich", "operacion": "Actualizar", "id-fichero": "f-0001", "contenido": "nuevo contenido"}
```
```json
{"estado": "ok", "mensaje": "fichero actualizado", "id-fichero": "f-0001"}
```

---

#### 8.1.4 Borrar

Elimina un fichero de `aralmac`. Falla si el fichero está en uso por un proceso activo.

```json
{"servicio": "gesfich", "operacion": "Borrar", "id-fichero": "f-0001"}
```
```json
{"estado": "ok", "mensaje": "fichero borrado", "id-fichero": "f-0001"}
```

Error (en uso):
```json
{"estado": "error", "mensaje": "fichero en uso"}
```

---

#### 8.1.5 Listar

Retorna la lista de todos los ficheros registrados.

```json
{"servicio": "gesfich", "operacion": "Listar"}
```
```json
{"estado": "ok", "mensaje": "ok", "ficheros": ["f-0001", "f-0002"]}
```

---

#### 8.1.6 Control de gesfich

| Operación | Petición | Efecto |
|-----------|----------|--------|
| `Suspender` | `{"servicio":"gesfich","operacion":"Suspender"}` | Pausa el servicio |
| `Reasumir` | `{"servicio":"gesfich","operacion":"Reasumir"}` | Reanuda el servicio |
| `Terminar` | `{"servicio":"gesfich","operacion":"Terminar"}` | Termina el servicio |

Error en transición inválida:
```json
{"estado": "error", "mensaje": "transicion invalida"}
```

---

### 8.2 Operaciones de gesprog

#### 8.2.1 Guardar

Registra un nuevo programa en `aralmac`.

```json
{"servicio": "gesprog", "operacion": "Guardar", "ejecutable": "/usr/bin/sort", "argumentos": ["-r"], "ambiente": {"LANG": "es_ES.UTF-8"}}
```
```json
{"estado": "ok", "mensaje": "programa guardado", "id-programa": "p-0001"}
```

---

#### 8.2.2 Leer

Retorna los metadatos de un programa.

```json
{"servicio": "gesprog", "operacion": "Leer", "id-programa": "p-0001"}
```
```json
{"estado": "ok", "mensaje": "ok", "id-programa": "p-0001", "ejecutable": "/usr/bin/sort", "argumentos": ["-r"], "ambiente": {"LANG": "es_ES.UTF-8"}}
```

Error:
```json
{"estado": "error", "mensaje": "programa no encontrado"}
```

---

#### 8.2.3 Actualizar

Actualiza los metadatos de un programa existente.

```json
{"servicio": "gesprog", "operacion": "Actualizar", "id-programa": "p-0001", "ejecutable": "/usr/bin/sort", "argumentos": [], "ambiente": {}}
```
```json
{"estado": "ok", "mensaje": "programa actualizado", "id-programa": "p-0001"}
```

---

#### 8.2.4 Borrar

Elimina un programa de `aralmac`.

```json
{"servicio": "gesprog", "operacion": "Borrar", "id-programa": "p-0001"}
```
```json
{"estado": "ok", "mensaje": "programa borrado", "id-programa": "p-0001"}
```

Error:
```json
{"estado": "error", "mensaje": "programa no encontrado"}
```

---

#### 8.2.5 Listar

Retorna la lista de todos los programas registrados.

```json
{"servicio": "gesprog", "operacion": "Listar"}
```
```json
{"estado": "ok", "mensaje": "ok", "programas": ["p-0001", "p-0002"]}
```

---

#### 8.2.6 Control de gesprog

| Operación | Efecto |
|-----------|--------|
| `Suspender` | Pausa el servicio |
| `Reasumir` | Reanuda el servicio |
| `Terminar` | Termina el servicio |

---

### 8.3 Operaciones de ejecutor

#### 8.3.1 Ejecutar

Lanza un proceso de lotes a partir de un programa registrado. Los campos `stdin`, `stdout` y `stderr` son opcionales: si se omiten, el proceso hereda los descriptores del servicio `ejecutor`.

La operación es **no bloqueante**: el ejecutor valida, lanza el proceso, y responde de inmediato con el `id-ejecucion`.

```json
{"servicio": "ejecutor", "operacion": "Ejecutar", "id-programa": "p-0001", "stdin": "f-0001", "stdout": "f-0002", "stderr": "f-0003"}
```

Respuesta inmediata:
```json
{"estado": "ok", "mensaje": "proceso lanzado", "id-ejecucion": "e-0001"}
```

Error (programa no existe):
```json
{"estado": "error", "mensaje": "programa no encontrado"}
```

Error (fichero no existe):
```json
{"estado": "error", "mensaje": "fichero no encontrado"}
```

---

#### 8.3.2 Estado

Consulta el estado actual de un proceso.

```json
{"servicio": "ejecutor", "operacion": "Estado", "id-ejecucion": "e-0001"}
```

Proceso en ejecución:
```json
{"estado": "ok", "mensaje": "ok", "id-ejecucion": "e-0001", "estado-proceso": "Ejecutando"}
```

Proceso terminado:
```json
{"estado": "ok", "mensaje": "ok", "id-ejecucion": "e-0001", "estado-proceso": "Terminado", "codigo-salida": 0}
```

Proceso suspendido:
```json
{"estado": "ok", "mensaje": "ok", "id-ejecucion": "e-0001", "estado-proceso": "Suspendido"}
```

**Estados posibles de un proceso:** `"Ejecutando"`, `"Suspendido"`, `"Terminado"`.

El campo `codigo-salida` solo aparece cuando el estado es `"Terminado"`.

---

#### 8.3.3 Listar

Retorna todos los procesos conocidos por el ejecutor.

```json
{"servicio": "ejecutor", "operacion": "Listar"}
```
```json
{"estado": "ok", "mensaje": "ok", "ejecuciones": ["e-0001", "e-0002"]}
```

---

#### 8.3.4 Matar

Termina forzadamente un proceso en ejecución.

```json
{"servicio": "ejecutor", "operacion": "Matar", "id-ejecucion": "e-0001"}
```
```json
{"estado": "ok", "mensaje": "proceso terminado", "id-ejecucion": "e-0001"}
```

Error:
```json
{"estado": "error", "mensaje": "ejecucion no encontrada"}
```

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
3. Espera confirmación de cada uno
4. Se apaga

Respuesta al cliente:
```json
{"estado": "ok", "mensaje": "sistema terminando"}
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
| `Corriendo` | Acepta `Ejecutar`, `Estado`, `Listar`, `Matar` |
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
| Fichero en uso por proceso activo | `"fichero en uso"` |
| Servicio suspendido o terminado | `"transicion invalida"` |
| Operación desconocida | `"operacion desconocida"` |

### Errores de gesprog

| Situación | `mensaje` |
|-----------|-----------|
| Programa no existe | `"programa no encontrado"` |
| Servicio suspendido o terminado | `"transicion invalida"` |
| Operación desconocida | `"operacion desconocida"` |

### Errores de ejecutor

| Situación | `mensaje` |
|-----------|-----------|
| Programa no existe | `"programa no encontrado"` |
| Fichero referenciado no existe | `"fichero no encontrado"` |
| Ejecución no existe | `"ejecucion no encontrada"` |
| Servicio suspendido/parando | `"transicion invalida"` |
| Operación desconocida | `"operacion desconocida"` |

### Errores de ctrllt

| Situación | `mensaje` |
|-----------|-----------|
| Campo `servicio` desconocido | `"servicio desconocido"` |
| Operación propia desconocida | `"operacion ctrllt desconocida"` |
| Servicio destino no conectado | `"servicio no conectado"` |
| Error al enviar al servicio | `"error enviando solicitud al servicio"` |
| Error al leer respuesta del servicio | `"error leyendo respuesta del servicio"` |
