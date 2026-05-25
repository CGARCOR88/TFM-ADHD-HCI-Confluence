
# -*- coding: utf-8 -*-
"""
Step 02 — GWAS Query
Consulta el GWAS Catalog (EBI) para los fenotipos de interés (TDAH/ACI).
Estrategia:
  1. Descarga TODAS las asociaciones para cada EFO term (EFO_TDAH + EFO_ACI)
     mediante el endpoint /efoTraits/{shortForm}/associations  — pocas llamadas.
  2. Filtra las asociaciones donde alguno de nuestros genes candidatos aparezca
     en loci.authorReportedGenes.
  3. Usa caché en disco para evitar repetir las llamadas.
Genera: data/output/resultados_gwas.xlsx
"""

import json
import logging
import time

import pandas as pd
import requests
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_exponential,
)

from config.settings import (
    RESULTADOS_1, RESULTADOS_GWAS,
    GWAS_BASE, GWAS_HEADERS, GWAS_TIMEOUT, GWAS_SLEEP, GWAS_MAX_PAGES,
    EFO_TDAH, EFO_ACI,
    BASE_DIR,
)

logger = logging.getLogger(__name__)

# ── Caché en disco ────────────────────────────────────────────────────────────
CACHE_DIR   = BASE_DIR / "data" / "cache"
CACHE_GWAS  = CACHE_DIR / "gwas_cache.json"


