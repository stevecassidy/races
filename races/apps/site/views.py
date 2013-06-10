# top-level views for the project, which don't belong in any specific app

from django.views.generic.base import TemplateView
from django.views.generic import ListView
from django.views.generic import DetailView
from django.contrib.flatpages.models import FlatPage

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from races.apps.site.models import Race, Club, RaceCourse
import datetime

class HomePage(ListView):

    model = Race
    template_name = "index.html"


    def get_queryset(self):
        # show the races for the next week
        startdate = datetime.date.today()
        enddate = startdate + datetime.timedelta(days=14)
        return Race.objects.filter(date__gte=startdate, date__lt=enddate)
    
    def get_context_data(self, **kwargs):
        
        context = super(HomePage, self).get_context_data(**kwargs)
        pages = FlatPage.objects.filter(url='/')
        if len(pages) == 1:
            context['page'] = pages[0]
        else:
            context['page'] = {'title': 'Content',
                               'content': "<p>Create a flatpage with url '/' to see content here</p>"}
        return context    
    


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
            return Race.objects.filter(date__gte=datetime.date.today())


class RaceDetailView(DetailView):
    model = Race
    template_name = 'race_detail.html'
    context_object_name = 'race'

class ClubListView(ListView):
    model = Club
    template_name = 'club_list.html'
    context_object_name = 'clubs'

class ClubDetailView(DetailView):
    model = Club
    template_name = 'club_detail.html'
    context_object_name = 'club'
    
    def get_context_data(self, **kwargs):
        
        context = super(ClubDetailView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the future races
        slug = self.kwargs['slug']
        club = Club.objects.get(slug=slug)
        context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club)
        return context
    
    

class RaceUpdateView(UpdateView):
    model = Race
    template_name = "race_form.html"
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RaceUpdateView, self).dispatch(*args, **kwargs)
    
    
class RaceDeleteView(DeleteView):
    model = Race
    success_url = reverse_lazy('races')
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RaceDeleteView, self).dispatch(*args, **kwargs)
    
class RaceCreateView(CreateView):
    model = Race
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RaceCreateView, self).dispatch(*args, **kwargs)
    

