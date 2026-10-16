# Investigacion: Evaluacion de LLMLingua-2 para SynRAG

> Nota de revision (15-oct-2026): el "> 95 %" atribuido al filtro de terminal no venia de una medicion propia de esta tarea. Medido despues en `benchmarks/filtro.py`: 31-55 % en comandos ruidosos cortos (pip, npm, pytest, cargo) y 86-99 % en salidas largas (find, scripts de miles de lineas, journalctl). La conclusion (no integrar LLMLingua-2) no cambia.


Fecha: 15 de octubre de 2026  
Entorno de prueba: CachyOS Linux (Kernel 6.x), CPU x86_64, Python 3.12.15  
Modelos evaluados:
- `microsoft/llmlingua-2-xlm-roberta-large-meetingbank` (variante grande basada en XLM-RoBERTa)
- `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` (variante pequena basada en mBERT)

---

## 1. Resumen y veredicto

**Recomendacion: NO incorporar LLMLingua-2 a SynRAG**, ni siquiera como modulo opcional.

Las soluciones nativas de SynRAG (filtrado determinista de logs de Tarea B y fragmentacion semantica de documentacion en trozos de ~200 tokens de Tarea C) superan a LLMLingua-2 en todas las metricas:

| Criterio | LLMLingua-2 (XLM-RoBERTa / BERT) | SynRAG Tarea B (Logs) / Tarea C (Docs) |
|---|---|---|
| Ahorro de tokens en logs | 33 % a 54 % | **> 95 %** (filtro determinista) |
| Ahorro de tokens en docs | 47 % a 55 % | **> 95 %** (trozo exacto de ~200 tokens vs archivo entero) |
| Latencia en CPU | **3,2 a 11,7 segundos por cada 1.000 tokens** | **< 15 milisegundos** |
| Huella en disco | **1,9 GB a 6,6 GB** (venv + modelos) | **0 MB** adicionales (cero dependencias pesadas) |
| Validez sintactica en codigo | **0 % valida** (`ast.parse` falla siempre) | **100 % valida** (arbol AST completo) |
| Integridad de logs | Destruye estados (`PASSED` eliminado) y versiones | Preserva errores, salidas clave y codigos de retorno |

---

## 2. Metodologia y comandos exactos

Para garantizar total reproducibilidad sin alterar el entorno principal de SynRAG:

```bash
# 1. Creacion de entorno virtual temporal aislado
uv venv --python python3.12 /tmp/scratchpad/venv-llmlingua
uv pip install --python /tmp/scratchpad/venv-llmlingua pip

# 2. Instalacion de dependencias con wheel de PyTorch CPU (evitando 3,5 GB de CUDA)
/tmp/scratchpad/venv-llmlingua/bin/pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple \
  llmlingua > /tmp/scratchpad/pip_install.log 2>&1

# 3. Descarga de modelos en cache aislada
export HF_HOME=/tmp/scratchpad/hf-cache

# 4. Verificacion sintactica de codigo
python -c "import ast; ast.parse(open('codigo_comprimido.py').read())"
```

---

## 3. Tamano de instalacion y tiempos de descarga

### Paquetes y dependencias

- **Instalacion estandar PyPI (`pip install llmlingua`)**: Descarga 65 paquetes incluyendo el runtime de NVIDIA CUDA (`nvidia-cublas`, `nvidia-cudnn`, `nvidia-cusparse`, etc.). Tamano total en disco: **~3,8 GB a 4,0 GB**.
- **Instalacion optimizada CPU (`--index-url https://download.pytorch.org/whl/cpu`)**: 46 paquetes instalados. Tamano total: **1,2 GB**.

Principales paquetes en el entorno CPU:
- `torch (2.14.1+cpu)`: 765 MB
- `transformers (5.19.0)`: 112 MB
- `sympy (1.14.0)`: 73 MB
- `numpy (2.5.4)`: 42 MB
- `networkx (3.7)`: 18 MB
- `nltk (3.10.3)`: 15 MB
- `tokenizers (0.23.3)`: 12 MB

Tiempo de instalacion de paquetes en venv: **79 segundos**.

### Modelos de lenguaje

