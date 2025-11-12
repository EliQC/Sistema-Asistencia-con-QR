from django.db import models
"""
Aquí se coloca los modelos que representan las entidades del sistema:

Grado Sección Apoderado Estudiante Asistencia
"""
# Crea tus modelos aquí.
#=======================
#Modelo Grado
#=======================
from django.db import models

class Grado(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre
"""
👉 Representa los grados: “1°”, “2°”, “3°”, etc.
El campo unique=True evita duplicados.
"""
#=======================
#Modelo Sección
#=======================
class Seccion(models.Model):
    nombre = models.CharField(max_length=5)
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE, related_name="secciones")

    def __str__(self):
        return f"{self.grado.nombre} - Sección {self.nombre}"
"""
👉 Cada sección pertenece a un grado.
related_name="secciones" te permitirá acceder a todas las secciones de un grado con 
grado.secciones.all().
"""
#=======================
#Modelo Apoderado  
#=======================
class Apoderado(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    celular = models.CharField(max_length=15)
    correo = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
""" 
👉 Guarda la información de contacto del padre o tutor.
El correo es único para evitar duplicados.
"""
#=======================
#Modelo Estudiante
#=======================
class Estudiante(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(max_length=8, unique=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    codigo_qr = models.CharField(max_length=255, unique=True)
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)
    # Apoderado pasa a ser opcional (no obligatorio al crear estudiante)
    apoderado = models.ForeignKey(Apoderado, on_delete=models.CASCADE, null=True, blank=True)
    # Periodo (año escolar) para permitir depuración por año
    periodo = models.IntegerField(default=2025)
    # Código interno opcional (p. ej. código del colegio distinto al DNI)
    codigo_interno = models.CharField(max_length=50, null=True, blank=True)
    # Estado de matrícula y observaciones (opcional)
    estado_matricula = models.CharField(max_length=50, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
"""
👉 Este modelo vincula las relaciones principales: grado, sección y apoderado.
Más adelante el campo codigo_qr servirá para almacenar el texto o URL codificada del QR.
"""
#=======================
#Modelo Asistencia
#=======================
class Asistencia(models.Model):
    ESTADOS = [
        ('puntual', 'Puntual'),
        ('tarde', 'Tarde'),
        ('falta', 'Falta'),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="asistencias")
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADOS)
    observacion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.estudiante} - {self.fecha} - {self.estado}"
"""
👉 Cada registro pertenece a un estudiante, con fecha y hora automáticas.
Usamos choices para limitar el estado a “puntual”, “tarde” o “falta”.
"""
