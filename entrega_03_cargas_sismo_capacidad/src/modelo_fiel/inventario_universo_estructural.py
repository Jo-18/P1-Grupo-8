# -*- coding: utf-8 -*-
"""Inventario del universo estructural visible en el viewer (edificios I y II).

Clasifica cada objeto (columna, viga, muro) del viewer en una de las clases:
  ESTRUCTURAL_CONFIRMADO / NO_ESTRUCTURAL / REFERENCIA_O_HIPOTESIS / PENDIENTE_DE_FUENTE

Objetivo de cobertura del proyecto: 100% de ESTRUCTURAL_CONFIRMADO debe quedar
con resultado FE regenerado (MODELO_FE_COMPLETO). NO_ESTRUCTURAL y
REFERENCIA_O_HIPOTESIS quedan fuera del analisis riguroso. PENDIENTE_DE_FUENTE
queda fuera hasta resolver la fuente.

Reglas documentadas con evidencia (lamina/capa/coordenadas):
  - LAMINA P1S/P1/P2/P3: 2017_67-101/102 (+ P2=BORRADOR), RLE-PILAR + RLE-LOSA.
  - LAMINA P4 (cielo piso 4, cota 11.83): 2017_67-103.dxf; centros fisicos de
    columnas en capa RLE-SOLID a v = grilla + 0.1812 m (18/18 handles 1E202..),
    ver _candidata_unity.evidencia_columnas. Grid de vigas trasladado +0.18 en
    v (correccion_grid_longitudinal_P4, 2026-09-03), alero norte 0.23 -> 0.05 m.
  - EII: geometria con las mismas cotas de nivel que EI; columnas con rol
    'referencia_no_receptor_losa'/'receptor_nodal_activo' (rol de transferencia,
    no niega existencia fisica).

Estructura de salida: JSON + MD por edificio con conteos, clases, sub-estados,
correspondencia FE (tags) y notas de evidencia.
"""
import glob
import json
import os

RUTA = r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\P1"
VIEWER = os.path.join(RUTA, "viewer_unity", "Assets", "StreamingAssets", "lab_data", "edificios")
AUDIT = os.path.join(RUTA, "entrega_03_cargas_sismo_capacidad", "docs")
OUT = os.path.join(RUTA, "entrega_03_cargas_sismo_capacidad", "modelo_fiel")

CLASES = ("ESTRUCTURAL_CONFIRMADO", "REFERENCIA_O_HIPOTESIS", "NO_ESTRUCTURAL", "PENDIENTE_DE_FUENTE")

EVID_LAMINAS = {
    "EI_CP1S": "2017_67-101 (subterraneo, RLE-EXTABASE + RLE-PILAR)",
    "EI_P1": "2017_67-101 (piso 1; RLE-PILAR + RLE-LOSA)",
    "EI_P2": "2017_67-102 (piso 2 borrador; RLE-PILAR)",
    "EI_P3": "2017_67-102 (piso 3; RLE-PILAR + RLE-LOSA + RLE-VIGA)",
    "EI_P4": "2017_67-103 (cielo piso 4, cota 11.83; RLE-SOLID +0.1812 m, RLE-VIGA +0.18)",
    "EII_CP1S": "plano EII subterraneo (RLE-EXTABASE; cota -4.01)",
    "EII_CP1": "plano EII piso 1 (cota -0.05)",
    "EII_CP2": "plano EII piso 2 (cota 3.91)",
    "EII_CP3": "plano EII piso 3 (cota 7.87)",
    "EII_CP4": "plano EII cielo piso 4 (cota 11.83)",
}


def seccion_normalizada(sec):
    return (sec or "").strip()


def clasificar_columna(obj):
    sec = seccion_normalizada(obj.get("seccion"))
    oid = obj.get("id", "")
    if oid == "COL_EI_CP2_RLE_PILAR_10.00_20.27":
        return "NO_ESTRUCTURAL", "Huella RLE-PILAR (0.30x0.30) sin elemento resistente; excluida del modelo."
    if oid == "COL_EI_CP2_S_G3S1_18.96":
        return "NO_ESTRUCTURAL", "P.M. 300x300x20 sin huella en planta (RLE-TEXTO-1); excluida del modelo."
    if sec in ("P.M.I. (RLE-TEXTO-1, sin huella en planta)", "P.M.I."):
        return "PENDIENTE_DE_FUENTE", "Seccion P.M.I. por resolver (RLE-TEXTO-1, sin huella en planta); sin dimension de perfil."
    if sec.startswith("P.M. 300x300x20"):
        sub = "huella piso4_103 confirmada" if "huella piso4_103" in sec else "RLE-TEXTO-1"
        return "ESTRUCTURAL_CONFIRMADO", "Columna acero P.M.300x300x20 (%s); tramo/extremo superior a fijar por elevacion." % sub
    if sec in ("P. 70x70", "0.70x0.70"):
        return "ESTRUCTURAL_CONFIRMADO", "Columna concreto P.70x70 (RLE-PILAR/RLE-SOLID)."
    return "PENDIENTE_DE_FUENTE", "Seccion desconocida: %r." % sec