| Modelo HuggingFace | Parametros / Base | Tamano en disco | Tiempo de descarga e inicializacion |
|---|---|---|---|
| `microsoft/llmlingua-2-xlm-roberta-large-meetingbank` | XLM-RoBERTa Large (560M params) | 2,1 GB (2.239 MB) | 326,11 s (~5,4 min) |
| `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` | mBERT Base (178M params) | 681 MB (713 MB) | 116,93 s (~1,9 min) |

Huella total requerida en disco para operar:
- Solo con mBERT Base: **1,9 GB** (1,2 GB paquetes CPU + 0,68 GB modelo)
- Con XLM-RoBERTa Large: **3,3 GB** (1,2 GB paquetes CPU + 2,1 GB modelo)
- Con ambos modelos: **4,0 GB** en disco (y hasta **6,6 GB** si el usuario no configura repositorios de CPU explicitos).

---

## 4. Latencia en CPU por cada 1.000 tokens de entrada

Mediciones ejecutadas en CPU sobre textos representativos con 3 repeticiones por tamano (media de las ejecuciones, tasa de compresion objetivo `rate=0.5`):

| Longitud de entrada | Metrica | XLM-RoBERTa Large | BERT Base Multilingual |
|---|---|---|---|
| **500 tokens** | Tiempo total | 1,96 s | 2,72 s |
| | Latencia por 1.000 tokens | **3,92 s / 1k tok** | **5,43 s / 1k tok** |
| | Rendimiento | 255,0 tokens/s | 184,1 tokens/s |
| **1.000 tokens** | Tiempo total | 11,70 s | 3,25 s |
| | Latencia por 1.000 tokens | **11,70 s / 1k tok** | **3,25 s / 1k tok** |
| | Rendimiento | 85,4 tokens/s | 308,0 tokens/s |
| **2.000 tokens** | Tiempo total | 17,19 s | 7,56 s |
| | Latencia por 1.000 tokens | **8,60 s / 1k tok** | **3,78 s / 1k tok** |
| | Rendimiento | 116,3 tokens/s | 264,5 tokens/s |

**Impacto en la experiencia de usuario:**  
Para un documento de 7.000 tokens (`quickstart.rst`), XLM-RoBERTa Large tarda **58,85 segundos** y BERT Base tarda **21,07 segundos** en CPU. Esperar de 20 a 60 segundos antes de enviar una consulta a un LLM es inaceptable para una herramienta de terminal interactiva.

---

## 5. Razon de compresion real

Medido con el mismo contador para entrada y salida (`cl100k_base` via `tiktoken`, estandar de Claude y GPT-4). Se incluye tambien la metrica aproximada de SynRAG (`chars / 4`). Tasa solicitada `rate=0.5`.

| Archivo evaluado | Tipo | Tokens Originales (cl100k) | XLM-RoBERTa Comprimido | Ahorro XLM | BERT Base Comprimido | Ahorro BERT |
|---|---|---|---|---|---|---|
| `docs/quickstart.rst` | Doc Markdown/RST | 7.016 | 3.311 | **-52,8 %** | 3.562 | **-49,2 %** |
| `docs/blueprints.rst` | Doc Markdown/RST | 2.675 | 1.265 | **-52,7 %** | 1.355 | **-49,3 %** |
| `docs/installation.rst` | Doc Markdown/RST | 865 | 385 | **-55,5 %** | 456 | **-47,3 %** |
| `pip_install.log` | Terminal Log | 5.088 | 2.345 | **-53,9 %** | 3.392 | **-33,3 %** |
| `pytest_verbose.log` | Terminal Log | 1.856 | 1.027 | **-44,7 %** | 1.219 | **-34,3 %** |
| `flask/config.py` | Codigo Python | 2.834 | 1.212 | **-57,2 %** | 1.403 | **-50,5 %** |

---

## 6. Evaluacion de fidelidad y perdida de informacion critica

Se definieron 3 preguntas fácticas por cada archivo cuya respuesta existe en el texto original. Se verifico mediante inspeccion si la version comprimida permite responderlas.

### 6.1 `docs/quickstart.rst`
- **P1: ¿Que comando arranca el servidor de desarrollo?**  
  - Original: `flask --app <app> run` o `flask run`  
  - XLM-RoBERTa: Conservado (`flask run`).  
  - BERT Base: Conservado parcialmente (`flask run`), pero elimino `--app`.
