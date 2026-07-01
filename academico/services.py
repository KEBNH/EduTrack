from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg

from .models import Alerta, Asistencia, Curso, Matricula, MatriculaCurso, Nota

BIMESTRES = (
    (1, (3, 1), (4, 30)),
    (2, (5, 1), (7, 15)),
    (3, (8, 1), (10, 15)),
    (4, (10, 16), (12, 20)),
)

ORDEN_RIESGO = {
    Alerta.NivelRiesgo.BAJO: 1,
    Alerta.NivelRiesgo.MEDIO: 2,
    Alerta.NivelRiesgo.ALTO: 3,
}


@dataclass(frozen=True)
class ResultadoRiesgo:
    nivel: str
    valor: Decimal
    descripcion: str


@transaction.atomic
def asignar_cursos_activos(matricula):
    cursos = Curso.objects.filter(
        institucion=matricula.institucion,
        grado=matricula.grado,
        activo=True,
    )
    existentes = set(
        MatriculaCurso.objects.filter(matricula=matricula).values_list(
            "curso_id", flat=True
        )
    )
    MatriculaCurso.objects.bulk_create(
        [
            MatriculaCurso(
                institucion=matricula.institucion,
                matricula=matricula,
                curso=curso,
            )
            for curso in cursos
            if curso.pk not in existentes
        ]
    )


def obtener_bimestre(fecha=None):
    fecha = fecha or date.today()
    for numero, inicio, fin in BIMESTRES:
        fecha_inicio = date(fecha.year, inicio[0], inicio[1])
        fecha_fin = date(fecha.year, fin[0], fin[1])
        if fecha_inicio <= fecha <= fecha_fin:
            return numero, fecha_inicio, fecha_fin
    return None

def clasificar_riesgo_asistencia(porcentaje_faltas):
    if porcentaje_faltas > Decimal("20"):
        return Alerta.NivelRiesgo.ALTO
    if porcentaje_faltas >= Decimal("10"):
        return Alerta.NivelRiesgo.MEDIO
    return Alerta.NivelRiesgo.BAJO


def clasificar_riesgo_rendimiento(promedio):
    if promedio < Decimal("13"):
        return Alerta.NivelRiesgo.ALTO
    if promedio < Decimal("15"):
        return Alerta.NivelRiesgo.MEDIO
    return Alerta.NivelRiesgo.BAJO


def calcular_riesgo_asistencia(alumno, fecha=None):
    bimestre = obtener_bimestre(fecha)
    if not bimestre:
        return None

    numero_bimestre, fecha_inicio, fecha_fin = bimestre
    asistencias = Asistencia.objects.filter(
        matricula_curso__matricula__alumno=alumno,
        matricula_curso__matricula__estado=Matricula.Estado.ACTIVA,
        fecha__range=(fecha_inicio, fecha_fin),
    )

    total_clases = asistencias.count()
    total_faltas = asistencias.filter(estado=Asistencia.Estado.FALTA).count()

    if total_clases == 0:
        porcentaje = Decimal("0")
    else:
        porcentaje = (Decimal(total_faltas) * Decimal("100")) / Decimal(total_clases)

    nivel = clasificar_riesgo_asistencia(porcentaje)
    descripcion = (
        f"Bimestre {numero_bimestre}: {total_faltas} faltas de "
        f"{total_clases} clases registradas ({porcentaje:.2f}% de faltas)."
    )
    return ResultadoRiesgo(nivel=nivel, valor=porcentaje, descripcion=descripcion)

