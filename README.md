# EduTrack

## Sistema de Alerta Temprana (SAT) para la Prevención de la Deserción Escolar en el Perú

EduTrack es una plataforma académica orientada a detectar tempranamente estudiantes en riesgo de deserción escolar mediante el seguimiento de asistencia, rendimiento académico y alertas institucionales.

![Status](https://img.shields.io/badge/status-en%20desarrollo-orange)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-5.x-green)
![License](https://img.shields.io/badge/license-Academic-lightgrey)

## Descripción

El proyecto busca apoyar a instituciones educativas en la identificación oportuna de señales de riesgo escolar. La plataforma centraliza información académica, permite registrar asistencia y calificaciones, genera alertas SAT y ofrece reportes para la toma de decisiones.

El enfoque principal es preventivo: facilitar que directores, docentes, personal académico y apoderados cuenten con información clara para actuar antes de que el riesgo avance.

## Objetivos

- Detectar patrones de riesgo escolar.
- Centralizar información académica institucional.
- Generar alertas tempranas por asistencia y rendimiento.
- Facilitar el seguimiento académico de estudiantes.
- Brindar información útil a directores, docentes, personal académico, MINEDU y apoderados.
- Proteger la privacidad de los estudiantes mediante control de acceso por roles.

## Funcionalidades actuales

- Landing pública con acceso al sistema.
- Login seguro con autenticación por correo.
- Gestión de usuarios por roles.
- Activación de cuentas por correo.
- Registro de instituciones.
- Registro y gestión de alumnos.
- Registro y gestión de apoderados.
- Inscripción y matrícula de estudiantes.
- Gestión de grados y cursos.
- Asignación de profesores y tutores.
- Registro de asistencia.
- Registro de notas.
- Generación de alertas SAT por asistencia y rendimiento.
- Panel de alertas activas.
- Portal para apoderados.
- Reporte institucional para directores.
- Reporte nacional para MINEDU.
- Pruebas automatizadas y pipeline CI/CD.

## Próximamente

- Planes de intervención por estudiante.
- Registro de reuniones con apoderados.
- Seguimiento tutorial o psicológico.
- Historial detallado de acciones por caso.
- Notificaciones automatizadas.
- Páginas personalizadas de error para producción.

## Roles del sistema

| Rol | Alcance principal |
|---|---|
| IT / Soporte Técnico | Gestión administrativa de usuarios y soporte del sistema. |
| MINEDU | Consulta de reportes agregados y vista nacional. |
| Director | Seguimiento institucional, reportes y alertas. |
| Profesor | Registro académico y consulta de estudiantes asignados. |
| Personal Académico | Gestión de inscripciones, alumnos, apoderados y matrículas. |
| Padre/Apoderado | Consulta del portal del estudiante asociado. |

## Tecnologías utilizadas

| Tecnología | Propósito |
|---|---|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) | Desarrollo backend y lógica del sistema. |
| ![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white) | Framework web principal. |
| ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white) | Base de datos local de desarrollo. |
| ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white) | Base de datos preparada para despliegue mediante `DATABASE_URL`. |
| ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white) | Integración continua, pruebas y despliegue. |
| ![OWASP ZAP](https://img.shields.io/badge/OWASP_ZAP-00549E?style=for-the-badge&logo=owasp&logoColor=white) | Escaneo DAST baseline en CI/CD. |

## Requisitos

- Python 3.11
- pip
- Entorno virtual recomendado

Verificar la versión de Python:

```bash
python --version
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar migraciones:

```bash
python manage.py migrate
```

Iniciar el servidor local:

```bash
python manage.py runserver
```

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Landing pública. |
| `/accounts/login/` | Inicio de sesión. |
| `/dashboard/` | Panel principal protegido. |
| `/academico/` | Módulo académico protegido. |
| `/admin/` | Administración Django. |

## Calidad y seguridad

El proyecto incluye validaciones de seguridad y calidad dentro del pipeline:

- `python manage.py check`
- Pruebas automatizadas con coverage.
- Análisis con Bandit.
- DAST baseline con OWASP ZAP.
- Smoke tests sobre el login en ambiente de desarrollo.

Ejecutar pruebas localmente:

```bash
python manage.py test
```

## Casos de uso

- Identificar estudiantes con riesgo académico.
- Detectar inasistencias frecuentes.
- Generar alertas tempranas.
- Consultar reportes institucionales.
- Consultar reportes nacionales agregados.
- Facilitar el acceso de apoderados a información relevante del estudiante.

## Dream Team

<div align="center">

| Integrante | Rol |
|---|---|
| <img src="https://github.com/KEBNH.png" width="100px"><br><b>Kevin Luis Moreyra Ivarra</b> | Backend/Frontend |
| <img src="https://github.com/lelegarel.png" width="100px"><br><b>Leonardo Gonzales Urbina</b> | Backend/Frontend |
| <img src="https://github.com/SnackyT.png" width="100px"><br><b>Mauricio Garcia Garay</b> | Frontend |
| <img src="https://github.com/Miminki.png" width="100px"><br><b>Pamela Estacio Ascencio</b> | Frontend |
| <img src="https://github.com/Sushi-milki.png" width="100px"><br><b>Angie Almeida Pedraza</b> | Frontend |

</div>