def _load_cache(path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(path, data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── HTTP con reintentos ───────────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    reraise=True,
)
def _get_json(url, params=None):
    r = requests.get(url, params=params, headers=GWAS_HEADERS, timeout=GWAS_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _fetch_safe(url, params=None):
    try:
        return _get_json(url, params=params)
    except Exception as exc:
        logger.warning("Petición GWAS fallida (%s): %s", url, exc)
        return None


# ========================================================================
# -----------> FUN 1 : LECTURA DE LA HOJA "MAESTRA" (símbolo + fenotipo) <-
# ========================================================================

def cargar_genes(path):
    """Devuelve un DataFrame con columnas [Gen, Fenotipo, Ensembl] únicos por símbolo."""
    df = pd.read_excel(path, sheet_name="Maestra")
    df.columns = [c.strip().lower() for c in df.columns]
    if "gen" not in df.columns:
        raise ValueError("No se encontró la columna 'Gen' en la hoja 'Maestra'.")
    df = df[["gen", "fenotipo", "ensembl"]].dropna(subset=["gen"]).copy()
    df["gen"] = df["gen"].astype(str).str.strip()
    # Un mismo símbolo puede aparecer para TDAH y ACI — mantenemos ambas filas
    return df.drop_duplicates(subset=["gen", "fenotipo"]).reset_index(drop=True)

# ========================================================================
# -----------------> FUN 2 : DESCARGA POR EFO TERM <---------------------
# ========================================================================

def _fetch_efo_associations(short_form: str) -> list:
    """Descarga todas las asociaciones GWAS para un EFO shortform (paginado)."""
    url = f"{GWAS_BASE}/efoTraits/{short_form}/associations"
    all_items, page = [], 0

    while page < GWAS_MAX_PAGES:
        data = _fetch_safe(url, params={"size": 500, "page": page})
        if not data:
            break
        items = (data.get("_embedded") or {}).get("associations", [])
        if not items:
            break
        all_items.extend(items)
        total = (data.get("page") or {}).get("totalPages", 0)
        page += 1
        if page >= total:
            break
        time.sleep(GWAS_SLEEP)

    logger.debug("  EFO %s: %d asociaciones descargadas", short_form, len(all_items))
    return all_items


def _build_gene_map(genes_df, cache: dict) -> dict:
    """Descarga asociaciones para EFO_TDAH ∪ EFO_ACI y construye
    un mapa {gen_symbol → lista_de_filas}.
    """
    gene_info = {
        row["gen"]: {"ensembl": row.get("ensembl"), "fenotipo": row.get("fenotipo")}
        for _, row in genes_df.iterrows()
    }
    genes_set = set(gene_info.keys())
    gene_map: dict = {}

    for short_form in sorted(EFO_TDAH | EFO_ACI):
        cache_key = f"_efo_{short_form}"
        if cache_key in cache:
            raw = cache[cache_key]
            logger.info("  EFO %s: desde caché (%d asoc.)", short_form, len(raw))
        else:
            logger.info("  EFO %s: consultando API…", short_form)
            raw = _fetch_efo_associations(short_form)
            cache[cache_key] = raw
            _save_cache(CACHE_GWAS, cache)

        fenotipo_label = "TDAH" if short_form in EFO_TDAH else "ACI"

        for a in raw:
            # Genes reportados por los autores en cada locus
            gene_names = {
                g.get("geneName", "").strip()
                for locus in a.get("loci", [])
                for g in locus.get("authorReportedGenes", [])
                if g.get("geneName") and g["geneName"].strip() not in ("NR", "")
            }
            matched = gene_names & genes_set
            if not matched:
                continue

            # Extraer rsIDs desde strongestRiskAlleles (formato "rsXXX-A")
            rsids = [
                sra.get("riskAlleleName", "").split("-")[0]
                for locus in a.get("loci", [])
                for sra in locus.get("strongestRiskAlleles", [])
                if sra.get("riskAlleleName", "").startswith("rs")
            ]
            efolist  = a.get("efoTraits") or []
            efos     = [e.get("shortForm") for e in efolist if e.get("shortForm")]
            trait    = a.get("trait")
            if not trait and efolist:
                trait = efolist[0].get("trait")
            efo_str  = ";".join(sorted(set(efos))) if efos else short_form
            rsid_str = ";".join(sorted({r for r in rsids if r})) if rsids else None
            pval     = a.get("pvalue")
            if pval is None and a.get("pvalueMantissa") is not None:
                pval = a["pvalueMantissa"] * 10 ** a["pvalueExponent"]

            for gen in matched:
                info = gene_info.get(gen, {})
                gene_map.setdefault(gen, []).append({
                    "Gen":      gen,
                    "Ensembl":  info.get("ensembl"),
                    "Fenotipo": info.get("fenotipo") or fenotipo_label,
                    "GCST":     a.get("studyAccession"),
                    "PMID":     a.get("pubmedId"),
                    "Trait":    trait,
                    "EFO":      efo_str,
                    "RSID":     rsid_str,
                    "PValue":   pval,
                })

    return gene_map


# ========================================================================
# -----------------> FUN 3 : CONSULTA POR SÍMBOLO (lookup) <-------------
# ========================================================================

def gwas_por_simbolo(symbol, gene_map: dict) -> list:
    """Devuelve las filas GWAS para un símbolo dado (desde gene_map pre-calculado)."""
    return gene_map.get(symbol, [])


# ========================================================================
# ------------------ LLAMADO DE LAS FUNCIONES ----------------------------
# ========================================================================

def main():
    logger.info("[1/3] Leyendo genes desde %s", RESULTADOS_1)
    genes_df = cargar_genes(RESULTADOS_1)
    logger.info("   Símbolos únicos: %d", genes_df["gen"].nunique())

    cache = _load_cache(CACHE_GWAS)

    logger.info("[2/3] Descargando asociaciones GWAS por EFO term (TDAH+ACI)…")
    gene_map = _build_gene_map(genes_df, cache)
    n_con_datos = sum(1 for v in gene_map.values() if v)
    logger.info("   Genes con ≥1 asociación: %d / %d", n_con_datos, genes_df["gen"].nunique())

    logger.info("[3/3] Compilando resultados…")
    out = []
    for sym in genes_df["gen"].unique():
        filas = gwas_por_simbolo(sym, gene_map)
        if filas:
            logger.info("  [%s] %d asociaciones", sym, len(filas))
        out.extend(filas)

    cols = ["Gen", "Ensembl", "Fenotipo", "GCST", "PMID", "Trait", "EFO", "RSID", "PValue"]
    res = pd.DataFrame(out, columns=cols).drop_duplicates()
    RESULTADOS_GWAS.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(RESULTADOS_GWAS, engine="openpyxl", mode="w") as xls:
        res.to_excel(xls, sheet_name="resultados_gwas", index=False)
    logger.info("Paso 2 completado. %s (%d filas)", RESULTADOS_GWAS, len(res))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(message)s",
    )
    main()

