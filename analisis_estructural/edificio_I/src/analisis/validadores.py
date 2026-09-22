"""
Validadores de entrada del analisis estructural del Edificio I.

No modifican diccionarios: devuelven una lista de :class:`ProblemaEntrada` con
codigo, nivel de severidad y mensaje, o elevan :class:`ErrorEntrada`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from shapely.geometry import LineString, Point

TIPOS_TRANSFERENCIA_SOPORTADOS = {
    "unidireccional_x",
    "unidireccional_y",
    "bidireccional",
    "por_definir",
}

# Tipos aceptados en un caso geometrico de ENSAYO (no diseno). Un ensayo no puede
# dejar ninguna losa en ``por_definir``.
TIPOS_ADMISIBLES_ENSAYO = {"unidireccional_x", "unidireccional_y", "bidireccional"}


@dataclass(frozen=True)
class ProblemaEntrada:
    codigo: str
    nivel: str                 # error | warning
    ubicacion: str
    mensaje: str


class ErrorEntrada(Exception):
    """Se eleva cuando hay un problema de severidad 'error' en la entrada."""

    def __init__(self, problemas: List[ProblemaEntrada]):
        self.problemas = problemas
        msgs = [f"[{p.codigo}] {p.ubicacion}: {p.mensaje}" for p in problemas]
        super().__init__("\n".join(msgs))


def _ids_duplicados(coleccion: List[dict], clave: str, rotulo: str) -> List[ProblemaEntrada]:
    vistos: Dict[str, int] = {}
    problemas: List[ProblemaEntrada] = []
    for item in coleccion:
        iid = item.get(clave)
        if iid is None:
            continue
        vistos[iid] = vistos.get(iid, 0) + 1
        if vistos[iid] == 2:
            problemas.append(
                ProblemaEntrada(
                    codigo="ID_DUPLICADO", nivel="error",
                    ubicacion=f"{rotulo}", mensaje=f"identificador '{iid}' repetido",
                )
            )
    return problemas


def _segmento_de(muro: dict) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    inicio = tuple(float(x) for x in muro["eje"]["inicio"])
    fin = tuple(float(x) for x in muro["eje"]["fin"])
    return inicio, fin


def _segmento_viga(viga: dict) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    return (tuple(float(x) for x in viga["inicio"]),
            tuple(float(x) for x in viga["fin"]))


def _linea_viga(viga: dict) -> LineString:
    a, b = _segmento_viga(viga)
    return LineString([a, b])


def _linea_muro(muro: dict) -> LineString:
    a, b = _segmento_de(muro)
    return LineString([a, b])


def _eje_interfaz_geometria(iface: dict) -> Optional[LineString]:
    eje = iface.get("eje_interfaz")
    if not eje:
        return None
    try:
        return LineString([tuple(float(x) for x in eje["inicio"]),
                           tuple(float(x) for x in eje["fin"])])
    except Exception:
        return None


def _linea_segmento(a, b) -> LineString:
    return LineString([a, b])


def validar_estructura(data: dict) -> List[ProblemaEntrada]:
    """Comprueba unicidad de identificadores y tipos de transferencia soportados."""
    problemas: List[ProblemaEntrada] = []
    if data.get("estado") == "borrador_no_ejecutable":
        problemas.append(
            ProblemaEntrada(
                codigo="GEOMETRIA_NO_EJECUTABLE", nivel="warning",
                ubicacion="estado",
                mensaje=("archivo base marcado 'borrador_no_ejecutable'; "
                         "solo se lee, no se ejecuta como diseno"),
            )
        )
    problemas += _ids_duplicados(data.get("losas", []), "id", "losas")
    problemas += _ids_duplicados(data.get("vigas", []), "id", "vigas")
    problemas += _ids_duplicados(data.get("muros", []), "id", "muros")
    problemas += _ids_duplicados(data.get("aberturas_globales", []), "id", "aberturas")
    problemas += _ids_duplicados(data.get("juntas_dilatacion", []), "id", "juntas")
    problemas += _ids_duplicados(data.get("interfaces_junta", []), "id", "interfaces")
    for losa in data.get("losas", []):
        tt = losa.get("tipo_transferencia")
        if tt not in TIPOS_TRANSFERENCIA_SOPORTADOS:
            problemas.append(
                ProblemaEntrada(
                    codigo="TIPO_TRANSFERENCIA_INVALIDO", nivel="error",
                    ubicacion=f"losas.{losa.get('id')}",
                    mensaje=f"tipo_transferencia '{tt}' no soportado",
                )
            )
    return problemas


def validar_receptores_existentes(data: dict) -> List[ProblemaEntrada]:
    """Cada apoyos_validos debe resolverse en una viga o un muro definidos."""
    problemas: List[ProblemaEntrada] = []
    catalogo = {v["id"] for v in data.get("vigas", [])} | \
               {m["id"] for m in data.get("muros", [])}
    for losa in data.get("losas", []):
        for rid in losa.get("apoyos_validos", []):
            if rid not in catalogo:
                problemas.append(
                    ProblemaEntrada(
                        codigo="RECEPTOR_INEXISTENTE", nivel="error",
                        ubicacion=f"losas.{losa.get('id')}",
                        mensaje=f"apoyo_valido '{rid}' no coincide con viga ni muro",
                    )
                )
    return problemas


def validar_edge_glob_ids_unicos(data: dict) -> List[ProblemaEntrada]:
    """Tramos de la interfaz global unicos por nivel (no se duplica el mismo tramo).

    NOTA: varios registros pueden compartir ``id_interfaz_global`` (los cinco tramos
    JD_EI_EII_CP1S..CP4 son UNA interfaz); NO se consideran duplicados. La unicidad se
    comprueba por ``id_tramo_nivel``.
    """
    problemas: List[ProblemaEntrada] = []
    globales = [j for j in data.get("interfaces_junta", [])
                if j.get("id_interfaz_global") == "JD_EI_EII_10CM"]
    tramos = [j.get("id_tramo_nivel") for j in globales]
    tramos = [t for t in tramos if t]
    vistos = []
    for t in tramos:
        if t in vistos:
            problemas.append(
                ProblemaEntrada(
                    codigo="TRAMO_GLOBAL_DUPLICADO", nivel="error",
                    ubicacion="interfaces_junta",
                    mensaje=f"tramo global '{t}' repetido en el mismo nivel",
                )
            )
        vistos.append(t)
    return problemas


def validar_interfaz_global_ensamblada(registros: List[dict]) -> List[ProblemaEntrada]:
    """Valida el modelo de la interfaz global en el ENSAMBLAJE (5 niveles).

    - unico id_interfaz_global (JD_EI_EII_10CM);
    - id_tramo_nivel unicos entre niveles (rechaza repetir el mismo tramo);
    - ancho_total_m = 0.10 (rechaza 0.20);
    - ancho_por_lado_m = null;
    - contabilizacion = una_sola_vez_en_modelo_conjunto;
    - transferencia_entre_edificios = false.
    """
    problemas: List[ProblemaEntrada] = []
    global_ids = {r.get("id_interfaz_global") for r in registros}
    if global_ids != {"JD_EI_EII_10CM"}:
        problemas.append(
            ProblemaEntrada(
                codigo="INTERFAZ_GLOBAL_INVALIDA", nivel="error",
                ubicacion="interfaz_global",
                mensaje=f"todos los registros deben usar id_interfaz_global=JD_EI_EII_10CM (obtenido {global_ids})",
            )
        )
    tramos = [r.get("id_tramo_nivel") for r in registros]
    tramos = [t for t in tramos if t]
    if len(tramos) != len(set(tramos)):
        problemas.append(
            ProblemaEntrada(
                codigo="TRAMO_GLOBAL_REPETIDO_ENSAMBLAJE", nivel="error",
                ubicacion="interfaz_global",
                mensaje="se repite un id_tramo_nivel entre niveles; cada nivel debe tener un tramo unico",
            )
        )
    if len(tramos) < 5:
        problemas.append(
            ProblemaEntrada(
                codigo="TRAMOS_GLOBALES_INCOMPLETOS", nivel="warning",
                ubicacion="interfaz_global",
                mensaje="se esperan cinco tramos: JD_EI_EII_CP1S, CP1, CP2, CP3, CP4",
            )
        )
    for r in registros:
        if r.get("ancho_total_m") != 0.10:
            problemas.append(
                ProblemaEntrada(
                    codigo="ANCHO_GLOBAL_INVALIDO", nivel="error",
                    ubicacion=f"interfaz_global.{r.get('id_tramo_nivel')}",
                    mensaje=f"ancho_total_m={r.get('ancho_total_m')} debe ser 0.10 (rechaza 0.20)",
                )
            )
        if r.get("ancho_por_lado_m") is not None:
            problemas.append(
                ProblemaEntrada(
                    codigo="ANCHO_POR_LADO_INVALIDO", nivel="error",
                    ubicacion=f"interfaz_global.{r.get('id_tramo_nivel')}",
                    mensaje="ancho_por_lado_m debe ser null (una sola vez, no por lado)",
                )
            )
        if r.get("contabilizacion") != "una_sola_vez_en_modelo_conjunto":
            problemas.append(
                ProblemaEntrada(
                    codigo="CONTABILIZACION_INVALIDA", nivel="error",
                    ubicacion=f"interfaz_global.{r.get('id_tramo_nivel')}",
                    mensaje="contabilizacion debe ser 'una_sola_vez_en_modelo_conjunto'",
                )
            )
        if r.get("transferencia_entre_edificios") is not False:
            problemas.append(
                ProblemaEntrada(
                    codigo="TRANSFERENCIA_ENTRE_EDIFICIOS", nivel="error",
                    ubicacion=f"interfaz_global.{r.get('id_tramo_nivel')}",
                    mensaje="transferencia_entre_edificios debe ser false",
                )
            )
    return problemas


def _clasificar_contacto_segmento_junta(ln: LineString, junta: LineString) -> str:
    """Clasifica el contacto de un segmento receptor con una linea de junta.

    Tipos devueltos (permitido = contacto sin cruzar; rechazado = cruza/solapa):
      - "ninguno"        -> no hay interseccion (permitido)
      - "extremo"        -> comparten un unico punto en el extremo del receptor
                            (permitido: el receptor REMATA en/o toca la junta sin cruzarla)
      - "t"              -> el extremo de la junta toca el interior del receptor
                            (permitido: la junta termina, el receptor no cruza)
      - "cruce"          -> el receptor atraviesa la junta por un punto interior
                            (RECHAZADO)
      - "solape"         -> el receptor se apoya/coincide colinealmente con la junta
                            (RECHAZADO: como un apoyo compartido sobre el vacio)
    """
    if not ln.intersects(junta):
        return "ninguno"
    inter = ln.intersection(junta)
    tipo = inter.geom_type

    if tipo == "LineString" or tipo.startswith("MultiLineString"):
        return "solape"  # colineal / solapado con la junta

    if tipo == "Point":
        p = inter
        return _clasificar_punto(ln, junta, p)
    if tipo == "MultiPoint":
        # varios contactos puntuales => siempre al menos un cruce (el receptor no esta
        # como un simple toque; o solapa a lo largo de varios puntos)
        for p in inter.geoms:
            if _clasificar_punto(ln, junta, p) == "cruce":
                return "cruce"
        return "cruce"

    # GeometryCollection u otro: descomponer conservadoramente
    if tipo == "GeometryCollection":
        rechazo = False
        for geom in inter.geoms:
            if geom.geom_type in ("LineString", "MultiLineString"):
                return "solape" if not rechazo else "cruce"
            if geom.geom_type in ("Point", "MultiPoint"):
                pts = geom.geoms if geom.geom_type == "MultiPoint" else [geom]
                for p in pts:
                    c = _clasificar_punto(ln, junta, p)
                    if c == "cruce":
                        return "cruce"
                rechazo = True
        return "cruce"

    return "cruce"  # estado desconocido => conservador: rechazar


def _clasificar_punto(ln: LineString, junta: LineString, p) -> str:
    """Clasifica un punto compartido: extremo del receptor, T, o cruce interior."""
    tol = 1e-9
    d_i = p.distance(Point(ln.coords[0]))
    d_j = p.distance(Point(ln.coords[-1]))
    es_extremo_receptor = min(d_i, d_j) <= tol
    d_ji = p.distance(Point(junta.coords[0]))
    d_jj = p.distance(Point(junta.coords[-1]))
    es_extremo_junta = min(d_ji, d_jj) <= tol

    if es_extremo_receptor:
        # el receptor termina justo en/sobre la junta (remate en la barrera)
        return "extremo"
    if es_extremo_junta:
        # la junta termina sobre el interior del receptor (T) => la junta NO la cruza
        return "t"
    # punto interior de ambos => el receptor atraviesa la junta
    return "cruce"


def validar_cruce_de_juntas(data: dict) -> List[ProblemaEntrada]:
    """Ningun receptor (viga/muro) debe CRUZAR ni SOLAPAR una junta con eje definido.

    Contactos permitidos: sin interseccion, elemento que remata en el extremo/toca la
    junta en un extremo, o junta que termina en T sobre el interior del receptor.
    Rechazados: cruce transversal por un punto interior y solape colineal con el vacio.

    Nota: la junta global EI-EII (sin eje confirmado en la cara del Edificio I) se
    valida por invariantes de metadata y por el control de barrera ensamblado
    (pendiente_correlacion_geometrica), por lo que aqui solo se revisan juntas cuyo eje
    este definido.
    """
    problemas: List[ProblemaEntrada] = []
    lineas_junta = []
    for iface in data.get("interfaces_junta", []):
        ej = _eje_interfaz_geometria(iface)
        if ej is not None:
            lineas_junta.append((iface.get("id", "?"), ej))
    for v in data.get("vigas", []):
        ln = _linea_viga(v)
        if ln.is_empty or ln.length == 0:
            continue
        for iid, junta in lineas_junta:
            c = _clasificar_contacto_segmento_junta(ln, junta)
            if c in ("cruce", "solape"):
                problemas.append(
                    ProblemaEntrada(
                        codigo="RECEPTOR_CRUZA_JUNTA", nivel="error",
                        ubicacion=f"vigas.{v['id']}",
                        mensaje=f"el receptor {c} la junta/interfaz '{iid}'",
                    )
                )
    for m in data.get("muros", []):
        ln = _linea_muro(m)
        if ln.is_empty or ln.length == 0:
            continue
        for iid, junta in lineas_junta:
            c = _clasificar_contacto_segmento_junta(ln, junta)
            if c in ("cruce", "solape"):
                problemas.append(
                    ProblemaEntrada(
                        codigo="RECEPTOR_CRUZA_JUNTA", nivel="error",
                        ubicacion=f"muros.{m['id']}",
                        mensaje=f"el receptor {c} la junta/interfaz '{iid}'",
                    )
                )
    return problemas


def clasificar_contacto_linea_junta(
    ln: LineString, junta: LineString
) -> str:
    """API publica para tests: devuelve la clasificacion de contacto."""
    return _clasificar_contacto_segmento_junta(ln, junta)


def validar_invariante_junta_global(data: dict) -> List[ProblemaEntrada]:
    """Invariantes de la junta global para el Edificio I."""
    problemas: List[ProblemaEntrada] = []
    tramos = [j for j in data.get("interfaces_junta", [])
              if j.get("id_interfaz_global") == "JD_EI_EII_10CM"]
    top = data.get("junta_dilatacion", {})
    for registro in tramos + ([top] if top else []):
        if registro.get("transferencia_entre_edificios") not in (False, None):
            problemas.append(
                ProblemaEntrada(
                    codigo="TRANSFERENCIA_ENTRE_EDIFICIOS", nivel="error",
                    ubicacion=f"junta.{registro.get('id','global')}",
                    mensaje="no puede existir transferencia hacia el Edificio II",
                )
            )
        if registro.get("ancho_total_m") not in (0.10, None):
            problemas.append(
                ProblemaEntrada(
                    codigo="ANCHO_JUNTA_INVALIDO", nivel="error",
                    ubicacion=f"junta.{registro.get('id','global')}",
                    mensaje=("el ancho total de la interfaz debe ser 0.10 m; "
                             "los anchos por lado no se suman"),
                )
            )
        if registro.get("no_borde_libre") is False:
            problemas.append(
                ProblemaEntrada(
                    codigo="JUNTA_BORDE_LIBRE", nivel="error",
                    ubicacion=f"junta.{registro.get('id','global')}",
                    mensaje="la junta global no es borde libre (no_borde_libre=true)",
                )
            )
    # invariante de contabilizacion: no debe haber un ancho 0.20 acumulado
    if top.get("contabilizacion", "") == "una_sola_vez_en_modelo_conjunto":
        pass  # aceptado
    return problemas


def validar_para_ensayo(losas: List[dict]) -> List[ProblemaEntrada]:
    """En un ensayo, cada losa debe declarar un tipo de transferencia admisible."""
    problemas: List[ProblemaEntrada] = []
    for losa in losas:
        tt = losa.get("tipo_transferencia")
        if tt not in TIPOS_ADMISIBLES_ENSAYO:
            problemas.append(
                ProblemaEntrada(
                    codigo="LOSA_SIN_TRANSFERENCIA_ENSAYO",
                    nivel="error",
                    ubicacion=f"losas.{losa.get('id')}",
                    mensaje=f"transferencia '{tt}' no admisible en ensayo; requiere "
                            "decision explicita por losa (unidireccional_x/y, bidireccional)",
                )
            )
    return problemas


def elevar_si_error(problemas: Iterable[ProblemaEntrada]) -> List[ProblemaEntrada]:
    """Convierte todos los problemas en lista; eleva ErrorEntrada si hay algun error."""
    lista = list(problemas)
    errores = [p for p in lista if p.nivel == "error"]
    if errores:
        raise ErrorEntrada(lista)
    return lista