"""Especificación de los datasets DS01-DS09.

Fuente: diccionario_variables.xlsx (una hoja por dataset; columnas Variable,
Tipo y Unidad). Los nombres, tipos y unidades se copiaron literalmente de esas
hojas; `verificar_contra_diccionario` comprueba que sigan coincidiendo y
reporta cualquier diferencia en vez de ajustarla.

Naturaleza del dato (regla 4 del encargo y hoja Léame):
- real: DS09 (IPM del INEI) y la geografía INEI (ubigeo, departamento,
  provincia, distrito, macrorregión, localidad capital de distrito).
- estimado: población servida y población beneficiaria.
- sintético: todo lo demás (EPS, montos, expedientes, proyectos, CUI, documentos).
"""

from __future__ import annotations

from dataclasses import dataclass, field

TIPOS = ("texto", "entero", "decimal", "fecha", "booleano")
NATURALEZAS = ("real", "sintético", "estimado", "supuesto")


@dataclass(frozen=True)
class Columna:
    nombre: str
    tipo: str
    unidad: str
    naturaleza: str = "sintético"
    nota: str = ""

    def __post_init__(self) -> None:
        assert self.tipo in TIPOS, self.tipo
        assert self.naturaleza in NATURALEZAS, self.naturaleza


@dataclass(frozen=True)
class Dataset:
    codigo: str  # DS01 ... DS09
    nombre: str  # nombre del CSV sin extensión = hoja del diccionario = tabla
    descripcion: str
    llave: tuple[str, ...]  # llave natural esperada (unicidad)
    columnas: tuple[Columna, ...] = field(default_factory=tuple)

    @property
    def archivo(self) -> str:
        return f"{self.nombre}.csv"

    @property
    def tabla(self) -> str:
        return self.nombre

    def columna(self, nombre: str) -> Columna:
        for c in self.columnas:
            if c.nombre == nombre:
                return c
        raise KeyError(nombre)


C = Columna
REAL_INEI = "Geografía INEI (hoja Léame)"
EST_POB = "Estimada con la densidad poblacional 2020 del INEI (hojas Léame y Supuestos)"

