from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, time
import qrcode
from io import BytesIO
import base64
from .models import Estudiante, Asistencia, Grado, Seccion, Apoderado
from .forms import SeccionMultipleForm
from django.contrib.auth.decorators import user_passes_test
from .forms import ImportFileForm
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.core.management import call_command
import os
import uuid
from django.views.decorators.http import require_http_methods
import json
from . import tasks
import threading
import re
from django.views.decorators.csrf import ensure_csrf_cookie

# =====================================================
# VISTA PRINCIPAL - Dashboard
# =====================================================
def dashboard(request):
    """
    Vista principal del sistema que muestra estadísticas generales
    """
    total_estudiantes = Estudiante.objects.count()
    total_grados = Grado.objects.count()
    
    # Asistencias de hoy
    hoy = timezone.now().date()
    asistencias_hoy = Asistencia.objects.filter(fecha=hoy)
    
    context = {
        'total_estudiantes': total_estudiantes,
        'total_grados': total_grados,
        'asistencias_hoy': asistencias_hoy.count(),
        'puntuales': asistencias_hoy.filter(estado='puntual').count(),
        'tardes': asistencias_hoy.filter(estado='tarde').count(),
        'faltas': asistencias_hoy.filter(estado='falta').count(),
    }
    return render(request, 'asistencia/dashboard.html', context)

# =====================================================
# GESTIÓN DE ESTUDIANTES
# =====================================================
def lista_estudiantes(request):
    """
    Lista todos los estudiantes con filtros por grado y sección
    """
    grado_id = request.GET.get('grado')
    seccion_id = request.GET.get('seccion')
    
    estudiantes = Estudiante.objects.all().select_related('grado', 'seccion', 'apoderado')
    
    if grado_id:
        estudiantes = estudiantes.filter(grado_id=grado_id)
    if seccion_id:
        estudiantes = estudiantes.filter(seccion_id=seccion_id)
    
    grados = Grado.objects.all()
    if grado_id:
        secciones = Seccion.objects.filter(grado_id=grado_id)
    else:
        secciones = Seccion.objects.all()
    
    context = {
        'estudiantes': estudiantes,
        'grados': grados,
        'secciones': secciones,
    }
    return render(request, 'asistencia/lista_estudiantes.html', context)

# =====================================================
# SISTEMA DE CÓDIGOS QR
# =====================================================
def generar_qr_estudiante(request, estudiante_id):
    """
    Genera un código QR único para un estudiante
    """
    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
    
    # Si el estudiante ya tiene código QR, lo mostramos
    if not estudiante.codigo_qr:
        # Generamos un código único basado en el ID y DNI
        estudiante.codigo_qr = f"EST-{estudiante.id}-{estudiante.dni}"
        estudiante.save()
    
    # Crear el código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(estudiante.codigo_qr)
    qr.make(fit=True)
    
    # Generar imagen
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Devolver la imagen
    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="qr_{estudiante.dni}.png"'
    return response

def ver_qr_estudiante(request, estudiante_id):
    """
    Página para ver y descargar el QR de un estudiante
    """
    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
    
    # Generar QR en base64 para mostrar en HTML
    if not estudiante.codigo_qr:
        estudiante.codigo_qr = f"EST-{estudiante.id}-{estudiante.dni}"
        estudiante.save()
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(estudiante.codigo_qr)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'estudiante': estudiante,
        'qr_base64': qr_base64,
    }
    return render(request, 'asistencia/ver_qr.html', context)

