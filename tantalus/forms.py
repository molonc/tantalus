import os

#===========================
# Django imports
#---------------------------
from django.forms import ModelForm
from django.forms.extras.widgets import SelectDateWidget

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