def clasificar_viga(obj):
    sec = seccion_normalizada(obj.get("seccion"))
    if sec in ("V. 60/80", "V.30/80", "V.40/80", "V.M. 300x300x5", "V.60/80"):
        return "ESTRUCTURAL_CONFIRMADO", "Viga con seccion confirmada."
    if sec in ("Diag. marco I'-J (elev 800)", "Diag. torre G-H (lamina 801/802)"):
        return "ESTRUCTURAL_CONFIRMADO", "Diagonal de arriostramiento real (lamina de elevacion respaldada)."
    if sec == "M.H.A. e=30":
        return "ESTRUCTURAL_CONFIRMADO", "Panel muro-placa M.H.A. e=30 (no viga); tratar como muro en el modelo FE."
    if sec in ("V.S.I. 20/150",):
        return "PENDIENTE_DE_FUENTE", "Seccion V.S.I. 20/150 pendiente de fuente (peralte/armadura sin confirmar)."
    if sec == "por_resolver":
        return "PENDIENTE_DE_FUENTE", "Seccion 'por_resolver' segun geometria viewer."
    return "PENDIENTE_DE_FUENTE", "Seccion desconocida: %r." % sec


def clasificar_muro(obj):
    espesor = obj.get("espesor")
    oid = obj.get("id", "")
    suffix = " (sub-segmento del mismo muro)" if any(s in oid for s in ("DER", "IZQ", "INF")) else ""
    return "ESTRUCTURAL_CONFIRMADO", ("Muro H.A. espesor %s%s (capa RLE-LOSA/RLE-MURO); "
                                       "continuidad vertical/segmentacion a verificar." % (espesor, suffix))


def clasificar(obj, tipo):
    if tipo == "columna":
        return clasificar_columna(obj)
    if tipo == "viga":
        return clasificar_viga(obj)
    if tipo == "muro":
        return clasificar_muro(obj)
    return "PENDIENTE_DE_FUENTE", "Tipo desconocido."


def fe_mapping_audit(edificio):
    path = os.path.join(AUDIT, "AUDITORIA_COBERTURA_VIEWER_FE_%s.json" % edificio)
    if not os.path.exists(path):
        return {}, None
    audit = json.load(open(path, encoding="utf-8"))
    mapa = {}
    for estado, fila in audit.get("viewer_a_fE", {}).items():
        for item in fila:
            clave = (item["nivel"], item["tipo"], item["id"])
            mapa[clave] = {"estado": estado, "tags": item.get("tags", [])}
    return mapa, audit.get("totales")


def cargar_viewer(edificio):
    base = os.path.join(VIEWER, edificio, "geometry")
    objs = []
    for f in sorted(glob.glob(os.path.join(base, "*.json"))):
        nivel = os.path.splitext(os.path.basename(f))[0]
        geo = json.load(open(f, encoding="utf-8"))
        for tipo in ("columnas", "vigas", "muros"):
            plural = tipo
            singular = "viga" if tipo == "vigas" else tipo[:-1]
            for o in geo.get(plural, []):
                objs.append({
                    "edificio": edificio,
                    "nivel": nivel,
                    "tipo": singular,
                    "id": o["id"],
                    "seccion": o.get("seccion") or ("e=%s" % o.get("espesor")),
                    "posicion_pts": o.get("posicion") or o.get("pts"),
                    "geometria": o,
                })
    return objs