# =====================================================
# REGISTRO DE ASISTENCIA
# =====================================================
def registrar_asistencia_manual(request):
    """
    Permite registrar asistencia manualmente seleccionando estudiantes
    """
    if request.method == 'POST':
        estudiante_id = request.POST.get('estudiante_id')
        estado = request.POST.get('estado')
        observacion = request.POST.get('observacion', '')
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        
        # Verificar si ya existe registro hoy
        hoy = timezone.localdate()
        # usar hora local y comparar con objetos time naive
        _now_local = timezone.localtime()
        hora_actual = _now_local.time().replace(tzinfo=None)
        asistencia_existente = Asistencia.objects.filter(
            estudiante=estudiante,
            fecha=hoy
        ).first()

        if asistencia_existente:
            messages.warning(request, f'Ya existe un registro de asistencia para {estudiante} hoy.')
        else:
            # Horarios del centro
            inicio_clase = time(12, 30)
            limite_tarde = time(12, 40)
            fin_clase = time(17, 30)

            # Si se intenta registrar después del fin de clases, no se permite desde la UI
            if hora_actual > fin_clase:
                messages.error(request, f'No se puede registrar asistencia: el día lectivo terminó a las {fin_clase.strftime("%H:%M")}')
            else:
                # Si el estado no fue enviado, deducir en base a la hora
                if not estado:
                    if hora_actual <= limite_tarde:
                        estado_calculado = 'puntual'
                    else:
                        estado_calculado = 'tarde'
                else:
                    estado_calculado = estado

                Asistencia.objects.create(
                    estudiante=estudiante,
                    estado=estado_calculado,
                    observacion=observacion
                )
                messages.success(request, f'Asistencia registrada para {estudiante} ({estado_calculado})')
        
        return redirect('registrar_asistencia_manual')
    
    # GET request
    grados = Grado.objects.all()
    estudiantes = Estudiante.objects.all().select_related('grado', 'seccion')
    
    context = {
        'grados': grados,
        'estudiantes': estudiantes,
    }
    return render(request, 'asistencia/registrar_asistencia.html', context)

def registrar_asistencia_qr(request):
    """
    Registra asistencia escaneando el código QR
    """
    if request.method == 'POST':
        codigo_qr = request.POST.get('codigo_qr')
        
        try:
            estudiante = Estudiante.objects.get(codigo_qr=codigo_qr)
            
            # Verificar si ya se registró hoy
            hoy = timezone.localdate()
            asistencia_existente = Asistencia.objects.filter(
                estudiante=estudiante,
                fecha=hoy
            ).first()

            if asistencia_existente:
                return JsonResponse({
                    'success': False,
                    'message': f'{estudiante.nombre} {estudiante.apellido} ya registró asistencia hoy a las {asistencia_existente.hora.strftime("%H:%M")}'
                })

            # Determinar el estado según la hora y las reglas del centro
            # usar hora local y comparar con objetos time naive
            _now_local = timezone.localtime()
            hora_actual = _now_local.time().replace(tzinfo=None)
            inicio_clase = time(12, 30)
            limite_tarde = time(12, 40)
            fin_clase = time(17, 30)

            # Si ya pasó el fin de clases, no registramos via QR (las faltas se marcarán con comando al final del día)
            if hora_actual > fin_clase:
                return JsonResponse({
                    'success': False,
                    'message': f'No es posible registrar asistencia: el horario de clase finalizó a las {fin_clase.strftime("%H:%M")}'
                })

            if hora_actual <= limite_tarde:
                estado = 'puntual'
            else:
                estado = 'tarde'

            # Crear el registro
            asistencia = Asistencia.objects.create(
                estudiante=estudiante,
                estado=estado
            )
            
            return JsonResponse({
                'success': True,
                'estudiante': f'{estudiante.nombre} {estudiante.apellido}',
                'grado': str(estudiante.grado),
                'seccion': str(estudiante.seccion),
                'estado': estado,
                'hora': asistencia.hora.strftime('%H:%M:%S')
            })
            
        except Estudiante.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Código QR no válido'
            })
    
    return render(request, 'asistencia/escanear_qr.html')

