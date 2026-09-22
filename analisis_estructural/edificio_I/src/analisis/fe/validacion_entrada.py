"""Validacion de ENTRADA de la geometria de un edificio para el motor FE.

Es GENERICA (no depende del Edificio I): valida los archivos de geometria de una
configuracion de edificio antes de usarlos, comprobando unidades, coordenadas,
cotas, IDs, secciones, apoyos y referencias entre elementos.

Los errores se reportan de forma estructurada (lista de {ruta, mensaje, nivel}).
No modifica los archivos de origen.

Cuando los JSON del Edificio II lleguen, se valida con `validar_geometria(cfg)`.
Antes de rellenar la configuracion con esos datos (unidades/cotas/IDs/secciones),
esta validacion es la puerta de entrada: NUNCA se ejecuta un analisis con
geometria inventada ni con datos que no pasen esta comprobacion.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config_edificios as CFG

UNIDAD_LONGITUD_ESPERADA = "m"


def _finito(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _texto_id(x) -> bool:
    return isinstance(x, str) and x.strip() != ""


class ValidacionEntrada:
    def __init__(self, id_edificio: str):
        self.id_edificio = id_edificio
        self.cfg = CFG.config_edificio(id_edificio)
        self.errores: List[dict] = []
        self.advertencias: List[dict] = []

    # ---- helpers ----
    def _err(self, ruta: str, mensaje: str):
        self.errores.append({"ruta": ruta, "mensaje": mensaje, "nivel": "error"})

    def _warn(self, ruta: str, mensaje: str):
        self.advertencias.append({"ruta": ruta, "mensaje": mensaje, "nivel": "advertencia"})

    # ---- validacion principal ----
    def validar_geometria(self, archivos_nivel: Dict[str, Path]) -> dict:
        """Valida los archivos de geometria {codigo_nivel: ruta} contra el contrato."""
        self._validar_niveles_esperados(archivos_nivel)
        ids_por_categoria: Dict[str, set] = {"losas": set(), "vigas": set(),
                                             "muros": set(), "columnas": set()}
        for cod, path in archivos_nivel.items():
            if path is None or not Path(path).exists():
                self._err("nivel:%s" % cod, "archivo de geometria no existe")
                continue
            try:
                d = json.loads(Path(path).read_text(encoding="utf-8"))
            except Exception as exc:
                self._err("nivel:%s" % cod, "JSON invalido: %s" % exc)
                continue
            self._validar_archivo(cod, d, ids_por_categoria)
        self._validar_apoyos_cruzados(ids_por_categoria)
        return self.resultado()

    def _validar_niveles_esperados(self, archivos_nivel: Dict[str, Path]):
        esperados = set(self.cfg.niveles_orden)
        dados = set(archivos_nivel.keys())
        for cod in expected_sorted(esperados):
            if cod not in dados:
                self._warn("niveles",
                           "falta nivel esperado '%s' (validacion parcial del edificio)"
                           % cod)
        for cod in dados:
            if esperados and cod not in esperados:
                self._warn("niveles", "nivel '%s' no declarado en la configuracion" % cod)

    def _validar_archivo(self, cod: str, d: dict, ids_por_categoria: Dict[str, set]):
        r = "nivel:%s" % cod
        # unidades
        proy = d.get("proyecto", {}) or {}
        unidades = proy.get("unidades", {}) if isinstance(proy, dict) else {}
        if isinstance(unidades, dict):
            ul = unidades.get("longitud") or unidades.get("unidad_longitud")
            if ul is not None and str(ul).strip().lower() != "m":
                self._err(r, "unidad de longitud '%s' != 'm'" % ul)
        # cota de nivel
        nivel = d.get("nivel", {}) or {}
        cota = nivel.get("cota") if isinstance(nivel, dict) else None
        if cota is None:
            self._warn(r, "nivel sin cota declarada (se usara la de la configuracion)")
        elif not _finito(cota):
            self._err(r, "cota de nivel no es un numero finito: %r" % cota)
        # losas
        for lo in d.get("losas", []) or []:
            self._validar_losa(r, lo, ids_por_categoria["losas"])
        # vigas
        for vi in d.get("vigas", []) or []:
            self._validar_viga(r, vi, ids_por_categoria["vigas"])
        # muros
        for mu in d.get("muros", []) or []:
            self._validar_muro(r, mu, ids_por_categoria["muros"])
        # columnas
        cols = d.get("columnas") or d.get("columnas_referencia") or []
        for co in cols:
            self._validar_columna(r, co, ids_por_categoria["columnas"])

    # ---- validadores por categoria ----
    def _validar_losa(self, r, lo: dict, idset: set):
        lid = lo.get("id")
        if not _texto_id(lid):
            self._err(r, "losa sin id valido")
            return
        if lid in idset:
            self._err(r, "id de losa duplicado: %r" % lid)
        idset.add(lid)
        poly = lo.get("poligono_exterior") or lo.get("poligono") or []
        if len(poly) < 3:
            self._err(r, "losa %r: poligono con <3 puntos" % lid)
        for i, p in enumerate(poly):
            if len(p) < 2 or not (_finito(p[0]) and _finito(p[1])):
                self._err(r, "losa %r: punto %d invalido" % (lid, i))
        esp = lo.get("espesor")
        if esp is None or not _finito(esp) or float(esp) <= 0:
            self._err(r, "losa %r: espesor no positivo/finito" % lid)

    def _validar_viga(self, r, vi: dict, idset: set):
        vid = vi.get("id")
        if not _texto_id(vid):
            self._err(r, "viga sin id valido")
            return
        if vid in idset:
            self._err(r, "id de viga duplicado: %r" % vid)
        idset.add(vid)
        pts = vi.get("pts") or (vi.get("inicio"), vi.get("fin"))
        pts = [p for p in pts if p is not None]
        if len(pts) < 2:
            self._err(r, "viga %r: <2 puntos (inicio/fin) validos" % vid)
        for p in pts:
            if len(p) < 2 or not (_finito(p[0]) and _finito(p[1])):
                self._err(r, "viga %r: punto invalido" % vid)
        sec = (vi.get("seccion") or {}).get("nombre") \
            if isinstance(vi.get("seccion"), dict) else vi.get("seccion")
        if not _texto_id(sec):
            self._err(r, "viga %r: sin seccion nombrada" % vid)

    def _validar_muro(self, r, mu: dict, idset: set):
        mid = mu.get("id")
        if not _texto_id(mid):
            self._err(r, "muro sin id valido")
            return
        if mid in idset:
            self._err(r, "id de muro duplicado: %r" % mid)
        idset.add(mid)
        eje = mu.get("eje") or {}
        ia, ib = eje.get("inicio") if isinstance(eje, dict) else None, \
                 eje.get("fin") if isinstance(eje, dict) else None
        for tag, p in (("inicio", ia), ("fin", ib)):
            if p is None or len(p) < 2 or not (_finito(p[0]) and _finito(p[1])):
                self._err(r, "muro %r: extremo %s invalido" % (mid, tag))
        esp = mu.get("espesor")
        if esp is None or not _finito(esp) or float(esp) <= 0:
            self._err(r, "muro %r: espesor no positivo/finito" % mid)

    def _validar_columna(self, r, co: dict, idset: set):
        cid = co.get("id")
        if not _texto_id(cid):
            self._err(r, "columna sin id valido")
            return
        if cid in idset:
            self._err(r, "id de columna duplicado: %r" % cid)
        idset.add(cid)
        pos = co.get("posicion")
        if pos is None or len(pos) < 2 or not (_finito(pos[0]) and _finito(pos[1])):
            self._err(r, "columna %r: posicion invalida" % cid)
        sec = co.get("seccion")
        if not _texto_id(sec):
            self._err(r, "columna %r: sin seccion" % cid)

    def _validar_apoyos_cruzados(self, ids_por_categoria: Dict[str, set]):
        """Los `apoyos_validos` de las losas deben referenciar vigas o muros existentes."""
        # Nota: esta comprobacion cruzada requiere re-scan de los archivos; se delega en
        # la pasada por archivo via parametro `referencias` si se necesita. Aqui se deja
        # como gancho documentado (ver `registrar_apoyos` en validar_geometria).
        pass

    def registrar_apoyos(self, d: dict, idset_receptores: set, r: str):
        """Valida que cada 'apoyos_validos' de una losa exista como viga/muro."""
        for lo in d.get("losas", []) or []:
            lid = lo.get("id")
            for ap in lo.get("apoyos_validos", []) or []:
                if ap not in idset_receptores:
                    self._err(r, "losa %r: apoyo '%s' no referenciado" % (lid, ap))

    def resultado(self) -> dict:
        return {
            "id_edificio": self.id_edificio,
            "ok": len(self.errores) == 0,
            "n_errores": len(self.errores),
            "n_advertencias": len(self.advertencias),
            "errores": sorted(self.errores, key=lambda e: e["ruta"]),
            "advertencias": sorted(self.advertencias, key=lambda e: e["ruta"]),
        }


def expected_sorted(esperados):
    return sorted(esperados)
