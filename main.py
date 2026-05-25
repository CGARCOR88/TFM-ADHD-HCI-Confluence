# -*- coding: utf-8 -*-
"""
main.py  —  Punto de entrada del pipeline TFM-GENES
=====================================================
Ejecuta los pasos del pipeline de forma secuencial o individual.

Uso:
    python main.py              # Pipeline completo (pasos 1-6)
    python main.py --step 1     # Solo el paso indicado
    python main.py --from 3     # Desde el paso indicado hasta el final
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Pasos del pipeline ────────────────────────────────────────────────────────

STEPS = {
    1: ("Gene Mapping  (MyGene.info + Reactome)", "src.step01_gene_mapping"),
    2: ("GWAS Query    (EBI GWAS Catalog)",        "src.step02_gwas_query"),
    3: ("Intermediate  (normalización de datos)",  "src.step03_intermediate"),
    4: ("Create DB     (MySQL genes_2e)",           "src.step04_create_db"),
    5: ("Load Data     (INSERT / UPSERT MySQL)",    "src.step05_load_data"),
    6: ("Queries       (análisis vías compartidas)", "src.step06_queries"),
}


def run_step(step_num: int) -> bool:
    """Importa y ejecuta el main() del paso indicado. Devuelve True si OK."""
    name, module_path = STEPS[step_num]
    logger.info("=" * 60)
    logger.info(f"  PASO {step_num}: {name}")
    logger.info("=" * 60)
    t0 = time.perf_counter()
    try:
        import importlib
        mod = importlib.import_module(module_path)
        if hasattr(mod, "main"):
            mod.main()
        else:
            logger.warning(f"El módulo '{module_path}' no expone una función main().")
        elapsed = time.perf_counter() - t0
        logger.info(f"  Paso {step_num} completado en {elapsed:.1f}s\n")
        return True
    except Exception as exc:
        logger.error(f"  ERROR en paso {step_num}: {exc}", exc_info=True)
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline TFM-GENES: análisis de genes TDAH / ACI"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--step", type=int, choices=STEPS.keys(),
        help="Ejecuta únicamente el paso especificado (1-6)."
    )
    group.add_argument(
        "--from", dest="from_step", type=int, choices=STEPS.keys(),
        help="Ejecuta el pipeline desde el paso especificado hasta el final."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.step:
        steps_to_run = [args.step]
    elif args.from_step:
        steps_to_run = list(range(args.from_step, max(STEPS.keys()) + 1))
    else:
        steps_to_run = list(STEPS.keys())

    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║         PIPELINE TFM-GENES  —  INICIO       ║")
    logger.info("╚══════════════════════════════════════════════╝")
    logger.info(f"Pasos a ejecutar: {steps_to_run}\n")

    t_total = time.perf_counter()
    failed = []
    for n in steps_to_run:
        ok = run_step(n)
        if not ok:
            failed.append(n)
            logger.error(f"Pipeline interrumpido en el paso {n}.")
            break

    elapsed_total = time.perf_counter() - t_total
    if failed:
        logger.error(f"Pipeline FINALIZADO CON ERRORES. Pasos fallidos: {failed}")
        sys.exit(1)
    else:
        logger.info("╔══════════════════════════════════════════════╗")
        logger.info(f"║  Pipeline completado en {elapsed_total:.1f}s  —  OK       ║")
        logger.info("╚══════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
