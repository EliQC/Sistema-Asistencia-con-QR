from django import forms
from asistencia.models import Grado, Seccion
from django.utils import timezone

class SeccionMultipleForm(forms.Form):
    grados = forms.ModelMultipleChoiceField(
        queryset=Grado.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Selecciona los grados'
    )
    secciones = forms.MultipleChoiceField(
        choices=[('A','A'),('B','B'),('C','C'),('D','D')],
        widget=forms.CheckboxSelectMultiple,
        label='Selecciona las secciones'
    )


class ImportFileForm(forms.Form):
    archivo = forms.FileField(label='Archivo (.xlsx o .csv)')
    periodo = forms.IntegerField(required=False, label='Periodo (año)', initial=timezone.now().year)