def calcular_riesgo_rendimiento(alumno, fecha=None):
    bimestre = obtener_bimestre(fecha)
    if not bimestre:
        return None

    numero_bimestre, _, _ = bimestre
    promedios_por_curso = (
        Nota.objects.filter(
            matricula_curso__matricula__alumno=alumno,
            matricula_curso__matricula__estado=Matricula.Estado.ACTIVA,
            periodo=str(numero_bimestre),
        )
        .values("matricula_curso")
        .annotate(promedio_curso=Avg("calificacion"))
    )

    promedios = [
        registro["promedio_curso"]
        for registro in promedios_por_curso
        if registro["promedio_curso"] is not None
    ]

    if not promedios:
        promedio_general = Decimal("20")
        cursos_evaluados = 0
    else:
        promedio_general = sum(promedios, Decimal("0")) / Decimal(len(promedios))
        cursos_evaluados = len(promedios)

    nivel = clasificar_riesgo_rendimiento(promedio_general)
    descripcion = (
        f"Bimestre {numero_bimestre}: promedio general {promedio_general:.2f} "
        f"calculado sobre {cursos_evaluados} cursos evaluados."
    )
    return ResultadoRiesgo(
        nivel=nivel,
        valor=promedio_general,
        descripcion=descripcion,
    )


def peor_nivel(*niveles):
    niveles_validos = [nivel for nivel in niveles if nivel]
    if not niveles_validos:
        return Alerta.NivelRiesgo.BAJO
    return max(niveles_validos, key=lambda nivel: ORDEN_RIESGO[nivel])


def sincronizar_alerta(alumno, tipo, resultado):
    alertas_activas = Alerta.objects.filter(
        alumno=alumno,
        tipo=tipo,
        activa=True,
    ).order_by("pk")

    alerta = alertas_activas.first()
    alertas_activas.exclude(pk=getattr(alerta, "pk", None)).update(activa=False)

    if resultado is None or resultado.nivel == Alerta.NivelRiesgo.BAJO:
        if alerta:
            alerta.activa = False
            alerta.descripcion = resultado.descripcion if resultado else alerta.descripcion
            alerta.nivel_riesgo = (
                resultado.nivel if resultado else alerta.nivel_riesgo
            )
            alerta.save(update_fields=("activa", "descripcion", "nivel_riesgo", "fmodificacion"))
        return None

    if alerta is None:
        return Alerta.objects.create(
            institucion=alumno.institucion,
            alumno=alumno,
            tipo=tipo,
            nivel_riesgo=resultado.nivel,
            descripcion=resultado.descripcion,
        )

    alerta.nivel_riesgo = resultado.nivel
    alerta.descripcion = resultado.descripcion
    alerta.save(update_fields=("nivel_riesgo", "descripcion", "fmodificacion"))
    return alerta

@transaction.atomic
def generar_alertas_sat(fecha=None):
    bimestre = obtener_bimestre(fecha)
    if not bimestre:
        return {
            "procesados": 0,
            "alertas_activas": 0,
            "cerradas": 0,
            "fuera_de_periodo": True,
        }

    alumnos = (
        Matricula.objects.filter(estado=Matricula.Estado.ACTIVA)
        .select_related("alumno", "institucion")
        .values_list("alumno_id", flat=True)
        .distinct()
    )

    procesados = 0
    alertas_activas = 0

    from .models import Alumno

    for alumno in Alumno.objects.filter(pk__in=alumnos, activo=True):
        procesados += 1

        resultado_asistencia = calcular_riesgo_asistencia(alumno, fecha)
        resultado_rendimiento = calcular_riesgo_rendimiento(alumno, fecha)

        alerta_asistencia = sincronizar_alerta(
            alumno,
            Alerta.Tipo.ASISTENCIA,
            resultado_asistencia,
        )
        alerta_rendimiento = sincronizar_alerta(
            alumno,
            Alerta.Tipo.RENDIMIENTO,
            resultado_rendimiento,
        )

        alertas_activas += int(alerta_asistencia is not None)
        alertas_activas += int(alerta_rendimiento is not None)

        peor_nivel(
            resultado_asistencia.nivel if resultado_asistencia else None,
            resultado_rendimiento.nivel if resultado_rendimiento else None,
        )

    return {
        "procesados": procesados,
        "alertas_activas": alertas_activas,
        "cerradas": None,
        "fuera_de_periodo": False,
    }
