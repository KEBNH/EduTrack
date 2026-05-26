# Estructura Frontend y Backend

El repositorio esta separado fisicamente en dos carpetas principales:

```text
EduTrack/
+-- backend/        # Django, modelos, vistas, rutas, base de datos y dependencias
+-- frontend/       # Templates HTML, CSS, JavaScript, imagenes, fuentes y assets
+-- .github/        # Automatizaciones CI/CD
+-- Dockerfile      # Configuracion del contenedor para despliegue
`-- README.md
```

## Backend

La carpeta `backend/` contiene la logica del sistema:

- `backend/EduTrackApp/`: configuracion principal del proyecto Django.
- `backend/academico/`: app academica con modelos, vistas, rutas y admin.
- `backend/manage.py`: comando principal para ejecutar tareas Django.
- `backend/requirements.txt`: dependencias Python.
- `backend/db.sqlite3`: base de datos local de desarrollo.

## Frontend

La carpeta `frontend/` contiene lo que el usuario ve en el navegador:

- `frontend/templates/`: paginas HTML renderizadas por Django.
- `frontend/static/`: CSS, JavaScript, imagenes, iconos, fuentes y assets.

## Infraestructura

Los archivos de infraestructura quedan en la raiz:

- `Dockerfile`: define como ejecutar la aplicacion en contenedor.
- `.github/workflows/ci.yml`: ejecuta pruebas y despliegue hacia Render.

## Como corre Django ahora

Desde la raiz del repositorio:

```bash
python backend/manage.py runserver
```

Desde la carpeta `backend/`:

```bash
python manage.py runserver
```
