"""Valida un archivo JSON de geometria contra el esquema canonico.

Uso (desde la raiz del repositorio):
    python -m src.areas_tributarias.validar_formato <ruta_json> [esquema]

Codigos de salida:
    0  archivo valido contra el esquema
    2  archivo no valido, o no se encuentra el archivo/schema
    3  falta el paquete 'jsonschema'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except Exception as exc:  # pragma: no cover
    sys.stderr.write(
        "ERROR: se requiere el paquete 'jsonschema' (pip install jsonschema)\n"
        f"detalle: {exc}\n"
    )
    sys.exit(3)


def _resolver_esquema(ruta_esquema: str | Path | None, referencia: Path) -> Path:
    """Resuelve la ruta del esquema; si no se indica, busca el canonico."""
    if ruta_esquema is not None:
        return Path(ruta_esquema)
    for candidato in (
        Path.cwd() / "datos" / "geometria" / "esquema_entrada_areas_tributarias_v1.json",
        referencia.parent / "esquema_entrada_areas_tributarias_v1.json",
    ):
        if candidato.exists():
            return candidato
    raise FileNotFoundError(
        "No se encontro el esquema canonico; indicar su ruta explicitamente."
    )


def validar(datos: dict, esquema: dict) -> list:
    """Devuelve los errores de jsonschema (vacios si el documento valida)."""
    validator = Draft202012Validator(esquema)
    return sorted(validator.iter_errors(datos), key=lambda e: list(e.path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ruta_json", help="Archivo JSON de geometria a validar")
    parser.add_argument(
        "esquema",
        nargs="?",
        default=None,
        help="Ruta del esquema canonico (opcional; se busca automaticamente)",
    )
    args = parser.parse_args(argv)

    ruta_json = Path(args.ruta_json)
    if not ruta_json.exists():
        sys.stderr.write(f"ERROR: no existe el archivo {ruta_json}\n")
        return 2

    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    ruta_esquema = _resolver_esquema(args.esquema, Path(__file__).resolve())
    with open(ruta_esquema, "r", encoding="utf-8") as f:
        esquema = json.load(f)

    version = datos.get("version_formato")
    if not isinstance(version, str):
        sys.stderr.write("ERROR: falta 'version_formato' (string) en el JSON validado\n")
        return 2

    errores = validar(datos, esquema)
    nombre = ruta_json.name
    if not errores:
        print(f"[OK] {nombre}: valido contra el esquema (version_formato={version})")
        return 0

    print(f"[FALLO] {nombre}: {len(errores)} error(es) contra el esquema:")
    for e in errores:
        ruta = "/".join(str(p) for p in e.path) or "(raiz)"
        print(f"  - {ruta}: {e.message}")
    return 2


if __name__ == "__main__":
    sys.exit(main())