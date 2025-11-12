from django.urls import path
from . import views

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard, name='dashboard'),
    
    # Gestión de estudiantes
    path('estudiantes/', views.lista_estudiantes, name='lista_estudiantes'),
    
    # Sistema de QR
    path('estudiante/<int:estudiante_id>/qr/', views.ver_qr_estudiante, name='ver_qr_estudiante'),
    path('estudiante/<int:estudiante_id>/generar-qr/', views.generar_qr_estudiante, name='generar_qr_estudiante'),
    
    # Registro de asistencia
    path('asistencia/registrar/', views.registrar_asistencia_manual, name='registrar_asistencia_manual'),
    path('asistencia/escanear/', views.registrar_asistencia_qr, name='registrar_asistencia_qr'),
    
    # Reportes
    path('reportes/', views.reporte_asistencia, name='reporte_asistencia'),
    path('secciones/registrar-multiples/', views.registrar_secciones_multiples, name='registrar_secciones_multiples'),
    path('ajax/secciones/', views.secciones_por_grado, name='ajax_secciones_por_grado'),
    # Importador vía web (staff)
    path('importar/', views.importar_estudiantes_web, name='importar_estudiantes_web'),
    path('import_status/<str:upload_name>/', views.import_status, name='import_status'),
    path('import_delete/<str:upload_name>/', views.import_delete_upload, name='import_delete_upload'),
]
