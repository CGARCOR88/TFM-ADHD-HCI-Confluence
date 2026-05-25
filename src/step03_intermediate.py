# -*- coding: utf-8 -*-
"""
Step 03 — Intermediate Builder
Lee los resultados de los pasos 1 y 2 y genera tablas normalizadas
listas para cargar en MySQL.
Genera: data/output/intermedio_bd.xlsx
"""

import logging

import pandas as pd

from config.settings import RESULTADOS_1, RESULTADOS_GWAS, INTERMEDIO_BD

logger = logging.getLogger(__name__)

# ========================================================================
# --------------> FUN 1 : LECTURA DEL ARCHIVO: RESULTADOS 1 <-------------
# ========================================================================

def leer_cod1_maestra_y_reactome(ruta):
    try:
        maestra_df  = pd.read_excel(ruta, sheet_name="Maestra")
        reactome_df = pd.read_excel(ruta, sheet_name="Reactome")
    except Exception as e:
        logger.error("No se pudieron leer hojas de %s: %s", ruta, e)
        return None, None
    maestra_df.columns  = [c.strip().lower() for c in maestra_df.columns]
    reactome_df.columns = [c.strip().lower() for c in reactome_df.columns]
    return maestra_df, reactome_df

# ========================================================================
# -------------> FUN 2 : LECTURA DEL ARCHIVO RESULTADOS GWAS <------------
# ========================================================================

def leer_cod2_gwas(ruta):
    try:
        gwas_df = pd.read_excel(ruta, sheet_name="resultados_gwas")
    except Exception as e:
        logger.error("No se pudo leer hoja 'resultados_gwas' de %s: %s", ruta, e)
        return None
    gwas_df.columns = [c.strip().lower() for c in gwas_df.columns]
    return gwas_df

# ========================================================================
# --------------------> FUN 3 : INCLUSION DE FENOTIPOS <------------------
# ========================================================================

def derivar_fenotipos(maestra_df: pd.DataFrame):
    if maestra_df is None or "fenotipo" not in maestra_df.columns:
        return pd.DataFrame(columns=["id", "trait"])

    fenotipos_unicos = sorted(set(maestra_df["fenotipo"].dropna().unique()))
    fenotipos_tbl = pd.DataFrame({
        "id": range(1, len(fenotipos_unicos) + 1),
        "trait": fenotipos_unicos
    })
    return fenotipos_tbl

# ========================================================================
# ---------------------> FUN 4 : CONTRUCCION TABLAS <---------------------
# ========================================================================

def construir_tablas_intermedias(maestra_df, reactome_df, gwas_df):
    if maestra_df is None:
        return None, None, None, None, None, None

    # ---- Hoja genes ----
    genes_tbl = pd.DataFrame({
        "id": range(1, len(maestra_df) + 1),
        "nombre": maestra_df.get("genename"),
        "gen": maestra_df.get("symbol_input"),
        "simbolo": maestra_df.get("gen"),
        "localizacion_cromosomica": maestra_df.get("localizacion_cromosomica"),
        "entrez_id": maestra_df.get("entrez"),
        "ensembl_id": maestra_df.get("ensembl"),
        "uniprot_id": maestra_df.get("uniprot")
    })

    # ---- Hoja pathways (BUG FIX: incluir reactome_id) ----
    if reactome_df is not None and "reactome_id" in reactome_df.columns:
        pathways_unicos = (
            reactome_df[["reactome_id", "reactome_name"]]
            .drop_duplicates(subset=["reactome_id"])
            .dropna(subset=["reactome_id"])
            .reset_index(drop=True)
        )
        pathways_tbl = pd.DataFrame({
            "id":          range(1, len(pathways_unicos) + 1),
            "nombre":      pathways_unicos["reactome_name"].values,
            "reactome_id": pathways_unicos["reactome_id"].values,
        })
    else:
        pathways_tbl = pd.DataFrame(columns=["id", "nombre", "reactome_id"])

    # ---- Hoja fenotipos ----
    fenotipos_tbl = derivar_fenotipos(maestra_df)

    # ---- Hoja artículos ----
    if gwas_df is not None:
        articulos_unicos = gwas_df.drop_duplicates(subset=["pmid"])
        articulos_tbl = pd.DataFrame({
            "pmid": articulos_unicos["pmid"],
            "doi": pd.NA,
            "titulo": pd.NA,
            "anio": pd.NA
        })
    else:
        articulos_tbl = pd.DataFrame(columns=["pmid", "doi", "titulo", "anio"])

    # ---- Hoja variantes ----
    if gwas_df is not None:
        variantes_tbl = gwas_df.drop_duplicates(subset=["rsid"])[["rsid", "pvalue"]]
    else:
        variantes_tbl = pd.DataFrame(columns=["rsid", "pvalue"])

    # ---- Hoja asociaciones ----
    if gwas_df is not None and len(gwas_df) > 0:
        rows = []
        for _, row in gwas_df.iterrows():
            gen_sym  = str(row.get("gen", "")).strip()
            fenotipo = str(row.get("fenotipo", "")).strip()
            if not gen_sym or not fenotipo:
                continue
            rows.append({
                "simbolo":       gen_sym,
                "trait":         fenotipo,
                "via_nombre":    None,
                "reactome_id":   None,
                "pmid":          row.get("pmid"),
                "rsid":          row.get("rsid"),
                "pvalue":        row.get("pvalue"),
            })
        asociaciones_tbl = pd.DataFrame(rows)
    else:
        asociaciones_tbl = pd.DataFrame(columns=["simbolo", "trait", "via_nombre", "reactome_id", "pmid", "rsid", "pvalue"])

    logger.info(
        "Tablas construidas — genes:%d  pathways:%d  fenotipos:%d  articulos:%d  variantes:%d",
        len(genes_tbl), len(pathways_tbl), len(fenotipos_tbl),
        len(articulos_tbl), len(variantes_tbl),
    )
    return genes_tbl, pathways_tbl, fenotipos_tbl, articulos_tbl, variantes_tbl, asociaciones_tbl


    # **********************************************************
    # *********** PROCESAMIENTO DE DATOS Y EXPORTACIÓN *********
    # **********************************************************
    
def main():
    logger.info("[1/3] Leyendo datos de entrada…")
    maestra_df, reactome_df = leer_cod1_maestra_y_reactome(RESULTADOS_1)
    gwas_df = leer_cod2_gwas(RESULTADOS_GWAS)

    logger.info("[2/3] Construyendo tablas intermedias…")
    genes_tbl, pathways_tbl, fenotipos_tbl, articulos_tbl, variantes_tbl, asociaciones_tbl = (
        construir_tablas_intermedias(maestra_df, reactome_df, gwas_df)
    )

    logger.info("[3/3] Exportando a Excel: %s", INTERMEDIO_BD)
    INTERMEDIO_BD.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(INTERMEDIO_BD) as writer:
        genes_tbl.to_excel(writer,        sheet_name="genes",        index=False)
        pathways_tbl.to_excel(writer,     sheet_name="vias",         index=False)
        fenotipos_tbl.to_excel(writer,    sheet_name="fenotipos",    index=False)
        articulos_tbl.to_excel(writer,    sheet_name="articulos",    index=False)
        variantes_tbl.to_excel(writer,    sheet_name="variantes",    index=False)
        asociaciones_tbl.to_excel(writer, sheet_name="asociaciones", index=False)
    logger.info("Paso 3 completado: %s", INTERMEDIO_BD)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(message)s",
    )
    main()
