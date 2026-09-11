"""Perfiles y manifest de integridad para la iteracion modelo_fiel.

Dos perfiles:
  * checkpoint_semana3 : reproduce los resultados congelados del commit de la
    Entrega 3 (tag `entrega-03-checkpoint-verificado`). El manifest guarda el
    SHA-256 de cada archivo versionado (`docs/tables/`, `docs/assets/`) y de
    los resultados fisicos (`results/`, `figures/`) mas valores de referencia
    (totales, equilibrios, errores de superposicion). La verificacion vuelve a
    hashear y compara; detecta cualquier desviacion accidental.
  * modelo_fiel        : manifest de las salidas nuevas bajo `modelo_fiel/`.

Uso (desde entrega_03_cargas_sismo_capacidad):
  python -X utf8 -m src.modelo_fiel.perfiles --crear checkpoint_semana3
  python -X utf8 -m src.modelo_fiel.perfiles --crear modelo_fiel
  python -X utf8 -m src.modelo_fiel.perfiles --verificar checkpoint_semana3
  python -X utf8 -m src.modelo_fiel.perfiles --verificar modelo_fiel

Salidas bajo `modelo_fiel/perfiles/`:
  checkpoint_semana3_manifest.json / _verificacion.md
  modelo_fiel_manifest.json / _verificacion.md
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
PERFILES_DIR = E3 / "modelo_fiel" / "perfiles"

TAG_CHECKPOINT = "entrega-03-checkpoint-verificado"
COMMIT_CHECKPOINT = "9413871ef1a7fe577cca43f8ce40cc1852bcd8fe"

# Diversos de archivos (mismo algoritmo para todos los tipos).
_EXT_JSON = (".json",)
_EXT_TODO = (".json", ".csv", ".md", ".png", ".txt")


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _git_head() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(REPO), timeout=20)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # noqa: BLE001 - perfil no puede depender de git
        pass
    return "git-indisponible"


def _walk_files(root: Path, ext=...) -> list:
    if not root.exists():
        return []
    files = [p for p in sorted(root.rglob("*")) if p.is_file()]
    if ext is ...:
        outs = []
        for p in files:
            parts = p.name.lower()
            if not parts.endswith((".json", ".csv", ".md", ".png", ".txt", ".asset")):
                continue
            outs.append(p)
        return outs
    return [p for p in files if p.suffix.lower() in ext]


def _relative_items(root: Path, files: list) -> dict:
    return {str(p.relative_to(root)).replace("\\", "/"): _hash_file(p)
            for p in files}


def _archivos_checkpoint() -> dict:
    """Conjunto de archivos congelados del checkpoint (versionados + fisicos)."""
    items = {}
    for sub in ("docs/tables", "docs/assets"):
        root = E3 / sub
        for p in _walk_files(root):
            items[str(p.relative_to(E3)).replace("\\", "/")] = _hash_file(p)
    for sub in ("results/cargas", "results/superposicion",
                "results/ejecutor_entrega_03", "results/capacidad_rc"):
        root = E3 / sub
        for p in _walk_files(root):
            items[str(p.relative_to(E3)).replace("\\", "/")] = _hash_file(p)
    for p in sorted((E3 / "results").glob("peso_propio_teorico_*.json")):
        items[str(p.relative_to(E3)).replace("\\", "/")] = _hash_file(p)
    return items


def _archivos_modelo_fiel() -> dict:
    """Salidas del perfil fiel (todo `modelo_fiel/` salvo el propio dir perfiles)."""
    root = E3 / "modelo_fiel"
    arch = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if "perfiles" in p.parts:
            continue                       # el manifest no se manifiesta a si mismo
        arch[str(p.relative_to(E3)).replace("\\", "/")] = _hash_file(p)
    return arch


def _valores_referencia_checkpoint() -> dict:
    """Valores esenciales del checkpoint (semanticos, no solo bytes)."""
    out = {"commit_checkpoint": COMMIT_CHECKPOINT,
           "tag": TAG_CHECKPOINT,
           "tolerancias": {"equilibrio_vertical_abs_kN": 1e-4}}
    car = {}
    for f in sorted((E3 / "results" / "cargas").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        name = f.name
        if name == "caso_G_EII_reproducible.json":
            sol = d.get("solucion", {})
            car["G_EII_reproducible"] = {
                "P_z_aplicada_kN": sol.get("F_total_aplicado_kN", [None])[2]}
            car["G_EII_reproducible"]["R_z_kN"] = round(
                sum(r[2] for r in d.get("solucion", {}).get("reacciones", {}).values()), 6)
        if name in ("caso_Q_EI_FE.json", "caso_Q_EII_FE.json"):
            car[name] = {"F_total_aplicado_kN": d.get("solucion", {})
                         .get("F_total_aplicado_kN")}
        if name == "carga_viva_Q_resumen.json":
            car[name] = {"globales": d.get("edificios")}
        if name.startswith("caso_sismico_"):
            car.setdefault(name, {})["corte_basal_kN"] = sum(
                fl.get("F_lateral_kN", 0.0)
                for fl in d.get("sismo", {}).get("ledger_por_nivel", []))
    out["cargas"] = car

    sup = {}
    for f in sorted((E3 / "results" / "superposicion").glob("*completa*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        sup[f.name] = {
            "estado": d.get("estado"),
            "mensaje": d.get("mensaje"),
            "max_error_rel": d.get("max_error_rel"),
        }
    out["superposicion"] = sup
    return out


def _valores_referencia_modelo_fiel() -> dict:
    out = {}
    for f in sorted((E3 / "modelo_fiel").rglob("*.json")):
        if "perfiles" in str(f):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        name = str(f.relative_to(E3)).replace("\\", "/")
        if f.name.startswith(("G_EI_MODELO_FIEL_", "G_EII_MODELO_FIEL_")):
            per = d.get("ledger", d.get("perfiles", {}))
            out[name] = {
                "G_antes_kN": per.get("G_antes_kN") or per.get("G_confirmado_kN"),
                "G_despues_kN": per.get("G_despues_kN"),
                "equilibrio": (per.get("equilibrio_vertical")
                               or per.get("equilibrio_despues")),
            }
    return out


def _escribir_manifest(perfil: str, archivos: dict, valores: dict) -> Path:
    PERFILES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "perfil": perfil,
        "creado": None,  # no timestamps: el hash del manifest debe ser deterministico
        "commit_referencia": COMMIT_CHECKPOINT if perfil == "checkpoint_semana3" else None,
        "head_working": _git_head(),
        "n_archivos": len(archivos),
        "archivos": archivos,
        "valores_referencia": valores,
    }
    out = PERFILES_DIR / ("%s_manifest.json" % perfil)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    return out


def _cargar_manifest(perfil: str) -> dict:
    out = PERFILES_DIR / ("%s_manifest.json" % perfil)
    if not out.exists():
        raise SystemExit("no existe manifest del perfil '%s' (%s)" % (perfil, out))
    return json.loads(out.read_text(encoding="utf-8"))


def _verificar(perfil: str) -> dict:
    if perfil == "checkpoint_semana3":
        archivos = _archivos_checkpoint()
        valores = _valores_referencia_checkpoint()
    elif perfil == "modelo_fiel":
        archivos = _archivos_modelo_fiel()
        valores = _valores_referencia_modelo_fiel()
    else:
        raise SystemExit("perfil desconocido: %s" % perfil)

    ref = _cargar_manifest(perfil)
    mismatch = []
    for rel, h in sorted(ref["archivos"].items()):
        p = E3 / rel
        if not p.exists():
            mismatch.append({"archivo": rel, "error": "FALTA"})
            continue
        now = _hash_file(p)
        if now != h:
            mismatch.append({"archivo": rel, "esperado": h, "actual": now,
                             "error": "DIFIERE"})
    extra = sorted(set(archivos) - set(ref["archivos"]))
    ok = not mismatch
    return {"perfil": perfil, "ok": ok,
            "archivos_verificados": len(ref["archivos"]),
            "discrepancias": mismatch,
            "archivos_nuevos_no_manifestados": extra}


def _markdown(ver: dict) -> str:
    lines = [
        "# Verificacion de perfil: %s" % ver["perfil"],
        "",
        "- estado: **%s**" % ("OK" if ver["ok"] else "FALLO"),
        "- archivos verificados: %d" % ver["archivos_verificados"],
        "- discrepancias: %d" % len(ver["discrepancias"]),
    ]
    for m in ver["discrepancias"]:
        lines.append("  - `%s`: %s" % (m["archivo"], m["error"]))
    if ver.get("archivos_nuevos_no_manifestados"):
        lines.append("- nuevos no manifestados: %d"
                     % len(ver["archivos_nuevos_no_manifestados"]))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    accion = None
    perfil = None
    if "--crear" in args:
        accion = "crear"
        perfil = args[args.index("--crear") + 1]
    elif "--verificar" in args:
        accion = "verificar"
        perfil = args[args.index("--verificar") + 1]
    if accion is None or perfil is None:
        raise SystemExit(__doc__)

    PERFILES_DIR.mkdir(parents=True, exist_ok=True)
    if accion == "crear":
        if perfil == "checkpoint_semana3":
            arch = _archivos_checkpoint()
            val = _valores_referencia_checkpoint()
        elif perfil == "modelo_fiel":
            arch = _archivos_modelo_fiel()
            val = _valores_referencia_modelo_fiel()
        else:
            raise SystemExit("perfil desconocido: %s" % perfil)
        if not arch:
            raise SystemExit("no hay archivos que manifestar para '%s'" % perfil)
        out = _escribir_manifest(perfil, arch, val)
        print(json.dumps({"accion": "crear", "perfil": perfil,
                          "n_archivos": len(arch), "manifest": str(out)},
                         ensure_ascii=False, indent=2))
    else:
        ver = _verificar(perfil)
        md = _markdown(ver)
        (PERFILES_DIR / ("%s_verificacion.md" % perfil)).write_text(
            md, encoding="utf-8")
        print(json.dumps(ver, ensure_ascii=False, indent=2))
        return 0 if ver["ok"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())