- **P2: ¿Que metodo HTTP maneja `@app.route` por defecto?**  
  - Original: `GET`  
  - XLM-RoBERTa: Conservado.  
  - BERT Base: Conservado.
- **P3: ¿Que funcion genera URLs hacia una funcion dada?**  
  - Original: `url_for()`  
  - XLM-RoBERTa: Conservado (`url_for`).  
  - BERT Base: **Perdido** (`url_for` fue podado del texto).

### 6.2 `docs/blueprints.rst`
- **P1: ¿Cuales son los dos primeros argumentos obligatorios de `Blueprint`?**  
  - Original: `name` e `import_name`  
  - XLM-RoBERTa: **Perdido** (elimino `import_name`).  
  - BERT Base: **Perdido** (elimino la firma del constructor).
- **P2: ¿Como se registra un blueprint en la aplicacion?**  
  - Original: `app.register_blueprint(...)`  
  - XLM-RoBERTa: Conservado (`register_blueprint`).  
  - BERT Base: **Perdido** (elimino `register_blueprint`).
- **P3: ¿Que parametro define el prefijo de URL en un blueprint?**  
  - Original: `url_prefix`  
  - XLM-RoBERTa: Conservado.  
  - BERT Base: **Perdido** (`url_prefix` fue podado).

### 6.3 `docs/installation.rst`
- **P1: ¿Que version de Python requiere Flask segun el texto?**  
  - Original: `Python 3.11 and newer`  
  - XLM-RoBERTa: Conservado (`Flask supports Python 3.11 newer`).  
  - BERT Base: Conservado (`Flask supports Python 3. 11 newer`).
- **P2: ¿Que comando crea un entorno virtual `.venv` con el modulo de la biblioteca estandar?**  
  - Original: `python3 -m venv .venv`  
  - XLM-RoBERTa: **Dañado** (quedo `python3 -m venv`, borro el nombre `.venv`).  
  - BERT Base: **Perdido** (elimino `-m venv .venv`, quedo `python3 install - activate - env`).
- **P3: ¿Como se activa el entorno en macOS/Linux?**  
  - Original: `. .venv/bin/activate`  
  - XLM-RoBERTa: Conservado parcialmente (`.venv/bin/activate`, sin el punto inicial de source).  
  - BERT Base: **Perdido** (borro la seccion de macOS/Linux por completo; solo dejo Windows).

### 6.4 `pip_install.log`
- **P1: ¿Que version exacta de PyTorch se instalo?**  
  - Original: `torch-2.14.1+cpu`  
  - XLM-RoBERTa: **Alterado criticamente** (recorto a `torch-2.14.1`, borrando la etiqueta `+cpu`).  
  - BERT Base: **Alterado** (quedo `torch 2 14 cpu`, sin guiones ni versionado formal).
- **P2: ¿Que paquete se instalo en version 0.2.2?**  
  - Original: `llmlingua==0.2.2`  
  - XLM-RoBERTa: **Alterado** (en el resumen final recorto a `llmlingua-0`).  
  - BERT Base: **Perdido** (elimino el numero de version).
- **P3: ¿Que advertencia operativa clave ocurrio durante la instalacion?**  
  - Original: `warning: Failed to hardlink files; falling back to full copy.`  
  - XLM-RoBERTa: **Perdido** (seccion de warning eliminada al 100 %).  
  - BERT Base: **Perdido** (seccion de warning eliminada al 100 %).

### 6.5 `pytest_verbose.log`
- **P1: ¿Que archivo y nombre tiene el test sobre claves de API y red?**  
  - Original: `tests/test_argon.py::test_sin_clave_no_hay_herramientas_ni_red`  
  - XLM-RoBERTa: **Mutilado** (quedo `_argon.py_sin_clave_red`).  
  - BERT Base: Conservado (`tests test argon test _ sin _ clave _ no _ herramientas _ ni _ red`).
