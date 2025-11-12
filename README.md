# Sistema de Asistencia (IEJAQG)

Proyecto Django para gestión de asistencia con QR, importación desde Excel/CSV y panel de administración.

Requisitos
- Python 3.11+
- PostgreSQL (o ajusta `DATABASES` para tu motor)
- Dependencias en `requirements.txt`

Cómo ejecutar localmente
1. Crear entorno virtual e instalar dependencias:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. Crear archivo de entorno (no lo subas al repo):
```powershell
copy env.example .env
# editar .env y definir DJANGO_SECRET_KEY, DB_* etc.
```
3. Ejecutar migraciones y arrancar el servidor:
```powershell
python manage.py migrate
python manage.py runserver
```

Tests
```powershell
python manage.py test asistencia
```

Despliegue
- Recomiendo usar Render, Railway o Supabase (Postgres) como DB.
- No subas secretos al repo; usa variables de entorno en la plataforma.
