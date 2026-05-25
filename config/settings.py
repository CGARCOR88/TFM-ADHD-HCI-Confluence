# -*- coding: utf-8 -*-
"""
config/settings.py
==================
Configuración centralizada del proyecto TFM-GENES.
Las credenciales se cargan desde el archivo .env (nunca hardcodeadas aquí).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Directorios base ──────────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_IN    = BASE_DIR / "data" / "input"
DATA_OUT   = BASE_DIR / "data" / "output"
LOGS_DIR   = BASE_DIR / "logs"

# Carga variables de entorno desde .env (si existe)
load_dotenv(BASE_DIR / ".env")

# ── Archivos de datos ─────────────────────────────────────────────────────────

GENES_XLSX       = DATA_IN  / "genes.xlsx"
RESULTADOS_1     = DATA_OUT / "resultados_1.xlsx"
RESULTADOS_GWAS  = DATA_OUT / "resultados_gwas.xlsx"
INTERMEDIO_BD    = DATA_OUT / "intermedio_bd.xlsx"

# ── Base de datos MySQL ───────────────────────────────────────────────────────

DB_NAME = os.getenv("DB_NAME", "genes_2e")

DB_CFG = {
    "host":       os.getenv("DB_HOST", "localhost"),
    "port":       int(os.getenv("DB_PORT", "3306")),
    "user":       os.getenv("DB_USER", "root"),
    "password":   os.getenv("DB_PASSWORD", ""),
    "database":   DB_NAME,
    "autocommit": False,
    "charset":    "utf8mb4",
}

# ── API: MyGene.info ──────────────────────────────────────────────────────────

MYGENE_URL    = "https://mygene.info/v3/query"
USER_AGENT    = "TFM-genes2e"
HEADERS       = {"User-Agent": USER_AGENT, "Accept": "application/json"}
API_TIMEOUT   = 25      # segundos
API_SLEEP     = 0.12    # pausa entre peticiones (rate limit)

# ── API: Reactome ─────────────────────────────────────────────────────────────

REACTOME_URL  = "https://reactome.org/ContentService/data/mapping/UniProt/{uniprot_id}/pathways"

# ── API: GWAS Catalog (EBI) ───────────────────────────────────────────────────

GWAS_BASE     = "https://www.ebi.ac.uk/gwas/rest/api"
GWAS_HEADERS  = {"Accept": "application/json", "User-Agent": "TFM-GWAS/1.0"}
GWAS_TIMEOUT  = 25
GWAS_SLEEP    = 0.08
GWAS_MAX_PAGES = 20

# ── Filtros GWAS por fenotipo ─────────────────────────────────────────────────

USE_FILTER = True

EFO_TDAH = {"MONDO_0007743"}          # attention deficit-hyperactivity disorder (2387 assoc)
KW_TDAH  = ("adhd", "attention deficit", "attention-deficit")

EFO_ACI = {
    "EFO_0004337",   # intelligence (4288 assoc)
    "EFO_0004784",   # self reported educational attainment (4696 assoc, proxy cognitivo)
    "EFO_0008354",   # cognitive function measurement (5124 assoc, umbrella)
}
KW_ACI = (
    "intelligence", "cognitive", "cognition",
    "iq", "general cognitive", "cognitive performance",
)
