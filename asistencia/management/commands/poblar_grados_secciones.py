from django.core.management.base import BaseCommand
from asistencia.models import Grado, Seccion

class Command(BaseCommand):
    help = 'Crea grados (1ro a 5to) y secciones (A, B, C, D) automáticamente'

    def handle(self, *args, **options):
        grados = ['1ro', '2do', '3ro', '4to', '5to']
        secciones = ['A', 'B', 'C', 'D']
        creados = 0
        for grado_nombre in grados:
            grado, created = Grado.objects.get_or_create(nombre=grado_nombre)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Grado creado: {grado_nombre}'))
            for seccion_nombre in secciones:
                seccion, sec_created = Seccion.objects.get_or_create(nombre=seccion_nombre, grado=grado)
                if sec_created:
                    creados += 1
                    self.stdout.write(self.style.SUCCESS(f'  Sección creada: {seccion_nombre} para {grado_nombre}'))
        self.stdout.write(self.style.SUCCESS(f'Total de secciones creadas: {creados}'))
