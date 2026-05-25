# TFM-GENES

Pipeline bioinformático para el análisis de genes asociados a **TDAH** (Trastorno por Déficit de Atención e Hiperactividad) y **ACI** (Altas Capacidades Intelectuales / Rendimiento Cognitivo).

El proyecto integra datos de múltiples fuentes de acceso público (MyGene.info, Reactome, GWAS Catalog) en una base de datos relacional MySQL, permitiendo el análisis automatizado de vías moleculares compartidas entre ambos fenotipos.

---

## 📁 Estructura del proyecto

```
TFM-GENES/
├── main.py                    # Punto de entrada: ejecuta el pipeline completo
├── README.md                  # Este archivo
├── requirements.txt           # Dependencias de Python
├── .env.example               # Plantilla para variables de entorno (BD)
├── .gitignore                 # Archivos excluidos del control de versiones
│
├── config/
│   └── settings.py            # Rutas, lectura de entorno y parámetros globales
│
├── src/                       # Módulos del pipeline (en orden de ejecución)
│   ├── step01_gene_mapping.py # Mapeo de genes → MyGene.info + Reactome
│   ├── step02_gwas_query.py   # Consultas al GWAS Catalog (EBI)
│   ├── step03_intermediate.py # Integración y normalización de datos
│   ├── step04_create_db.py    # Creación de la BD MySQL
│   ├── step05_load_data.py    # Carga de datos en MySQL
│   └── step06_queries.py      # Consultas analíticas SQL
│
├── data/
│   ├── input/                 # Archivos de entrada (debe contener genes.xlsx)
│   └── output/                # Archivos Excel generados por el pipeline
│
├── logs/                      # Registro de eventos y errores de ejecución
├── sql/
│   └── queries.sql            # Consultas de análisis reutilizables
├── docs/                      # Documentación técnica adicional
└── tests/
    └── test_pipeline.py       # Tests unitarios de validación
```

---

## ⚙️ Pipeline de ejecución

```
genes.xlsx  (data/input/)
    │
    ▼
[STEP 1] Gene Mapping          → resultados_1.xlsx     (MyGene.info + Reactome)
    │
    ▼
[STEP 2] GWAS Query            → resultados_gwas.xlsx  (GWAS Catalog / EBI)
    │
    ▼
[STEP 3] Intermediate Builder  → intermedio_bd.xlsx    (tablas normalizadas)
    │
    ▼
[STEP 4] Create Database       → genes_2e (esquema MySQL)
    │
    ▼
[STEP 5] Load Data             → INSERT / UPSERT transaccional en MySQL
    │
    ▼
[STEP 6] Queries               → Análisis de vías compartidas TDAH ↔ ACI
```

---

## 🚀 Requisitos previos e instalación

### 1. Requisitos del sistema

- Python **3.9** o superior
- MySQL Server **8.0** o superior corriendo en el puerto por defecto (`3306`)

### 2. Clonar e instalar dependencias

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/TFM-GENES.git
cd TFM-GENES

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración de credenciales

Las credenciales de la base de datos **no están hardcodeadas** en el código; se cargan desde un archivo `.env` local:

```bash
cp .env.example .env
```

Edita `.env` con los datos de tu servidor MySQL:

```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_contraseña_aqui
DB_NAME=genes_2e
```

### 4. Archivo de entrada

Coloca el archivo `genes.xlsx` en `data/input/`. Debe contener dos hojas:

| Hoja | Columna obligatoria |
|------|---------------------|
| `TDAH` | `gen` (símbolo del gen) |
| `ACI` | `gen` (símbolo del gen) |

---

## ▶️ Modo de uso

### Ejecución completa (end-to-end)

```bash
python main.py
```

### Ejecución por paso individual

```bash
python main.py --step 1   # Mapeo de identificadores + Reactome
python main.py --step 2   # Extracción de variantes GWAS
python main.py --step 3   # Construcción del archivo intermedio
python main.py --step 4   # Inicialización del esquema MySQL
python main.py --step 5   # Inserción relacional con control de duplicados
```

### Reanudar desde un paso concreto

```bash
python main.py --from 3   # Ejecuta desde el paso 3 hasta el final
```

> **Caché de APIs**: los pasos 1 y 2 guardan automáticamente las respuestas en `data/cache/`.  
> Si el proceso se interrumpe, al relanzarlo los genes ya consultados se recuperan del caché sin hacer nuevas peticiones.

---

## 🔬 Fuentes de datos

| Fuente | URL | Uso |
|--------|-----|-----|
| MyGene.info | <https://mygene.info> | Mapeo símbolo → Entrez / Ensembl / UniProt |
| Reactome | <https://reactome.org> | Vías moleculares por UniProt |
| GWAS Catalog (EBI) | <https://www.ebi.ac.uk/gwas> | Asociaciones genéticas GWAS |

---

## 🗄️ Esquema de la base de datos `genes_2e`

```
genes ──────┐
            │
fenotipos ──┼──► asociaciones ◄──── variantes
            │
vias ───────┘        │
                     └──► articulos
```

| Tabla | Descripción |
|-------|-------------|
| `genes` | Genes evaluados con sus identificadores moleculares (Entrez, Ensembl, UniProt) |
| `fenotipos` | Rasgos bajo estudio (TDAH / ACI) con identificadores EFO |
| `vias` | Vías biológicas curadas extraídas de Reactome |
| `articulos` | Publicaciones GWAS indexadas (clave primaria: PMID) |
| `variantes` | Variantes genéticas (rsID) con p-valor asociado |
| `asociaciones` | Tabla puente: Gen ↔ Fenotipo ↔ Vía ↔ Variante ↔ Artículo |

---

## 🧪 Tests

```bash
pytest tests/
```

---

## 👤 Autor

**Carlos García Corona**  
TFM — Máster en Bioinformática / Biomedicina  
2026

