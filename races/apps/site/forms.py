
from django import forms
from races.apps.site.models import Race
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU


REPEAT_CHOICES = [('none', 'No Repeat'),
                  ('weekly', 'Weekly'), 
                  ('monthly', 'Monthly')]

MONTH_N_CHOICES = [(1, "first"),
                   (2, "second"),
                   (3, "third"),
                   (4, "fourth"),
                   (-1, "last")]
                   
DAYS = [(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
        (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]

class RaceCreateForm(forms.ModelForm):
    
    class Meta:
        model = Race
    
        fields = ['title', 'date', 'time', 'club', 'url', 'location', 'status', 'description']
    
    repeat = forms.ChoiceField(label="Repeat by", required=False, choices=REPEAT_CHOICES)
    repeatN = forms.IntegerField(label="Repeat every", initial=1, required=False)
    repeatMonthN = forms.TypedChoiceField(label="which week", required=False, 
                                          choices=MONTH_N_CHOICES, coerce=int, empty_value=1)
    repeatDay = forms.TypedChoiceField(label="Repeat on day", required=False, choices=DAYS, coerce=int, empty_value=0)
    number = forms.IntegerField(initial=6, required=False)
    