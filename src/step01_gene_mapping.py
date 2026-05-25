# -*- coding: utf-8 -*-
"""
Step 01 — Gene Mapping
Consulta MyGene.info y Reactome para cada gen del Excel de entrada.
Genera: data/output/resultados_1.xlsx  (hojas: Mapping_IDs, Reactome, Maestra)
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
    GENES_XLSX, RESULTADOS_1,
    HEADERS, API_TIMEOUT, API_SLEEP,
    MYGENE_URL, REACTOME_URL,
    BASE_DIR,
)

logger = logging.getLogger(__name__)

# ── Caché en disco ────────────────────────────────────────────────────────────
CACHE_DIR      = BASE_DIR / "data" / "cache"
CACHE_MYGENE   = CACHE_DIR / "mygene_cache.json"
CACHE_REACTOME = CACHE_DIR / "reactome_cache.json"


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
    r = requests.get(url, params=params, headers=HEADERS, timeout=API_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _fetch_safe(url, params=None):
    """Llama a _get_json con reintentos; devuelve None si falla definitivamente."""
    try:
        return _get_json(url, params=params)
    except Exception as exc:
        logger.warning("Petición fallida (%s): %s", url, exc)
        return None

# ================================================================
# -----------------> FUN 1 : LECTURA DE LA HOJA <-----------------
# ================================================================

def leer_genes(path):
    def leer_hoja(hoja, etiqueta):
        df = pd.read_excel(path, sheet_name=hoja)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "gen" not in df.columns:
            raise ValueError(f"La hoja '{hoja}' no tiene columna 'gen'. Columnas: {list(df.columns)}")
        mask = df["gen"].notna() & (df["gen"].astype(str).str.strip() != "")
        serie_gen = df.loc[mask, "gen"].astype(str).reset_index(drop=True)
        if "localizacion_cromosomica" in df.columns:
            serie_loc = df.loc[mask, "localizacion_cromosomica"].reset_index(drop=True)
        else:
            serie_loc = pd.Series([None] * len(serie_gen))
        return pd.DataFrame({"Symbol": serie_gen.values,
                             "Fenotipo": etiqueta,
                             "localizacion_cromosomica": serie_loc.values})
    df_tdah = leer_hoja("TDAH", "TDAH")
    df_aci  = leer_hoja("ACI",  "ACI")
    df = pd.concat([df_tdah, df_aci], ignore_index=True)
    return df  

# ================================================================
# -----------------> FUN 2: MAPEO CON MyGene.info <---------------
# ================================================================

def mapear_mygene(symbols):
    cache = _load_cache(CACHE_MYGENE)
    filas = []
    nuevos = 0

    for s in symbols:
        if s in cache:
            filas.append(cache[s])
            continue

        params = {
            "q": s,
            "scopes": "symbol,alias",
            "species": "9606",
            "fields": "symbol,name,entrezgene,ensembl.gene,uniprot.Swiss-Prot",
            "size": 5,
        }
        data = _fetch_safe(MYGENE_URL, params=params)
        time.sleep(API_SLEEP)

        sym    = s
        entrez = ensembl = uniprot = name = None
        if data and data.get("hits"):
            hit = data["hits"][0]
            sym    = str(hit.get("symbol", sym))
            entrez = hit.get("entrezgene")
            ens    = hit.get("ensembl", {})
            if isinstance(ens, dict):
                ensembl = ens.get("gene")
            elif isinstance(ens, list) and ens:
                ensembl = ens[0].get("gene")
            uni     = hit.get("uniprot", {}).get("Swiss-Prot")
            uniprot = (
                uni[0] if isinstance(uni, list) and uni
                else (uni if isinstance(uni, str) else None)
            )
            name = hit.get("name")

        row = {"symbol": sym, "entrez": entrez, "ensembl": ensembl,
               "uniprot": uniprot, "name": name}
        cache[s] = row
        nuevos += 1
        if nuevos % 10 == 0:
            _save_cache(CACHE_MYGENE, cache)
        filas.append(row)

    _save_cache(CACHE_MYGENE, cache)
    logger.info("MyGene.info: %d genes (%d nuevos, %d desde caché)",
                len(filas), nuevos, len(filas) - nuevos)
    return pd.DataFrame(filas).reset_index(drop=True)

# ================================================================
# -----------------> FUN 3: REACTOME (pathways) <-----------------
# ================================================================

def reactome_por_uniprot(uniprot_id):
    cache = _load_cache(CACHE_REACTOME)
    if uniprot_id in cache:
        return cache[uniprot_id]

    url  = REACTOME_URL.format(uniprot_id=uniprot_id)
    data = _fetch_safe(url)
    time.sleep(API_SLEEP)

    rutas = []
    if data:
        for p in data:
            rutas.append({
                "Reactome_ID":   p.get("stId"),
                "Reactome_Name": p.get("displayName"),
                "Species":       p.get("speciesName"),
            })

    cache[uniprot_id] = rutas
    _save_cache(CACHE_REACTOME, cache)
    return rutas

# **********************************************************
# ****************** LLAMADO DE FUNCIONES ******************
# **********************************************************

def main():
    logger.info("[1/3] Leyendo genes desde %s", GENES_XLSX)
    genes_df = leer_genes(GENES_XLSX)
    logger.info("   Total de filas leídas: %d", len(genes_df))

    logger.info("[2/3] Mapeando con MyGene.info…")
    mapping = mapear_mygene(genes_df["Symbol"].tolist())
    mapping.insert(0, "Fenotipo",               genes_df["Fenotipo"].values)
    mapping.insert(1, "Symbol_input",            genes_df["Symbol"].values)
    mapping.insert(2, "localizacion_cromosomica", genes_df["localizacion_cromosomica"].values)
    n_uni = int(mapping["uniprot"].notna().sum())
    logger.info("   Filas con UniProt: %d / %d", n_uni, len(mapping))

    logger.info("[3/3] Consultando Reactome…")
    r_rows = []
    for _, row in mapping.iterrows():
        fen, sym, uni = row["Fenotipo"], row["symbol"], row["uniprot"]
        if not uni:
            continue
        for ruta in reactome_por_uniprot(uni):
            r_rows.append({"Fenotipo": fen, "Symbol": sym, "UniProt": uni, **ruta})
    reactome_df = pd.DataFrame(
        r_rows, columns=["Fenotipo", "Symbol", "UniProt", "Reactome_ID", "Reactome_Name", "Species"]
    )
    if not reactome_df.empty:
        reactome_df = reactome_df.reset_index(drop=True)

    if not reactome_df.empty:
        by_paths = reactome_df.groupby("Symbol")["Reactome_Name"].apply(
            lambda s: "; ".join(sorted(set(s)))
        )
    else:
        by_paths = pd.Series(dtype="object")

    master = mapping.copy()
    master.rename(columns={
        "symbol": "Gen", "entrez": "Entrez", "ensembl": "Ensembl",
        "uniprot": "UniProt", "name": "GeneName",
    }, inplace=True)
    master = master.join(by_paths.rename("Reactome_Pathways"), how="left", on="Gen")

    RESULTADOS_1.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Guardando resultados en: %s", RESULTADOS_1)
    with pd.ExcelWriter(RESULTADOS_1) as xls:
        mapping.to_excel(xls, sheet_name="Mapping_IDs", index=False)
        if not reactome_df.empty:
            reactome_df.to_excel(xls, sheet_name="Reactome", index=False)
        master.to_excel(xls, sheet_name="Maestra", index=False)
    logger.info("Paso 1 completado.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(message)s",
    )
    main()

