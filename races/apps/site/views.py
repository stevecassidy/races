# top-level views for the project, which don't belong in any specific app

from django.views.generic.base import TemplateView
from django.views.generic import ListView
from django.views.generic import DetailView
from django.contrib.flatpages.models import FlatPage
from django.template import RequestContext
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect

from races.apps.site.models import Race, Club, RaceCourse
from races.apps.site.forms import RaceCreateForm

import datetime
import calendar
from dateutil.rrule import rrule, MONTHLY, WEEKLY, MO, TU, WE, TH, FR, SA, SU

DAYS = [MO, TU, WE, TH, FR, SA, SU]


class HomePage(ListView):

    model = Race
    template_name = "index.html"


    def get_queryset(self):
        # show the races for the next week
        startdate = datetime.date.today()
        enddate = startdate + datetime.timedelta(days=14)
        return Race.objects.filter(date__gte=startdate, date__lt=enddate, status__exact='p')
    
    def get_context_data(self, **kwargs):
        
        context = super(HomePage, self).get_context_data(**kwargs)
        pages = FlatPage.objects.filter(url='/')
        if len(pages) == 1:
            context['page'] = pages[0]
        else:
            context['page'] = {'title': 'Content',}
        return context    
    
class TestPageView(TemplateView):

    template_name = "test.html"


class ListRacesView(ListView):
    model = Race
    template_name = 'race_list.html'

    def get_queryset(self):

        if self.kwargs.has_key('year') and self.kwargs.has_key('month'):
            month = int(self.kwargs['month'])
            year = int(self.kwargs['year'])
            return Race.objects.filter(date__year=year, date__month=month, status__exact='p')
        else:
            # just pull races after today
            return Race.objects.filter(date__gte=datetime.date.today(), status__exact='p')


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
        context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club, status__exact='p')
        context['form'] = RaceCreateForm()
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
    template_name = "race_confirm_delete.html"
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RaceDeleteView, self).dispatch(*args, **kwargs)
    
@login_required
def create_races(request):
    
    if request.POST:
        form = RaceCreateForm(request.POST)
    else: 
        form = RaceCreateForm()
        
    if form.is_valid():
        # process it 
        if form.cleaned_data['repeat'] == 'none':

            race = form.save()
            return HttpResponseRedirect(reverse('race', kwargs={'slug': race.club.slug, 'pk': race.id}))
            
        else:
            startdate = form.cleaned_data['date']
                        
            number = form.cleaned_data['number']
            repeat = form.cleaned_data['repeat']
            repeatMonthN = form.cleaned_data['repeatMonthN']
            repeatDay = form.cleaned_data['repeatDay']
            
            if repeat == u'weekly':
                rule = rrule(WEEKLY, count=number, dtstart=startdate)
            elif repeat == u'monthly':
                rule = rrule(MONTHLY, count=number, dtstart=startdate, byweekday=DAYS[repeatDay](repeatMonthN))
                
            race = form.save(commit=False)
            
            # now make N more races 
            for date in rule:
                # force 'save as new'
                race.pk = None
                
                race.date = date
                race.save()
                
            return HttpResponseRedirect(reverse('club', kwargs={'slug': race.club.slug}))
    else:
        
        return render_to_response('race_create_form.html', 
                                  {'form': form},
                                  context_instance=RequestContext(request))


