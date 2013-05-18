# top-level views for the project, which don't belong in any specific app

from django.views.generic.base import TemplateView
from django.views.generic import ListView
from django.views.generic import DetailView

from races.apps.site.models import Race, Club, RaceCourse
import datetime

class HomePage(ListView):

    model = Race
    template_name = "index.html"


    def get_queryset(self):
        # show the races for the next week
        startdate = datetime.date.today()
        enddate = startdate + datetime.timedelta(days=14)
        return Race.objects.filter(date__gt=startdate, date__lt=enddate)


class ListRacesView(ListView):
    model = Race
    template_name = 'race_list.html'

    def get_queryset(self):

        if self.kwargs.has_key('year') and self.kwargs.has_key('month'):
            month = int(self.kwargs['month'])
            year = int(self.kwargs['year'])
            return Race.objects.filter(date__year=year, date__month=month)
        else:
            # just pull races after today
            return Race.objects.filter(date__gt=datetime.date.today())


class RaceDetailView(DetailView):
    model = Race
    template_name = 'race_detail.html'
    context_object_name = 'race'