def main():
    os.makedirs(OUT, exist_ok=True)
    resumen_total = {}
    for edificio in ("I", "II"):
        objs = cargar_viewer(edificio)
        mapa, totales_audit = fe_mapping_audit(edificio)
        registros = []
        conteo = {c: 0 for c in CLASES}
        for o in objs:
            clase, evidencia = clasificar(o, o["tipo"])
            conteo[clase] += 1
            registro = {
                "edificio": o["edificio"],
                "nivel": o["nivel"],
                "tipo": o["tipo"],
                "id": o["id"],
                "seccion": o["seccion"] if "seccion" in o else None,
                "clase": clase,
                "evidencia": evidencia,
                "lamina": EVID_LAMINAS.get("%s_%s" % (edificio, o["nivel"])),
            }
            fe = mapa.get((o["nivel"], o["tipo"], o["id"]))
            if fe:
                registro["fe_estado"] = fe["estado"]
                registro["fe_tags"] = fe["tags"]
            registros.append(registro)
        no_clasificados = [r for r in registros if r["clase"] not in CLASES]
        if no_clasificados:
            raise SystemExit("Objetos sin clase valida: %s" % [r["id"] for r in no_clasificados])
        confirmados = [r for r in registros if r["clase"] == "ESTRUCTURAL_CONFIRMADO"]
        sub_estado = {
            "analizado_1a1": sum(1 for r in confirmados if r.get("fe_estado") == "1A1"),
            "contenido": sum(1 for r in confirmados if r.get("fe_estado") == "CONTENIDO"),
            "sin_resultado": sum(1 for r in confirmados if r.get("fe_estado") == "SIN_RESULTADO_FE"),
            "sin_auditoria": sum(1 for r in confirmados if not r.get("fe_estado")),
        }
        salida = {
            "edificio": edificio,
            "clases": ["ESTRUCTURAL_CONFIRMADO", "REFERENCIA_O_HIPOTESIS", "NO_ESTRUCTURAL", "PENDIENTE_DE_FUENTE"],
            "totales_clases": conteo,
            "totales_estructural_confirmado": {
                "total": len(confirmados),
                "por_estado": sub_estado,
                "cobertura_actual_porcentaje": round(
                    100.0 * (sub_estado["analizado_1a1"] + sub_estado["contenido"]) / len(confirmados), 1
                ) if confirmados else None,
            },
            "totales_auditoria_previa": totales_audit,
            "objetos": registros,
        }
        with open(os.path.join(OUT, "inventario_universo_estructural_%s.json" % edificio), "w", encoding="utf-8") as fhd:
            json.dump(salida, fhd, ensure_ascii=False, indent=1)
        resumen_total[edificio] = {
            "totales_clases": conteo,
            "estructural": salida["totales_estructural_confirmado"],
        }
        escribir_md(salida, os.path.join(OUT, "inventario_universo_estructural_%s.md" % edificio))
        imprimir_revision(edificio, registros)
    with open(os.path.join(OUT, "inventario_universo_estructural_resumen.json"), "w", encoding="utf-8") as fhd:
        json.dump(resumen_total, fhd, ensure_ascii=False, indent=1)
    print(json.dumps(resumen_total, ensure_ascii=False, indent=1))


def imprimir_revision(edificio, registros):
    casos = [r for r in registros if r["clase"] != "ESTRUCTURAL_CONFIRMADO"]
    print("== EDIFICIO %s casos especiales (%d) ==" % (edificio, len(casos)))
    for r in sorted(casos, key=lambda x: (x["tipo"], x["id"])):
        print("  [%s] %s %s %s | %s" % (r["clase"][:4], r["nivel"], r["tipo"], r["id"], r["evidencia"][:70]))


def escribir_md(salida, path):
    ed = salida["edificio"]
    lin = ["# Inventario Universo Estructural - Edificio %s" % ed, ""]
    lin.append("Clases: `ESTRUCTURAL_CONFIRMADO` / `REFERENCIA_O_HIPOTESIS` / `NO_ESTRUCTURAL` / `PENDIENTE_DE_FUENTE`.")
    lin.append("")
    lin.append("## Totales por clase")
    lin.append("")
    lin.append("| Clase | N |")
    lin.append("|---|---|")
    for c in salida["clases"]:
        lin.append("| %s | %d |" % (c, salida["totales_clases"][c]))
    lin.append("")
    e = salida["totales_estructural_confirmado"]
    lin.append("## Estructural confirmado (objetivo 100%% cubierto)")
    lin.append("")
    lin.append("| Estado | N |")
    lin.append("|---|---|")
    for k, v in e["por_estado"].items():
        lin.append("| %s | %d |" % (k, v))
    lin.append("| **Total** | **%d** |" % e["total"])
    lin.append("")
    lin.append("Cobertura actual (1A1+CONTENIDO): **%s%%**" % e["cobertura_actual_porcentaje"])
    lin.append("")
    lin.append("## Detalle por nivel / tipo / clase")
    lin.append("")
    lin.append("| Nivel | Tipo | Clase | id | Seccion | FE | Evidencia |")
    lin.append("|---|---|---|---|---|---|---|")
    orden_tipo = {"columna": 0, "viga": 1, "muro": 2}
    for r in sorted(salida["objetos"], key=lambda x: (x["nivel"], orden_tipo[x["tipo"]], x["id"])):
        fe = (r.get("fe_estado") or "-") + (" tags %s" % r.get("fe_tags") if r.get("fe_tags") else "")
        lin.append("| %s | %s | %s | %s | %s | %s | %s |"
                   % (r["nivel"], r["tipo"], r["clase"], r["id"], r.get("seccion") or "-", fe, (r.get("evidencia") or "").replace("|", "/")))
    open(path, "w", encoding="utf-8").write("\n".join(lin))
    print("MD escrita:", path)


if __name__ == "__main__":
    main()