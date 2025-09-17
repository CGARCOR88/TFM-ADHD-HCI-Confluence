# -*- coding: utf-8 -*-

import time
import requests
import pandas as pd

# === RUTAS DE ARCHIVOS ==========================================

RUTA_ENTRADA = r"C:\Users\Usuario\Desktop\genes.xlsx"
RUTA_SALIDA  = r"C:\Users\Usuario\Desktop\resultados_1.xlsx"

USER_AGENT = "TFM-genes2e"
TIMEOUT = 25
SLEEP = 0.12
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}

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
    filas = []
    for s in symbols:
        params = {
            "q": s,
            "scopes": "symbol,alias",
            "species": "9606",
            "fields": "symbol,name,entrezgene,ensembl.gene,uniprot.Swiss-Prot",
            "size": 5
        }
        data = None
        try: 
            r = requests.get("https://mygene.info/v3/query", params=params, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                data = r.json()
        except Exception:
            data = None
        time.sleep(SLEEP)

        sym = s
        entrez = ensembl = uniprot = name = None
        if data and data.get("hits"):
            hit = data["hits"][0]
            sym = str(hit.get("symbol", sym))
            entrez = hit.get("entrezgene")
            ens = hit.get("ensembl", {})
            if isinstance(ens, dict):
                ensembl = ens.get("gene")
            elif isinstance(ens, list) and ens:
                ensembl = ens[0].get("gene")
            uni = hit.get("uniprot", {}).get("Swiss-Prot")
            uniprot = uni[0] if isinstance(uni, list) and uni else (uni if isinstance(uni, str) else None)
            name = hit.get("name")

        filas.append({"symbol": sym, "entrez": entrez, "ensembl": ensembl, "uniprot": uniprot, "name": name})

    df = pd.DataFrame(filas).reset_index(drop=True)
    return df  

# ================================================================
# -----------------> FUN 3: REACTOME (pathways) <-----------------
# ================================================================

def reactome_por_uniprot(uniprot_id):
    data = None
    try:
        url = f"https://reactome.org/ContentService/data/mapping/UniProt/{uniprot_id}/pathways"
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
    except Exception:
        data = None
    time.sleep(SLEEP)

    rutas = []
    if data:
        for p in data:
            rutas.append({
                "Reactome_ID": p.get("stId"),
                "Reactome_Name": p.get("displayName"),
                "Species": p.get("speciesName")
            })
    return rutas

# **********************************************************
# ****************** LLAMADO DE FUNCIONES ******************
# **********************************************************

def main():
    
    # --> FUN 1 : LECTURA DE LA HOJA
    
    print("[1/3] Leyendo genes…")
    genes_df = leer_genes(RUTA_ENTRADA)  # Symbol, Fenotipo, localizacion_cromosomica
    print(f"   Total de filas leídas: {len(genes_df)}")

    # --> FUN 2: MAPEO CON MyGene.info
    
    print("[2/3] Mapeando con MyGene.info…")
    mapping = mapear_mygene(genes_df["Symbol"].tolist())
    mapping.insert(0, "Fenotipo", genes_df["Fenotipo"].values)
    mapping.insert(1, "Symbol_input", genes_df["Symbol"].values)
    mapping.insert(2, "localizacion_cromosomica", genes_df["localizacion_cromosomica"].values)

    n_uni = int(mapping["uniprot"].notna().sum())
    print(f"   Filas con UniProt: {n_uni} / {len(mapping)}")

    # --> FUN 3: REACTOME (pathways)
    
    print("[3/3] Consultando Reactome…")
    r_rows = []
    for _, row in mapping.iterrows():
        fen, sym, uni = row["Fenotipo"], row["symbol"], row["uniprot"]
        if not uni:
            continue
        rutas = reactome_por_uniprot(uni)
        for ruta in rutas:
            r_rows.append({"Fenotipo": fen, "Symbol": sym, "UniProt": uni, **ruta})
    reactome_df = pd.DataFrame(r_rows, columns=["Fenotipo","Symbol","UniProt","Reactome_ID","Reactome_Name","Species"])
    if not reactome_df.empty:
        reactome_df = reactome_df.reset_index(drop=True)

    # **********************************************************
    # *********** PROCESAMIENTO DE DATOS Y EXPORTACIÓN *********
    # **********************************************************

    if not reactome_df.empty:
        by_paths = reactome_df.groupby("Symbol")["Reactome_Name"].apply(lambda s: "; ".join(sorted(set(s))))
    else:
        by_paths = pd.Series(dtype="object")

    master = mapping.copy()
    master.rename(columns={
        "symbol":"Gen", "entrez":"Entrez", "ensembl":"Ensembl",
        "uniprot":"UniProt", "name":"GeneName"
    }, inplace=True)
    master = master.join(by_paths.rename("Reactome_Pathways"), how="left", on="Gen")

    # --> Guardado de los datos.
    print(f"Guardando en: {RUTA_SALIDA}")
    with pd.ExcelWriter(RUTA_SALIDA) as xls:
        mapping.to_excel(xls, sheet_name="Mapping_IDs", index=False)
        if not reactome_df.empty:
            reactome_df.to_excel(xls, sheet_name="Reactome", index=False)
        master.to_excel(xls, sheet_name="Maestra", index=False)
      
    print("------------->Proceso finalizado.")

if __name__ == "__main__":
    main()