DATASETS: tuple[Dataset, ...] = (
    Dataset("DS01", "ds01_catalogo_eps", "Catálogo de EPS", ("cod_eps",), (
        C("cod_eps", "texto", "-"),
        C("nombre_eps", "texto", "-"),
        C("tamano", "texto", "-"),
        C("macrorregion", "texto", "-", "real", REAL_INEI),
        C("departamento", "texto", "-", "real", REAL_INEI),
        C("ubigeo_sede", "texto", "-", "real", REAL_INEI),
        C("n_localidades", "entero", "localidades"),
        C("conexiones_agua", "entero", "conexiones"),
        C("conexiones_alcantarillado", "entero", "conexiones"),
        C("poblacion_servida", "entero", "habitantes", "estimado", EST_POB),
        C("regimen", "texto", "-"),
        C("fecha_ingreso_rat", "fecha", "-"),
        C("periodo_regulatorio_inicio", "entero", "año"),
        C("periodo_regulatorio_fin", "entero", "año"),
        C("resolucion_estudio_vigente", "texto", "-"),
        C("fecha_resolucion_vigente", "fecha", "-"),
    )),
    Dataset("DS01", "ds01_localidades_eps", "Localidades atendidas por cada EPS", ("cod_eps", "ubigeo"), (
        C("cod_eps", "texto", "-"),
        C("localidad", "texto", "-", "real", REAL_INEI),
        C("ubigeo", "texto", "-", "real", REAL_INEI),
        C("departamento", "texto", "-", "real", REAL_INEI),
        C("provincia", "texto", "-", "real", REAL_INEI),
        C("distrito", "texto", "-", "real", REAL_INEI),
        C("es_sede", "booleano", "-"),
        C("poblacion_servida", "entero", "habitantes", "estimado", EST_POB),
        C("conexiones_agua", "entero", "conexiones"),
        C("conexiones_alcantarillado", "entero", "conexiones"),
    )),
    Dataset("DS02", "ds02_procedimientos", "Procedimientos (expedientes)", ("id_expediente",), (
        C("id_expediente", "texto", "-"),
        C("cod_eps", "texto", "-"),
        C("tipo_procedimiento", "texto", "-"),
        C("base_normativa", "texto", "-"),
        C("origen", "texto", "-"),
        C("periodo_regulatorio", "texto", "-"),
        C("periodo_reportado", "texto", "-"),
        C("fecha_inicio", "fecha", "-"),
        C("plazo_maximo_dh", "entero", "días hábiles"),
        C("dias_suspension_dh", "entero", "días hábiles"),
        C("dias_habiles_sunass", "entero", "días hábiles"),
        C("fecha_limite", "fecha", "-"),
        C("estado", "texto", "-"),
        C("etapa_actual", "texto", "-"),
        C("hito_actual", "texto", "-"),
        C("responsable_actual", "texto", "-"),
        C("resultado", "texto", "-"),
        C("fecha_conclusion", "fecha", "-"),
        C("documento_final", "texto", "-"),
        C("cod_proyecto", "texto", "-"),
        C("motivo", "texto", "-"),
        C("monto_solicitado", "decimal", "S/"),
        C("monto_aprobado", "decimal", "S/"),
        C("porcentaje_previsto", "decimal", "%"),
        C("porcentaje_aprobado", "decimal", "%"),
        C("indicador_cumplimiento", "decimal", "%"),
        C("fecha_presentacion", "fecha", "-"),
    )),
    Dataset("DS02", "ds02_hitos_procedimientos", "Hitos de cada expediente", ("id_expediente", "nro_hito"), (
        C("id_expediente", "texto", "-"),
        C("nro_hito", "entero", "-"),
        C("etapa", "texto", "-"),
        C("plazo_etapa_dh", "entero", "días hábiles"),
        C("hito", "texto", "-"),
        C("descripcion", "texto", "-"),
        C("responsable", "texto", "-"),
        C("fecha_inicio", "fecha", "-"),
        C("fecha_fin", "fecha", "-"),
        C("plazo_referencial_dh", "entero", "días hábiles"),
        C("cuenta_plazo", "booleano", "-"),
        C("documento", "texto", "-"),
    )),
    Dataset("DS03", "ds03_programa_inversiones", "Programa de inversiones (proyecto/año)",
            ("cod_proyecto", "periodo_regulatorio", "anio"), (
        C("cod_eps", "texto", "-"),
        C("periodo_regulatorio", "texto", "-"),
        C("tipo_periodo", "texto", "-"),
        C("cod_proyecto", "texto", "-"),
        C("cui", "entero", "-"),
        C("nombre_proyecto", "texto", "-"),
        C("tipo_inversion", "texto", "-"),
        C("componente", "texto", "-"),
        C("localidad", "texto", "-"),
        C("ubigeo", "texto", "-", "real", REAL_INEI),
        C("fuente_financiamiento", "texto", "-"),
        C("meta_asociada", "texto", "-"),
        C("poblacion_beneficiaria", "entero", "habitantes", "estimado", "Estimada (hoja ds03_programa_inversiones)"),
        C("anio", "entero", "año"),
        C("monto_programado_original", "decimal", "S/"),
        C("monto_programado_vigente", "decimal", "S/"),
        C("id_expediente_modificacion", "texto", "-"),
    )),
    Dataset("DS04", "ds04_ejecucion_inversiones", "Ejecución de inversiones (proyecto/trimestre)",
            ("cod_proyecto", "anio_trimestre"), (
        C("cod_eps", "texto", "-"),
        C("cod_proyecto", "texto", "-"),
        C("anio_trimestre", "texto", "-"),
        C("estado", "texto", "-"),
        C("avance_fisico_acumulado_pct", "decimal", "%"),
        C("ejecucion_financiera_trimestre", "decimal", "S/"),
        C("ejecucion_financiera_acumulada", "decimal", "S/"),
        C("fecha_reporte", "fecha", "-"),
    )),
    Dataset("DS05", "ds05_fondo_inversiones_reservas", "Fondo de inversiones y reservas (EPS/mes/fondo)",
            ("cod_eps", "anio_mes", "tipo_fondo"), (
        C("cod_eps", "texto", "-"),
        C("anio_mes", "texto", "-"),
        C("tipo_fondo", "texto", "-"),
        C("porcentaje_ingresos", "decimal", "%"),
        C("ingresos_base_mes", "decimal", "S/"),
        C("saldo_inicial", "decimal", "S/"),
        C("deposito_programado", "decimal", "S/"),
        C("deposito_efectuado", "decimal", "S/"),
        C("intereses", "decimal", "S/"),
        C("uso_programado", "decimal", "S/"),
        C("uso_ejecutado", "decimal", "S/"),
        C("uso_excepcional", "decimal", "S/"),
        C("id_expediente_uso_excepcional", "texto", "-"),
        C("saldo_final", "decimal", "S/"),
        C("fecha_reporte", "fecha", "-"),
    )),
    Dataset("DS06", "ds06_estados_financieros", "Estados financieros e indicadores (EPS/año)", ("cod_eps", "anio"), (
        C("cod_eps", "texto", "-"),
        C("anio", "entero", "año"),
        C("estado_presentacion", "texto", "-"),
        C("fecha_presentacion", "fecha", "-"),
        C("estados_auditados", "texto", "-"),
        C("ingresos_operativos", "entero", "S/"),
        C("costo_ventas", "entero", "S/"),
        C("gastos_administracion", "entero", "S/"),
        C("gastos_ventas", "entero", "S/"),
        C("depreciacion_amortizacion", "entero", "S/"),
        C("resultado_operativo", "entero", "S/"),
        C("ingresos_financieros", "entero", "S/"),
        C("gastos_financieros", "entero", "S/"),
        C("impuesto_renta", "entero", "S/"),
        C("resultado_neto", "entero", "S/"),
        C("efectivo_libre_disponibilidad", "entero", "S/"),
        C("efectivo_restringido_fondos", "entero", "S/"),
        C("cuentas_por_cobrar_comerciales", "entero", "S/"),
        C("activo_corriente", "entero", "S/"),
        C("activo_no_corriente", "entero", "S/"),
        C("activo_total", "entero", "S/"),
        C("pasivo_corriente", "entero", "S/"),
        C("pasivo_no_corriente", "entero", "S/"),
        C("pasivo_total", "entero", "S/"),
        C("patrimonio", "entero", "S/"),
        C("facturacion_servicios", "entero", "S/"),
        C("recaudacion", "entero", "S/"),
        C("margen_operativo_pct", "decimal", "%"),
        C("relacion_trabajo_pct", "decimal", "%"),
        C("liquidez_corriente", "decimal", "veces"),
        C("endeudamiento", "decimal", "veces"),
        C("morosidad_pct", "decimal", "%"),
        C("eficiencia_cobranza_pct", "decimal", "%"),
    )),
    Dataset("DS07", "ds07_metas_gestion", "Metas de gestión (EPS/meta/año)",
            ("cod_eps", "periodo_regulatorio", "cod_meta", "ubigeo", "anio"), (
        C("cod_eps", "texto", "-"),
        C("periodo_regulatorio", "texto", "-"),
        C("cod_meta", "texto", "-"),
        C("nombre_meta", "texto", "-"),
        C("nivel", "texto", "-"),
        C("localidad", "texto", "-", "real", REAL_INEI),
        C("ubigeo", "texto", "-", "real", REAL_INEI),
        C("unidad", "texto", "-"),
        C("sentido", "texto", "-"),
        C("condiciona_incremento", "booleano", "-"),
        C("anio_regulatorio", "entero", "-"),
        C("anio", "entero", "año"),
        C("valor_base", "decimal", "unidad"),
        C("valor_meta", "decimal", "unidad"),
        C("valor_alcanzado", "decimal", "unidad"),
        C("cumplimiento_pct", "decimal", "%"),
        C("fuente", "texto", "-"),
    )),
    Dataset("DS08", "ds08_inversiones_mef", "Inversiones registradas en el MEF (simulado)", ("cui",), (
        C("cui", "entero", "-"),
        C("nombre_inversion", "texto", "-"),
        C("entidad", "texto", "-"),
        C("tipo_inversion", "texto", "-"),
        C("estado_inversion", "texto", "-"),
        C("fecha_viabilidad", "fecha", "-"),
        C("monto_viable", "decimal", "S/"),
        C("costo_actualizado", "decimal", "S/"),
        C("devengado_acumulado", "decimal", "S/"),
        C("pim_2026", "decimal", "S/"),
        C("devengado_2026", "decimal", "S/"),
        C("avance_fisico_pct", "decimal", "%"),
        C("fecha_ultima_actualizacion", "fecha", "-"),
    )),
    Dataset("DS09", "ds09_ipm", "Índice de precios al por mayor (INEI)", ("anio_mes",), (
        C("anio_mes", "texto", "-", "real", "INEI vía BCRPData, serie PN01286PM"),
        C("variacion_mensual_pct", "decimal", "%", "real", "Dato real (INEI vía BCRPData, serie PN01286PM)"),
        C("indice_base_dic2020", "decimal", "índice", "real", "Calculado por el comité a partir de la variación mensual real"),
        C("variacion_12m_pct", "decimal", "%", "real", "Calculada por el comité a partir de la variación mensual real"),
        C("fecha_publicacion", "fecha", "-", "estimado", "Fecha aproximada: primer día hábil del mes siguiente"),
        C("fuente", "texto", "-", "real"),
    )),
)

POR_NOMBRE: dict[str, Dataset] = {d.nombre: d for d in DATASETS}


def dataset(nombre: str) -> Dataset:
    return POR_NOMBRE[nombre]


def naturaleza_dataset(ds: Dataset) -> str:
    """Rótulo general del dataset para la interfaz."""
    if ds.codigo == "DS09":
        return "real"
    return "sintético"
