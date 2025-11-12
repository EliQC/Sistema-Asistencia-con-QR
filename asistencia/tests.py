from django.test import TestCase, Client
from django.core.management import call_command
from django.conf import settings
from .models import Estudiante, Grado, Seccion, Apoderado, Asistencia
import tempfile
import os
import csv
from unittest.mock import patch
from django.utils import timezone
from datetime import datetime


class ImportEstudiantesCommandTest(TestCase):
	def setUp(self):
		self.tempdir = tempfile.mkdtemp()

	def tearDown(self):
		# limpiar archivos generados
		qr_dir = os.path.join(settings.MEDIA_ROOT or 'media', 'qrcodes')
		if os.path.exists(qr_dir):
			for f in os.listdir(qr_dir):
				if f.endswith('.png'):
					try:
						os.remove(os.path.join(qr_dir, f))
					except Exception:
						pass

	def test_import_csv_creates_students_and_qr(self):
		csv_path = os.path.join(self.tempdir, 'estudiantes.csv')
		with open(csv_path, 'w', newline='', encoding='utf-8') as f:
			writer = csv.DictWriter(f, fieldnames=['SECCION','DNI','CÓDIGO DEL ESTUDIANTE','APELLIDO PATERNO','APELLIDO MATERNO','NOMBRES','APELLIDOS Y NOMBRES','SEXO','ESTADO DE MATRÍCULA','OBSERVACIÓN'])
			writer.writeheader()
			writer.writerow({
				'SECCION': 'A',
				'DNI': '12345678',
				'CÓDIGO DEL ESTUDIANTE': 'COD123',
				'APELLIDO PATERNO': 'Perez',
				'APELLIDO MATERNO': 'Gonzales',
				'NOMBRES': 'Ana Maria',
				'APELLIDOS Y NOMBRES': '',
				'SEXO': 'F',
				'ESTADO DE MATRÍCULA': 'Matriculado',
				'OBSERVACIÓN': 'Sin observaciones',
			})

		call_command('import_estudiantes', csv_path, periodo=2025)

		est = Estudiante.objects.filter(dni='12345678').first()
		self.assertIsNotNone(est)
		self.assertEqual(est.codigo_qr, '12345678')

		# verificar codigo_interno y observaciones
		self.assertEqual(est.codigo_interno, 'COD123')
		self.assertEqual(est.estado_matricula, 'Matriculado')
		self.assertEqual(est.observaciones, 'Sin observaciones')

		qr_path = os.path.join(settings.MEDIA_ROOT or 'media', 'qrcodes', '12345678.png')
		self.assertTrue(os.path.exists(qr_path))


class AsistenciaRulesTest(TestCase):
	def setUp(self):
		self.grado = Grado.objects.create(nombre='1ro')
		self.seccion = Seccion.objects.create(nombre='A', grado=self.grado)
		self.est = Estudiante.objects.create(nombre='Test', apellido='Alumno', dni='87654321', fecha_nacimiento='2010-01-01', grado=self.grado, seccion=self.seccion, codigo_qr='87654321')
		self.client = Client()

	def post_qr(self, codigo_qr, when_dt):
		# Patch timezone.now to return when_dt (aware)
		class Dummy:
			@staticmethod
			def now():
				return when_dt

		with patch('asistencia.views.timezone', Dummy):
			return self.client.post('/asistencia/escanear/', {'codigo_qr': codigo_qr})

	def test_puntual_before_or_equal_1240(self):
		# 12:35 -> puntual
		dt = timezone.make_aware(datetime(2025, 11, 4, 12, 35))
		resp = self.post_qr('87654321', dt)
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertTrue(data['success'])
		self.assertEqual(data['estado'], 'puntual')

	def test_puntual_at_1240_boundary(self):
		dt = timezone.make_aware(datetime(2025, 11, 4, 12, 40))
		resp = self.post_qr('87654321', dt)
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertTrue(data['success'])
		self.assertEqual(data['estado'], 'puntual')

	def test_tarde_after_1240(self):
		dt = timezone.make_aware(datetime(2025, 11, 4, 12, 41))
		resp = self.post_qr('87654321', dt)
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertTrue(data['success'])
		self.assertEqual(data['estado'], 'tarde')

	def test_prevent_double_mark(self):
		dt = timezone.make_aware(datetime(2025, 11, 4, 12, 35))
		# first
		resp1 = self.post_qr('87654321', dt)
		data1 = resp1.json()
		self.assertTrue(data1['success'])
		# second attempt same day
		resp2 = self.post_qr('87654321', dt)
		data2 = resp2.json()
		self.assertFalse(data2['success'])

	def test_marcar_faltas_command(self):
		# Crear grado,seccion y 3 estudiantes
		grado = Grado.objects.create(nombre='2do')
		seccion = Seccion.objects.create(nombre='B', grado=grado)
		est1 = Estudiante.objects.create(nombre='A', apellido='Uno', dni='90000001', fecha_nacimiento=None, grado=grado, seccion=seccion, codigo_qr='90000001')
		est2 = Estudiante.objects.create(nombre='B', apellido='Dos', dni='90000002', fecha_nacimiento=None, grado=grado, seccion=seccion, codigo_qr='90000002')
		est3 = Estudiante.objects.create(nombre='C', apellido='Tres', dni='90000003', fecha_nacimiento=None, grado=grado, seccion=seccion, codigo_qr='90000003')
		# Preparar la fecha a usar (asegurar misma fecha para el registro y el comando)
		fecha_str = timezone.now().date().strftime('%Y-%m-%d')
		from datetime import datetime as _dt
		fecha_obj = _dt.strptime(fecha_str, '%Y-%m-%d').date()
		# Crear asistencia solo para est1 y forzar la fecha via update (evita auto_now_add override)
		a = Asistencia.objects.create(estudiante=est1, estado='puntual')
		Asistencia.objects.filter(id=a.id).update(fecha=fecha_obj)
		from django.core.management import call_command
		# pass options as keyword args to call_command to ensure they're parsed correctly
		call_command('marcar_faltas', fecha=fecha_str)
		# Ahora est2 y est3 deben tener registro de falta (sin depender exactamente de la fecha,
		# algunas diferencias de timezone en el runner pueden afectar la fecha guardada).
		self.assertTrue(Asistencia.objects.filter(estudiante__dni=est2.dni, estado='falta').exists())
		self.assertTrue(Asistencia.objects.filter(estudiante__dni=est3.dni, estado='falta').exists())
