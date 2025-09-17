# -*- coding: utf-8 -*-

import mysql.connector

         ######################
         # Conexion con MySQL #
         ######################
         
conexion = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="1234"
)

print("Conexión exitosa")

cursor = conexion.cursor()

cursor.execute("""
    CREATE DATABASE IF NOT EXISTS genes_2e
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci
""")
print(" 1. Base de datos 'genes_2e' creada con éxito ")

# Seleccionar la base
cursor.execute("USE genes_2e")

         ######################
         # Creacion de tablas #
         ######################

# --->TABLA GENES--------------------------------------------------------------

cursor.execute("""
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
""")

# --->TABLA ARTICULOS----------------------------------------------------------

cursor.execute("""
    CREATE TABLE IF NOT EXISTS articulos (
        pmid BIGINT PRIMARY KEY,
        doi VARCHAR(255),
        titulo TEXT,
        anio YEAR
    )
""")

# --->TABLA PATHWAYS---------------------------------------------------------------

cursor.execute("""
    CREATE TABLE IF NOT EXISTS vias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(255) UNIQUE,
        reactome_id VARCHAR(64) UNIQUE
    )
""")
    

# --->TABLFENOTIPOS------------------------------------------------------------
cursor.execute("""
    CREATE TABLE IF NOT EXISTS fenotipos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trait VARCHAR(255),
        efo_id VARCHAR(64)
    )
""")

# --->TABLA VARIANTES----------------------------------------------------------
cursor.execute("""
    CREATE TABLE IF NOT EXISTS variantes (
        rsid VARCHAR(32) PRIMARY KEY,
        pvalue DOUBLE
    )
""")

# --->TABLA ASOCIACIONES (PUENTE)----------------------------------------------
cursor.execute("""
    CREATE TABLE IF NOT EXISTS asociaciones (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        gen_id INT,
        fenotipo_id INT,
        via_id INT,
        pmid BIGINT,
        rsid VARCHAR(32),
        pvalue DOUBLE,

        FOREIGN KEY (gen_id) REFERENCES genes(id),
        FOREIGN KEY (fenotipo_id) REFERENCES fenotipos(id),
        FOREIGN KEY (via_id) REFERENCES vias(id),
        FOREIGN KEY (pmid) REFERENCES articulos(pmid),
        FOREIGN KEY (rsid) REFERENCES variantes(rsid)
    )
""")


conexion.commit()
cursor.close()
conexion.close()

print(" 2.Tablas creadas con éxito ")

