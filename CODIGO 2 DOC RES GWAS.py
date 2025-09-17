
# -*- coding: utf-8 -*-

import time
import requests
import pandas as pd
import os

# === RUTAS DE ARCHIVOS ==========================================
RUTA_ENTRADA = r"C:\Users\Usuario\Desktop\resultados_1.xlsx"   # hoja: Maestra (con columna Ensembl)
RUTA_SALIDA  = r"C:\Users\Usuario\Desktop\resultados_gwas.xlsx"

# === GWAS API ===================================================
BASE = "https://www.ebi.ac.uk/gwas/rest/api"
HEAD = {"Accept": "application/json", "User-Agent": "TFM-GWAS-Min/1.0"}
TIMEOUT = 25
SLEEP = 0.08

# ====== FILTRO POR FENOTIPO =====================================
USE_FILTER = True 

EFO_TDAH = {"EFO_0004284"}  # ADHD
KW_TDAH  = ("adhd", "attention deficit", "attention-deficit")

EFO_ACI = {
    "EFO_0004330",  # cognitive performance
    "EFO_0009706",  # intelligence
    "EFO_0010896",  # cognitive impairment
    "EFO_0005109",  # educational attainment
    "EFO_0000310",  # memory measurement
}
KW_ACI   = ("intelligence", "cognitive", "cognition", "iq", "general cognitive", "cognitive performance")


# ========================================================================
# ----------------> FUN 1 : LECTURA DE LA HOJA "MAESTRA" <----------------
# ========================================================================

def cargar_ensembl(path):
    """Devuelve un array (ndarray) de Ensembl IDs limpios y únicos."""
    df = pd.read_excel(path, sheet_name="Maestra")
    df.columns = [c.strip().lower() for c in df.columns]
    if "ensembl" not in df.columns:
        raise ValueError("No se encontró la columna 'Ensembl' en la hoja 'Maestra'.")
    ensembl_ids = df["ensembl"].dropna().astype(str).str.strip().unique()
    return ensembl_ids

# ========================================================================
# -----------------> FUN 2 : FILTROS (TDAH/ACI) <-------------------------
# ========================================================================

def es_interes(trait, efo_list):
    
    if not USE_FILTER:
        return True
    t = (trait or "").lower()
    # Keywords
    if any(k in t for k in KW_TDAH) or any(k in t for k in KW_ACI):
        return True
    # EFOs
    if efo_list:
        efos = set(efo_list.split(";"))
        if efos & EFO_TDAH: return True
        if efos & EFO_ACI:  return True
    return False


# ========================================================================
# -----------------> FUN 3 : CONSULTA A GWAS POR ENSEMBL <----------------
# ========================================================================

def gwas_por_ensembl(ensembl_id, max_pages=20, verbose=True):
    
    url = f"{BASE}/genes/{ensembl_id}/associations"
    filas, page = [], 0
    raw_count = 0
    kept_count = 0

    while page < max_pages:
        try:
            r = requests.get(url, headers=HEAD, params={"size": 500, "page": page}, timeout=TIMEOUT)
            if r.status_code != 200:
                break
            data = r.json()
        except Exception:
            break

        items = (data.get("_embedded", {}) or {}).get("associations", [])
        if not items:
            break

        for a in items:
            raw_count += 1
            trait = a.get("trait")
            efolist = a.get("efoTraits") or []
            efos = [e.get("shortForm") for e in efolist if e.get("shortForm")]
            if not trait and efolist:
                trait = efolist[0].get("trait")

            # Recolectar RSIDs
            rsids = []
            for locus in a.get("loci", []):
                for sra in locus.get("strongestRiskAlleles", []):
                    if sra.get("rsId"):
                        rsids.append(sra["rsId"])

            # --> Preparar representaciones
            efo_str = ";".join(sorted(set(efos))) if efos else None
            rsid_str = ";".join(sorted(set(rsids))) if rsids else None

            # --> Filtro temático 
            if not es_interes(trait, efo_str):
                continue
            kept_count += 1

            filas.append({
                "Ensembl": ensembl_id,
                "GCST": a.get("studyAccession"),
                "PMID": a.get("pubmedId"),
                "Trait": trait,
                "EFO": efo_str,
                "RSID": rsid_str,
                "PValue": a.get("pvalue"),
            })

        page += 1
        total = (data.get("page", {}) or {}).get("totalPages", 0)
        if page >= total:
            break
        time.sleep(SLEEP)

    if verbose:
        print(f"  [{ensembl_id}] asociaciones crudas: {raw_count} | tras filtro: {kept_count}")
    return filas


# ========================================================================
# ------------------ LLAMADO DE LAS FUNCIONES ----------------------------
# ========================================================================
def main():
    print("[1/2] Leyendo Ensembl (hoja 'Maestra')…")
    ens_ids = cargar_ensembl(RUTA_ENTRADA)
    print(f"   Ensembl únicos: {len(ens_ids)}")

    print(f"[2/2] Consultando GWAS…  (USE_FILTER={USE_FILTER})")
    out = []
    for ens in ens_ids:
        out.extend(gwas_por_ensembl(ens))
        time.sleep(SLEEP)

    res = pd.DataFrame(out, columns=["Ensembl", "GCST", "PMID", "Trait", "EFO", "RSID", "PValue"])
    with pd.ExcelWriter(RUTA_SALIDA, engine="openpyxl", mode="w") as xls:
        res.to_excel(xls, sheet_name="resultados_gwas", index=False)

    print("Listo:", os.path.abspath(RUTA_SALIDA))


if __name__ == "__main__":
    main()

