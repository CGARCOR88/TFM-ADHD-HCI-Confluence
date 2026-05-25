# -*- coding: utf-8 -*-
"""
tests/test_pipeline.py
Pruebas básicas de los módulos del pipeline.
Ejecutar con: pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Smoke tests de importación ────────────────────────────────────────────────

def test_import_settings():
    from config import settings
    assert hasattr(settings, "DB_CFG")
    assert hasattr(settings, "GENES_XLSX")


def test_import_step01():
    from src import step01_gene_mapping
    assert callable(getattr(step01_gene_mapping, "main", None))


def test_import_step02():
    from src import step02_gwas_query
    assert callable(getattr(step02_gwas_query, "main", None))


def test_import_step03():
    from src import step03_intermediate
    assert callable(getattr(step03_intermediate, "exportar_excel_intermedio", None))


def test_import_step05():
    from src import step05_load_data
    assert callable(getattr(step05_load_data, "main", None))


# ── Tests unitarios de funciones auxiliares ───────────────────────────────────

def test_to_none_nan():
    """to_none() debe convertir NaN y cadenas vacías a None."""
    import math
    from src.step05_load_data import to_none
    assert to_none(float("nan")) is None
    assert to_none("") is None
    assert to_none("  ") is None
    assert to_none(None) is None
    assert to_none("BRCA1") == "BRCA1"
    assert to_none(12345) == 12345


def test_gwas_filter_keywords():
    """es_interes() debe devolver True para palabras clave de TDAH/ACI."""
    from src.step02_gwas_query import es_interes
    assert es_interes("attention deficit hyperactivity disorder", None) is True
    assert es_interes("general cognitive ability", None) is True
    assert es_interes("blood pressure", None) is False
