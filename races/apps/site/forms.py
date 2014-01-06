
from django import forms
from races.apps.site.models import Race

class RaceCreateForm(forms.ModelForm):
    
    class Meta:
        model = Race
    
        fields = ['title', 'date', 'time', 'club', 'url', 'location', 'status', 'description']
    
    weekly = forms.BooleanField(required=False)
    monthly = forms.BooleanField(required=False)
    number = forms.IntegerField(initial=6, required=False)
    