# =====================================================
# REPORTES
# =====================================================
def reporte_asistencia(request):
    """
    Genera reportes de asistencia con filtros
    """
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    grado_id = request.GET.get('grado')
    estudiante_id = request.GET.get('estudiante')
    
    asistencias = Asistencia.objects.all().select_related('estudiante', 'estudiante__grado', 'estudiante__seccion')
    
    if fecha_inicio:
        asistencias = asistencias.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        asistencias = asistencias.filter(fecha__lte=fecha_fin)
    if grado_id:
        asistencias = asistencias.filter(estudiante__grado_id=grado_id)
    if estudiante_id:
        asistencias = asistencias.filter(estudiante_id=estudiante_id)
    
    # Ordenar por fecha descendente
    asistencias = asistencias.order_by('-fecha', '-hora')
    
    # Estadísticas
    total = asistencias.count()
    puntuales = asistencias.filter(estado='puntual').count()
    tardes = asistencias.filter(estado='tarde').count()
    faltas = asistencias.filter(estado='falta').count()
    
    grados = Grado.objects.all()
    estudiantes = Estudiante.objects.all().select_related('grado', 'seccion')
    
    context = {
        'asistencias': asistencias,
        'total': total,
        'puntuales': puntuales,
        'tardes': tardes,
        'faltas': faltas,
        'grados': grados,
        'estudiantes': estudiantes,
    }
    return render(request, 'asistencia/reporte_asistencia.html', context)

# =====================================================
# REGISTRO MÚLTIPLE DE SECCIONES POR GRADOS
# =====================================================
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def registrar_secciones_multiples(request):
    """
    Permite registrar varias secciones para varios grados en un solo paso
    """
    if request.method == 'POST':
        form = SeccionMultipleForm(request.POST)
        if form.is_valid():
            grados = form.cleaned_data['grados']
            secciones = form.cleaned_data['secciones']
            creados = 0
            for grado in grados:
                for nombre_seccion in secciones:
                    obj, created = Seccion.objects.get_or_create(nombre=nombre_seccion, grado=grado)
                    if created:
                        creados += 1
            messages.success(request, f'Se crearon {creados} secciones correctamente.')
            return redirect('registrar_secciones_multiples')
    else:
        form = SeccionMultipleForm()
    return render(request, 'asistencia/registrar_secciones_multiples.html', {'form': form})

def secciones_por_grado(request):
    grado_id = request.GET.get('grado_id')
    data = []
    if grado_id:
        secciones = Seccion.objects.filter(grado_id=grado_id).order_by('nombre')
        for s in secciones:
            data.append({'id': s.id, 'nombre': s.nombre})
    return JsonResponse({'secciones': data})


