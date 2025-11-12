from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from asistencia.models import Estudiante, Asistencia


class Command(BaseCommand):
    help = 'Marca como falta a estudiantes que no tengan registro de asistencia en la fecha indicada (por defecto hoy).'

    def add_arguments(self, parser):
        parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD. Por defecto hoy.')
        parser.add_argument('--periodo', type=int, help='Periodo (año escolar) para filtrar estudiantes', default=None)

    def handle(self, *args, **options):
        fecha_arg = options.get('fecha')
        periodo = options.get('periodo')

        if fecha_arg:
            fecha = datetime.strptime(fecha_arg, '%Y-%m-%d').date()
        else:
            fecha = timezone.now().date()

        qs = Estudiante.objects.all()
        if periodo:
            qs = qs.filter(periodo=periodo)

        total = 0
        marcadas = 0
        for est in qs:
            total += 1
            # Si ya existe alguna asistencia para la fecha indicada, no marcar falta
            if Asistencia.objects.filter(estudiante=est, fecha=fecha).exists():
                continue
            # Crear la falta usando la misma fecha (no confiar en auto_now_add para consistencia)
            Asistencia.objects.create(estudiante=est, fecha=fecha, hora=timezone.now().time(), estado='falta')
            marcadas += 1
            # NOTE: removed verbose debug prints; use logging in production if needed

        self.stdout.write(self.style.SUCCESS(f'Proceso terminado. Estudiantes revisados: {total}, faltas registradas: {marcadas}'))
