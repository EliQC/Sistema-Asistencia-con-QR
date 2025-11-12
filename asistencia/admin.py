from django.contrib import admin
from .models import Grado, Seccion, Apoderado, Estudiante, Asistencia
#Esto te permite ver y gestionar todos los datos desde el panel de administración.
admin.site.register(Grado)
admin.site.register(Seccion)
admin.site.register(Apoderado)
admin.site.register(Estudiante)
admin.site.register(Asistencia)

# Register your models here.