@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_http_methods(["GET", "POST"])
def importar_estudiantes_web(request):
    """
    Vista para subir un archivo (.xlsx o .csv) desde la web y ejecutar el importador.
    Solo accesible para staff/superuser.
    """
    form = ImportFileForm(request.POST or None, request.FILES or None)
    uploads_dir = os.path.join(settings.MEDIA_ROOT or 'media', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    if request.method == 'POST' and form.is_valid():
        archivo = form.cleaned_data['archivo']
        periodo = form.cleaned_data.get('periodo')

        # Basic validation: extension and size
        allowed_ext = ['.xlsx', '.xls', '.csv']
        ext = os.path.splitext(archivo.name)[1].lower()
        if ext not in allowed_ext:
            messages.error(request, 'Tipo de archivo no soportado. Usa .xlsx, .xls o .csv')
            return redirect('importar_estudiantes_web')

        # If user uploaded an Excel file, ensure openpyxl is installed before accepting
        if ext in ('.xls', '.xlsx'):
            try:
                import openpyxl  # noqa: F401
            except Exception:
                messages.error(request, 'Soporte para .xlsx no disponible en el servidor (falta openpyxl). Convierte a CSV o instala openpyxl.')
                return redirect('importar_estudiantes_web')

        max_size = 10 * 1024 * 1024  # 10 MB
        if archivo.size > max_size:
            messages.error(request, 'Archivo demasiado grande. Límite: 10 MB')
            return redirect('importar_estudiantes_web')

        # Guardar con nombre único
        unique_name = f"import_{uuid.uuid4().hex}{ext}"
        fs = FileSystemStorage(location=uploads_dir)
        filename = fs.save(unique_name, archivo)
        filepath = fs.path(filename)

        # Create a status json next to the file
        status_path = f"{filepath}.status.json"
        status = {
            'id': os.path.basename(filename),
            'filename': filename,
            'uploaded_at': str(datetime.now()),
            'status': 'queued',
            'periodo': periodo,
        }
        try:
            with open(status_path, 'w', encoding='utf-8') as sf:
                json.dump(status, sf, default=str, ensure_ascii=False)
        except Exception:
            pass

        # Lanzar la importación en background (Thread) para no bloquear la request
        try:
            if getattr(tasks, 'import_file_task', None):
                try:
                    thread = threading.Thread(target=tasks.import_file_task, args=(filepath, periodo), daemon=True)
                    thread.start()
                    messages.success(request, 'Archivo subido. Importación iniciada en segundo plano.')
                except Exception as e:
                    messages.error(request, f'Error iniciando importación en background: {e}')
            else:
                # Fallback: ejecutar el comando directamente (síncrono)
                try:
                    call_command('import_estudiantes', filepath, periodo=periodo)
                    messages.success(request, 'Archivo subido. Importación ejecutada vía comando.')
                except Exception as e:
                    messages.error(request, f'Error ejecutando importación vía comando: {e}')
        except Exception as e:
            messages.error(request, f'Error iniciando importación: {e}')

        return redirect('importar_estudiantes_web')

    # GET: list uploads and statuses
    uploads = []
    try:
        for fn in sorted(os.listdir(uploads_dir), reverse=True):
            if fn.startswith('import_'):
                full = os.path.join(uploads_dir, fn)
                statusf = f"{full}.status.json"
                status = None
                if os.path.exists(statusf):
                    try:
                        with open(statusf, 'r', encoding='utf-8') as sf:
                            status = json.load(sf)
                    except Exception:
                        status = {'status': 'unknown'}
                # create a safe id for DOM elements (no spaces or special chars)
                safe_id = re.sub(r'[^0-9a-zA-Z_-]', '_', fn)
                uploads.append({'name': fn, 'path': full, 'status': status, 'safe_id': safe_id})
    except Exception:
        uploads = []

    return render(request, 'asistencia/importar_estudiantes.html', {'form': form, 'uploads': uploads})


@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_http_methods(["GET"])
def import_status(request, upload_name):
    """Return the parsed status JSON for a given upload file name (without directory)."""
    uploads_dir = os.path.join(settings.MEDIA_ROOT or 'media', 'uploads')
    # sanitize upload_name to avoid path traversal
    safe_name = os.path.basename(upload_name)
    status_path = os.path.join(uploads_dir, safe_name) + '.status.json'
    if os.path.exists(status_path):
        try:
            with open(status_path, 'r', encoding='utf-8') as sf:
                data = json.load(sf)
            return JsonResponse({'ok': True, 'status': data})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    return JsonResponse({'ok': False, 'error': 'status file not found'}, status=404)


@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_http_methods(["POST"])
def import_delete_upload(request, upload_name):
    """Delete an uploaded file and its status JSON. POST-only, staff-only."""
    uploads_dir = os.path.join(settings.MEDIA_ROOT or 'media', 'uploads')
    safe_name = os.path.basename(upload_name)
    file_path = os.path.join(uploads_dir, safe_name)
    status_path = f"{file_path}.status.json"
    removed = []
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            removed.append(file_path)
        if os.path.exists(status_path):
            os.remove(status_path)
            removed.append(status_path)
    except Exception as e:
        messages.error(request, f'Error eliminando archivos: {e}')
        return redirect('importar_estudiantes_web')

    messages.success(request, f'Archivos eliminados: {len(removed)}')
    return redirect('importar_estudiantes_web')
