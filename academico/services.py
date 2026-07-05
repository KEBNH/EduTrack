from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import calendar as calendar_module

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Avg

from accounts.models import CustomUser
from accounts.validators import validar_celular_obligatorio

from .models import (
    Alerta,
    Alumno,
    Apoderado,
    Asistencia,
    Curso,
    Matricula,
    MatriculaCurso,
    Nota,
)

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


@transaction.atomic
def asignar_matriculas_activas(curso):
    if not curso.activo:
        return

    matriculas = Matricula.objects.filter(
        institucion=curso.institucion,
        grado=curso.grado,
        estado=Matricula.Estado.ACTIVA,
    )
    existentes = set(
        MatriculaCurso.objects.filter(curso=curso).values_list(
            "matricula_id", flat=True
        )
    )
    MatriculaCurso.objects.bulk_create(
        [
            MatriculaCurso(
                institucion=curso.institucion,
                matricula=matricula,
                curso=curso,
            )
            for matricula in matriculas
            if matricula.pk not in existentes
        ]
    )


@dataclass(frozen=True)
class ResultadoInscripcion:
    usuario: CustomUser
    apoderado: Apoderado
    alumno: Alumno
    matricula: Matricula
    alumno_creado: bool
    apoderado_creado: bool
    matricula_creada: bool


def _validar_usuario_apoderado(usuario, institucion):
    if usuario.rol != CustomUser.Rol.APODERADO:
        raise ValidationError("El usuario seleccionado no tiene rol Padre/Apoderado.")
    if usuario.institucion_id != institucion.id:
        raise ValidationError(
            "El usuario seleccionado pertenece a otra institucion."
        )
    if not usuario.is_active:
        raise ValidationError("El usuario seleccionado esta inactivo.")
    validar_celular_obligatorio(usuario.celular)


def _datos_perfil_apoderado(usuario):
    return {
        "nombres": usuario.first_name,
        "apellidos": usuario.last_name,
        "celular": usuario.celular,
        "correo": usuario.email,
        "activo": True,
    }


def _actualizar_perfil_apoderado(apoderado, usuario):
    apoderado.usuario = usuario
    apoderado.dni = usuario.dni
    for campo, valor in _datos_perfil_apoderado(usuario).items():
        setattr(apoderado, campo, valor)
    apoderado.save(
        update_fields=(
            "usuario",
            "dni",
            "nombres",
            "apellidos",
            "celular",
            "correo",
            "activo",
            "fmodificacion",
        )
    )


def _crear_o_actualizar_perfil_apoderado(*, usuario, institucion):
    _validar_usuario_apoderado(usuario, institucion)

    try:
        apoderado = usuario.perfil_apoderado
    except Apoderado.DoesNotExist:
        apoderado = None

    if apoderado:
        if apoderado.institucion_id != institucion.id:
            raise ValidationError(
                "El perfil del apoderado pertenece a otra institucion."
            )
        _actualizar_perfil_apoderado(apoderado, usuario)
        return apoderado, False

    apoderado = Apoderado.objects.filter(
        institucion=institucion,
        dni=usuario.dni,
    ).first()
    if apoderado:
        if apoderado.usuario_id and apoderado.usuario_id != usuario.id:
            raise ValidationError(
                "El perfil del apoderado esta vinculado a otro usuario."
            )
        _actualizar_perfil_apoderado(apoderado, usuario)
        return apoderado, False

    return Apoderado.objects.create(
        institucion=institucion,
        usuario=usuario,
        dni=usuario.dni,
        parentesco=Apoderado.Parentesco.OTRO,
        **_datos_perfil_apoderado(usuario),
    ), True


@transaction.atomic
def registrar_inscripcion(*, usuario_actual, datos):
    if (
        not usuario_actual.is_authenticated
        or not usuario_actual.is_active
        or usuario_actual.rol != CustomUser.Rol.PERSONAL_ACADEMICO
        or usuario_actual.institucion_id is None
    ):
        raise PermissionDenied("No tiene permiso para registrar inscripciones.")

    institucion = usuario_actual.institucion
    grado = datos["grado"]
    if grado.institucion_id != institucion.id or not grado.activo:
        raise ValidationError("El grado seleccionado no esta disponible.")

    usuario = datos["apoderado_usuario"]
    apoderado, apoderado_creado = _crear_o_actualizar_perfil_apoderado(
        usuario=usuario,
        institucion=institucion,
    )

    alumno, alumno_creado = Alumno.objects.get_or_create(
        institucion=institucion,
        dni=datos["alumno_dni"],
        defaults={
            "nombres": datos["alumno_nombres"],
            "apellidos": datos["alumno_apellidos"],
            "fecha_nacimiento": datos["alumno_fecha_nacimiento"],
            "activo": True,
        },
    )
    if not alumno_creado:
        alumno.nombres = datos["alumno_nombres"]
        alumno.apellidos = datos["alumno_apellidos"]
        alumno.fecha_nacimiento = datos["alumno_fecha_nacimiento"]
        alumno.activo = True
        alumno.save(
            update_fields=(
                "nombres",
                "apellidos",
                "fecha_nacimiento",
                "activo",
                "fmodificacion",
            )
        )

    apoderado.alumnos.add(alumno)

    matricula = Matricula.objects.filter(
        institucion=institucion,
        alumno=alumno,
        anio_academico=grado.anio_academico,
    ).first()
    if matricula:
        if matricula.grado_id != grado.id:
            raise ValidationError(
                "El alumno ya tiene una matricula para este anio academico."
            )
        matricula_creada = False
    else:
        matricula = Matricula.objects.create(
            institucion=institucion,
            alumno=alumno,
            grado=grado,
            estado=Matricula.Estado.ACTIVA,
        )
        asignar_cursos_activos(matricula)
        matricula_creada = True

    return ResultadoInscripcion(
        usuario=usuario,
        apoderado=apoderado,
        alumno=alumno,
        matricula=matricula,
        alumno_creado=alumno_creado,
        apoderado_creado=apoderado_creado,
        matricula_creada=matricula_creada,
    )

