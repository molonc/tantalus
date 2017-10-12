import os

#===========================
# Django imports
#---------------------------
from django.forms import ModelForm, Form, FileField

#===========================
# App imports
#---------------------------
from .models import Sample

#===========================
# Sample forms
#---------------------------
class SampleForm(ModelForm):
    class Meta:
        model = Sample
        fields = "__all__"

class ExcelForm(Form):
	excel_file = FileField()
