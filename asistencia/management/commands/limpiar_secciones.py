from django.core.management.base import BaseCommand
from asistencia.models import Grado, Seccion

class Command(BaseCommand):
    help = 'Elimina secciones duplicadas y deja solo A, B, C, D por cada grado'

    def handle(self, *args, **options):
        secciones_validas = ['A', 'B', 'C', 'D']
        grados = Grado.objects.all()
        total_eliminadas = 0
        for grado in grados:
            for nombre in secciones_validas:
                # Mantener solo una sección por nombre y grado
                secciones = Seccion.objects.filter(grado=grado, nombre=nombre)
                if secciones.count() > 1:
                    # Mantener la primera y eliminar el resto
                    for s in secciones[1:]:
                        s.delete()
                        total_eliminadas += 1
            # Eliminar secciones con nombres no válidos
            otras = Seccion.objects.filter(grado=grado).exclude(nombre__in=secciones_validas)
            total_eliminadas += otras.count()
            otras.delete()
        self.stdout.write(self.style.SUCCESS(f'Secciones duplicadas/no válidas eliminadas: {total_eliminadas}'))