def obtener_bimestre(fecha=None):
    fecha = fecha or date.today()
    for numero, inicio, fin in BIMESTRES:
        fecha_inicio = date(fecha.year, inicio[0], inicio[1])
        fecha_fin = date(fecha.year, fin[0], fin[1])
        if fecha_inicio <= fecha <= fecha_fin:
            return numero, fecha_inicio, fecha_fin
    return None

def obtener_rango_bimestre(anio, numero):
    for num, inicio, fin in BIMESTRES:
        if num == numero:
            return date(anio, *inicio), date(anio, *fin)
    return None


def anios_disponibles_alumno(alumno):
    return list(
        Matricula.objects.filter(alumno=alumno)
        .order_by("-anio_academico")
        .values_list("anio_academico", flat=True)
        .distinct()
    )

def clasificar_riesgo_asistencia(porcentaje_faltas):
    if porcentaje_faltas > Decimal("20"):
        return Alerta.NivelRiesgo.ALTO
    if porcentaje_faltas >= Decimal("10"):
        return Alerta.NivelRiesgo.MEDIO
    return Alerta.NivelRiesgo.BAJO


def clasificar_riesgo_rendimiento(promedio):
    if promedio < Decimal("13"):
        return Alerta.NivelRiesgo.ALTO
    if promedio <= Decimal("14"):
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
        return None

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

def notas_por_bimestre(alumno, anio, numero_bimestre):
    matricula = Matricula.objects.filter(
        alumno=alumno, anio_academico=anio
    ).first()
    if not matricula:
        return []

    notas = (
        Nota.objects.filter(
            matricula_curso__matricula=matricula,
            periodo=str(numero_bimestre),
        )
        .select_related("matricula_curso__curso")
        .order_by("matricula_curso__curso__nombre", "evaluacion")
    )

    cursos = {}
    for nota in notas:
        curso = nota.matricula_curso.curso
        cursos.setdefault(curso, []).append(nota)

    resultado = []
    for curso, notas_curso in cursos.items():
        promedio = sum(n.calificacion for n in notas_curso) / len(notas_curso)
        resultado.append({"curso": curso, "notas": notas_curso, "promedio": promedio})

    return resultado

def calendario_asistencia_bimestre(alumno, anio, numero_bimestre):
    rango = obtener_rango_bimestre(anio, numero_bimestre)
    if not rango:
        return []

    fecha_inicio, fecha_fin = rango
    matricula = Matricula.objects.filter(alumno=alumno, anio_academico=anio).first()
    if not matricula:
        return []

    asistencias = Asistencia.objects.filter(
        matricula_curso__matricula=matricula,
        fecha__range=(fecha_inicio, fecha_fin),
    ).select_related("matricula_curso__curso")

    estado_por_dia = {}
    for asistencia in asistencias:
        dia = asistencia.fecha
        if asistencia.estado == Asistencia.Estado.FALTA:
            estado_por_dia[dia] = "FALTA"
        elif dia not in estado_por_dia:
            estado_por_dia[dia] = "PRESENTE"

    meses = []
    mes_actual = fecha_inicio.replace(day=1)
    while mes_actual <= fecha_fin:
        _, dias_en_mes = calendar_module.monthrange(mes_actual.year, mes_actual.month)
        semanas = []
        cal = calendar_module.Calendar(firstweekday=0)
        for semana in cal.monthdayscalendar(mes_actual.year, mes_actual.month):
            fila = []
            for dia_num in semana:
                if dia_num == 0:
                    fila.append(None)
                    continue
                fecha_dia = date(mes_actual.year, mes_actual.month, dia_num)
                if fecha_dia < fecha_inicio or fecha_dia > fecha_fin:
                    fila.append({"dia": dia_num, "fuera_de_rango": True})
                elif fecha_dia.weekday() >= 5:
                    fila.append({"dia": dia_num, "fin_de_semana": True})
                else:
                    fila.append(
                        {
                            "dia": dia_num,
                            "estado": estado_por_dia.get(fecha_dia),
                        }
                    )
            semanas.append(fila)
        meses.append(
            {
                "nombre": calendar_module.month_name[mes_actual.month],
                "anio": mes_actual.year,
                "semanas": semanas,
            }
        )
        if mes_actual.month == 12:
            mes_actual = mes_actual.replace(year=mes_actual.year + 1, month=1)
        else:
            mes_actual = mes_actual.replace(month=mes_actual.month + 1)

    return meses
