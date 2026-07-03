from datetime import date
from django.core.management.base import BaseCommand, CommandError
from academico.services import generar_alertas_sat

class Command(BaseCommand):
    help = "Genera alertas SAT por asistencia y rendimiento academico."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fecha",
            help=(
                "Fecha de referencia en formato YYYY-MM-DD. "
                "Si no se indica, usa la fecha actual."
            ),
        )

    def handle(self, *args, **options):
        fecha_texto = options.get("fecha")
        fecha = None

        if fecha_texto:
            try:
                fecha = date.fromisoformat(fecha_texto)
            except ValueError as exc:
                raise CommandError("La fecha debe tener formato YYYY-MM-DD.") from exc

        resultado = generar_alertas_sat(fecha=fecha)

        if resultado["fuera_de_periodo"]:
            self.stdout.write(
                self.style.WARNING(
                    "No se generaron alertas porque la fecha esta fuera del anio escolar activo."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Motor SAT ejecutado correctamente: "
                f"{resultado['procesados']} alumnos procesados, "
                f"{resultado['alertas_activas']} alertas activas generadas o actualizadas."
            )
        )