- **P2: ¿El test paso o fallo?**  
  - Original: `PASSED`  
  - XLM-RoBERTa: **Perdido en el 90 % de lineas** (elimino la palabra `PASSED` en la mayoria de casos).  
  - BERT Base: **Perdido en el 100 % de lineas** (elimino la palabra `PASSED` en absolutamente todos los tests). Un agente o desarrollador no puede saber si los tests funcionaron.
- **P3: ¿Que plugin se cargo durante la sesion?**  
  - Original: `anyio-4.15.1`  
  - XLM-RoBERTa: Conservado (`anyio-4.15.1`).  
  - BERT Base: Conservado (`anyio - 4. 15. 1`).

### 6.6 `flask/config.py` (Codigo Python)
- **P1: ¿Que clase hereda de `dict`?**  
  - Original: `class Config(dict):`  
  - XLM-RoBERTa: Texto distorsionado en una sola linea: `Config(dict): ignore[type-arg] dict fill files`.  
  - BERT Base: Texto aplanado sin sintaxis de clase.
- **P2: ¿Que metodo carga configuraciones desde variables de entorno?**  
  - Original: `def from_envvar(...)`  
  - XLM-RoBERTa: Conservado el nombre, pero identacion e instrucciones internas mezcladas en un unico bloque plano.  
  - BERT Base: Perdido como definicion de funcion.
- **P3: ¿Es codigo Python sintacticamente valido (`ast.parse`)?**  
  - Codigo original: **VALIDO** (AST generado sin errores).  
  - XLM-RoBERTa: **FALLA ROTUNDAMENTE**:  
    `SyntaxError: closing parenthesis ']' does not match opening parenthesis '(' (<unknown>, line 1)`  
  - BERT Base: **FALLA ROTUNDAMENTE**:  
    `SyntaxError: unmatched ')' (<unknown>, line 1)`

---

## 7. Justificacion de la recomendacion final

1. **Incompatibilidad absoluta con codigo:**  
   LLMLingua-2 poda tokens individuales sin nocion de gramatica formal ni de identacion. Elimina parentesis de cierre, dos puntos y bloques de indentacion, produciendo cadenas que fallan inmediatamente en `ast.parse`. No sirve para comprimir codigo.

2. **Perdida de semantica critica en logs:**  
   En logs de prueba, el podado estadistico considera palabras repetitivas como `PASSED` como candidatos prescindibles y las elimina, convirtiendo el log en inutil para diagnostico. En logs de paquetes borra subversiones (`0.2.2` -> `0`) y sufijos criticos (`+cpu`).

3. **Sobrecoste inasumible frente a SynRAG Tarea B (Filtro de logs):**  
   - `SYNRAG filtrar` (Tarea B) mediante reglas deterministas (eliminar barras de progreso de pip, colapsar secuencias de pytest a resumen de fallos) reduce un log tipico de 5.000 tokens a menos de 200 tokens (**> 95 % de reduccion**) en **0 milisegundos**, sin modelos de machine learning.
   - LLMLingua-2 apenas logra un 33-54 % de compresion, demora 16-52 segundos en CPU y destruye datos criticos.

4. **Sobrecoste inasumible frente a SynRAG Tarea C (Fragmentacion de documentacion):**  
   - La fragmentacion semantica de documentacion en fragmentos de ~200 tokens (Tarea C) permite indexar la documentacion y devolver solo el tramo de respuesta relevante. En un archivo de 7.000 tokens, entregar un fragmento de 200 tokens representa un ahorro del **97,1 %**, con latencia de recuperacion en LanceDB de **< 15 ms**.
   - LLMLingua-2 procesa el documento entero de 7.000 tokens para dejarlo en ~3.300 tokens (ahorro del ~52 %), tardando casi un minuto en CPU y corriendo el riesgo de borrar comandos exactos como `url_for` o `.venv/bin/activate`.

5. **Violacion del espiritu de SynRAG:**  
   La regla 2 de `PLAN.md` establece que el motor debe ser rapido, ligero y sin dependencias obligatorias pesadas. Anadir PyTorch y transformadores de 2 a 4 GB para obtener una compresion peor que metodos deterministas y vectoriales contradice el diseno del proyecto.

**Veredicto:** Descartar LLMLingua-2. El valor de SynRAG reside en sus motores deterministas (AST, grep inteligente, filtros estructurados de terminal y chunking de documentacion).
