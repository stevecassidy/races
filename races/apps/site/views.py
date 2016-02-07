# top-level views for the project, which don't belong in any specific app

from django.views.generic.base import TemplateView
from django.views.generic import View, ListView, DetailView, FormView
from django.contrib.flatpages.models import FlatPage
from django.template import RequestContext
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.db import IntegrityError

from django.contrib.auth.models import User
from races.apps.site.models import Race, Club, RaceCourse
from races.apps.site.usermodel import PointScore, Rider, RaceResult
from races.apps.site.forms import RaceCreateForm, RaceCSVForm, RaceRiderForm

import datetime
import calendar
from dateutil.rrule import rrule, MONTHLY, WEEKLY, MO, TU, WE, TH, FR, SA, SU
import json
import csv

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

    def get_context_data(self, **kwargs):

        context = super(RaceDetailView, self).get_context_data(**kwargs)

        context['csvform'] = RaceCSVForm()
        if 'iframe' in self.request.GET:
            context['iframe'] = True

        return context

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

        if self.request.user.is_authenticated():
            context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club)
        else:
            context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club, status__exact='p')

        context['form'] = RaceCreateForm()
        if 'iframe' in self.request.GET:
            context['iframe'] = True

        return context

class ClubRidersView(ListView):

    model = Club
    template_name = 'club_riders.html'

    def get_context_data(self, **kwargs):

        context = super(ClubRidersView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the future races
        slug = self.kwargs['slug']
        context['club'] = Club.objects.get(slug=slug)
        context['riders'] = context['club'].rider_set.all().order_by('user__last_name')
        return context

class ClubPointscoreView(DetailView):

    model = PointScore
    template_name = "pointscore_detail.html"

    def get_context_data(self, **kwargs):

        context = super(ClubPointscoreView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the future races
        club = self.kwargs['club']
        context['club'] = Club.objects.get(slug=club)
        context['races'] = Race.objects.filter(pointscore=self.object)

        return context

class ClubPointscoreList(ListView):

    model = PointScore

    def get_context_data(self, **kwargs):

        context = super(ClubPointscoreView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the future races
        club = self.kwargs['club']
        context['club'] = Club.objects.get(slug=club)
        context['races'] = Race.objects.filter(pointscore=self.object)

        return context

class CSVResponseMixin(object):
    csv_filename = 'csvfile.csv'

    def get_csv_filename(self):
        return self.csv_filename

    def render_to_csv(self, data):
        response = HttpResponse(content_type='text/csv')
        cd = 'attachment; filename="{0}"'.format(self.get_csv_filename())
        response['Content-Disposition'] = cd

        writer = csv.writer(response)
        for row in data:
            writer.writerow(row)

        return response

class ClubRidersCSVView(View):

    def get(self, request, *args, **kwargs):

        club = get_object_or_404(Club, slug=kwargs['slug'])

        response = HttpResponse(content_type='text/csv')
        cd = 'attachment; filename="{0}"'.format("race.csv")
        response['Content-Disposition'] = cd

        writer = csv.writer(response)
        header = ('LastName',
                  'FirstName',
                  'Regd',  # U/R
                  'Grade',
                  'HCap',
                  'Fee',
                  'ShirtNo',
                  'Points',
                  'LicenceNo',
                  'Club',
                  'Email',
                  'Id',
                  'EventNo')

        writer.writerow(header)
        for r in Rider.objects.all():

            grades = r.clubgrade_set.filter(club=club)
            if grades.count() > 0:
                grade = grades[0].grade
            else:
                grade = ''

            row = (r.user.last_name,
                   r.user.first_name,
                   'U',
                   grade,
                   '2',
                   'F',
                   '',
                   '2',
                   r.licenceno,
                   r.club.slug,
                   r.user.email,
                   r.pk,
                   ''
                  )
            writer.writerow(row)

        return response


class RiderListView(ListView):
    model = Rider
    template_name = 'rider_list.html'
    context_object_name = 'riders'


class RiderView(DetailView):

    model = User
    template_name = 'rider_detail.html'
    context_object_name = 'user'


class RaceUpdateView(UpdateView):
    model = Race
    template_name = "race_form.html"
    fields = ['title', 'date', 'time', 'url', 'location', 'status', 'description']

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):

        race = get_object_or_404(Race, **kwargs)

        if self.request.user.rider.club == race.club and self.request.user.rider.official:
            return super(RaceUpdateView, self).dispatch(*args, **kwargs)
        else:
            return HttpResponseRedirect('/login/?next=%s' % self.request.path)

class RaceUploadCSVView(FormView):

    form_class = RaceCSVForm
    template_name = ''

    def form_valid(self, form):

        # need to work out what race we're in - from the URL pk
        race = get_object_or_404(Race, pk=self.kwargs['pk'])

        race.load_csv_results(self.request.FILES['csvfile'])

        return HttpResponseRedirect(reverse('race', kwargs=self.kwargs))

class RaceDeleteView(DeleteView):
    model = Race
    success_url = reverse_lazy('races')
    template_name = "race_confirm_delete.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RaceDeleteView, self).dispatch(*args, **kwargs)

class RaceRidersView(ListView):
    model = RaceResult
    template_name = "raceresult_list.html"

    def get_context_data(self, **kwargs):

        context = super(RaceRidersView, self).get_context_data(**kwargs)

        club = self.kwargs['slug']
        race = self.kwargs['pk']
        context['club'] = Club.objects.get(slug=club)
        context['race'] = Race.objects.get(pk=race)
        context['form'] = RaceRiderForm(initial={'race': race})

        return context

    def get_queryset(self):

        race = self.kwargs['pk']

        return RaceResult.objects.filter(race__pk__exact=race)

    def post(self, request, **kwargs):

        form = RaceRiderForm(request.POST)

        if form.is_valid():

            entry = RaceResult(race=form.cleaned_data['race'],
                               rider=form.cleaned_data['rider'],
                               number=form.cleaned_data['number'],
                               grade=form.cleaned_data['grade'])

            # TODO: check for errors here
            try:
                entry.save()
            except IntegrityError:
                # rider/number or number/grade already registered
                pass

        return HttpResponseRedirect(reverse('race_riders', kwargs=kwargs))


def clubRaces(request, slug):
    """View to create one or more races for a club"""

    if request.method == "POST":

        form = RaceCreateForm(request.POST)

        if request.is_ajax():
            if form.is_valid():
                # process it
                pointscore = form.cleaned_data['pointscore']
                if form.cleaned_data['repeat'] == 'none':

                    race = form.save()
                    if pointscore:
                        pointscore.races.add(race)

                    data = json.dumps({'success': 1})
                    return HttpResponse(data, content_type='application/json')
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
                        if pointscore:
                            pointscore.races.add(race)

                    data = json.dumps({'success': 1})
                    return HttpResponse(data, content_type='application/json')
            else:
                data = json.dumps(dict([(k, [unicode(e) for e in v]) for k,v in form.errors.items()]))
                return HttpResponse(data, content_type='application/json')

        return HttpError()
