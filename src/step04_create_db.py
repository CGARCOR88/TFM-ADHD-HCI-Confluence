# -*- coding: utf-8 -*-
"""
Step 04 — Creación de la base de datos MySQL
Crea la base de datos 'genes_2e' y sus tablas si no existen.
"""

import logging

import mysql.connector

from config.settings import DB_CFG, DB_NAME

logger = logging.getLogger(__name__)

# DDL de cada tabla en orden de creación (respeta dependencias FK)
_TABLAS = {
    "genes": """
        CREATE TABLE IF NOT EXISTS genes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(255),
            gen VARCHAR(255),
            simbolo VARCHAR(64) NOT NULL,
            localizacion_cromosomica VARCHAR(64),
            entrez_id BIGINT,
            ensembl_id VARCHAR(32),
            uniprot_id VARCHAR(32),
            UNIQUE (simbolo)
        )
    """,
    "articulos": """
        CREATE TABLE IF NOT EXISTS articulos (
            pmid BIGINT PRIMARY KEY,
            doi VARCHAR(255),
            titulo TEXT,
            anio YEAR
        )
    """,
    "vias": """
        CREATE TABLE IF NOT EXISTS vias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(255) UNIQUE,
            reactome_id VARCHAR(64) UNIQUE
        )
    """,
    "fenotipos": """
        CREATE TABLE IF NOT EXISTS fenotipos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trait VARCHAR(255),
            efo_id VARCHAR(64)
        )
    """,
    "variantes": """
        CREATE TABLE IF NOT EXISTS variantes (
            rsid VARCHAR(32) PRIMARY KEY,
            pvalue DOUBLE
        )
    """,
    "asociaciones": """
        CREATE TABLE IF NOT EXISTS asociaciones (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            gen_id INT,
            fenotipo_id INT,
            via_id INT,
            pmid BIGINT,
            rsid VARCHAR(32),
            pvalue DOUBLE,
            FOREIGN KEY (gen_id)      REFERENCES genes(id),
            FOREIGN KEY (fenotipo_id) REFERENCES fenotipos(id),
            FOREIGN KEY (via_id)      REFERENCES vias(id),
            FOREIGN KEY (pmid)        REFERENCES articulos(pmid),
            FOREIGN KEY (rsid)        REFERENCES variantes(rsid)
        )
    """,
}


def main():
    # Conectar sin base de datos para poder crearla
    cfg_sin_db = {k: v for k, v in DB_CFG.items() if k not in ("database", "autocommit")}
    cnx = mysql.connector.connect(**cfg_sin_db)
    cursor = cnx.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
        )
        logger.info("Base de datos '%s' lista.", DB_NAME)
        cursor.execute(f"USE `{DB_NAME}`")

        for nombre, ddl in _TABLAS.items():
            cursor.execute(ddl)
            logger.info("  Tabla '%s' verificada.", nombre)

        cnx.commit()
        logger.info("Paso 4 completado: esquema de base de datos listo.")
    except Exception as exc:
        logger.error("Error creando el esquema: %s", exc)
        raise
    finally:
        cursor.close()
        cnx.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(message)s",
    )
    main()

