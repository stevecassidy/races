# top-level views for the project, which don't belong in any specific app

from django.views.generic.base import TemplateView
from django.views.generic import View, ListView, DetailView, FormView
from django.contrib.flatpages.models import FlatPage
from django.template import RequestContext
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.db import IntegrityError
from django.contrib.auth.mixins import AccessMixin

from django.contrib.auth.models import User
from races.apps.cabici.models import Race, Club, RaceCourse
from races.apps.cabici.usermodel import PointScore, Rider, RaceResult, ClubRole, RaceStaff, parse_img_members, UserRole, ClubGrade
from races.apps.cabici.forms import RaceCreateForm, RaceCSVForm, RaceRiderForm, MembershipUploadForm, RiderSearchForm, RiderUpdateForm, RiderUpdateFormOfficial

import datetime
import calendar
from dateutil.rrule import rrule, MONTHLY, WEEKLY, MO, TU, WE, TH, FR, SA, SU
import json
import csv
import os
from StringIO import StringIO
import pyexcel

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

#class TestPageView(TemplateView):

#    template_name = "test.html"

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

        context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club, status__exact='p')[:5]

        context['form'] = RaceCreateForm()

        return context

class ClubOfficialRequiredMixin(AccessMixin):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        # user should be an official of the club referenced in the view
        if not request.user.rider.official:
            return self.handle_no_permission()

        # if there is a club slug in the kwargs then verify that
        # the official is a member of that club
        if 'slug' in kwargs:
            clublist = Club.objects.filter(slug=kwargs['slug'])
            if len(clublist) == 1:
                club = clublist[0]
                if not request.user.rider.club == club:
                    return self.handle_no_permission()

        return super(ClubOfficialRequiredMixin, self).dispatch(request, *args, **kwargs)

class ClubDashboardView(ClubOfficialRequiredMixin, DetailView):

    model = Club
    template_name = 'club_dashboard.html'
    context_object_name = 'club'

    def get_context_data(self, **kwargs):

        context = super(ClubDashboardView, self).get_context_data(**kwargs)
        #slug = self.kwargs['slug']
        #club = Club.objects.get(slug=slug)
        context['racecreateform'] = RaceCreateForm()
        context['memberuploadform'] = MembershipUploadForm(initial={'club': context['club']})
        context['statistics'] = context['club'].statistics()
        context['searchform'] = RiderSearchForm()

        return context

class ClubRidersView(ListView):

    model = Club
    template_name = 'club_riders.html'

    def get_context_data(self, **kwargs):

        thisyear = datetime.date.today().year

        context = super(ClubRidersView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the future races
        slug = self.kwargs['slug']
        context['club'] = Club.objects.get(slug=slug)
        context['members'] = context['club'].rider_set.filter(membership__year__gte=thisyear).distinct().order_by('user__last_name')
        context['pastmembers'] = context['club'].rider_set.exclude(membership__year__gte=thisyear).distinct().order_by('user__last_name')

        return context

    def post(self, request, **kwargs):
        """Handle upload of membership spreadsheets"""

        form = MembershipUploadForm(request.POST, request.FILES)
        if form.is_valid():
            mf = request.FILES['memberfile']
            club = form.cleaned_data['club']
            fileformat = form.cleaned_data['fileformat']

            if fileformat == 'IMG':
                changed = Rider.objects.update_from_spreadsheet(club, parse_img_members(mf))

            else:
                # unknown format
                pass

            return render(request, 'club_rider_update.html', {'club': club, 'changed': changed})

class ClubPointscoreView(DetailView):

    model = PointScore
    template_name = "pointscore_detail.html"

    def get_context_data(self, **kwargs):

        context = super(ClubPointscoreView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the future races
        club = self.kwargs['slug']
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

class ClubRidersExcelView(View):

    def get(self, request, *args, **kwargs):

        club = get_object_or_404(Club, slug=kwargs['slug'])

        # worksheet is a list of row tuples
        ws = []

        if 'eventno' in request.GET:
            eventno = request.GET['eventno']
        else:
            eventno = '12345'

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

        ws.append(header)

        for r in Rider.objects.all():

            grades = r.clubgrade_set.filter(club=club)
            if grades.count() > 0:
                grade = grades[0].grade
            else:
                grade = ''

            try:
                clubslug = r.club.slug
            except:
                clubslug = 'Unknown'

            row = (r.user.last_name,
                   r.user.first_name,
                   'U',
                   grade,
                   2,
                   'F',
                   '',
                   2,
                   r.licenceno,
                   clubslug,
                   r.user.email,
                   '',  # needs to be the id from the old site or empty
                   eventno
                  )
            ws.append(row)

        sheet = pyexcel.Sheet(ws)
        io = StringIO()
        sheet.save_to_memory("xls", io)

        response = HttpResponse(io.getvalue(), content_type='application/vnd-ms.excel')
        response['Content-Disposition'] = 'attachment; filename="riders-{0}.xls"'.format(eventno)

        return response

class ClubGradeView(UpdateView,ClubOfficialRequiredMixin):
    model = ClubGrade
    template_name = "rider_update.html"
    context_object_name = "clubgrade"
    fields = ['grade']

    def get_object(self):

        club = get_object_or_404(Club, slug=self.kwargs['slug'])
        user = get_object_or_404(User, pk=self.kwargs['pk'])

        clubgrade = ClubGrade.objects.get(rider=user.rider, club=club)
        return clubgrade

    def get_success_url(self):
        # redirect to the rider view on success
        return reverse('rider', kwargs={'pk': self.kwargs['pk']})


class RiderListView(ListView):
    model = Rider
    template_name = 'rider_list.html'
    context_object_name = 'riders'


    def get_context_data(self, **kwargs):

        context = super(RiderListView, self).get_context_data(**kwargs)

        context['searchform'] = RiderSearchForm(self.request.GET)

        return context

    def get_queryset(self):

        if self.request.GET.has_key('name'):
            name = self.request.GET['name']
            return Rider.objects.filter(user__last_name__icontains=name)
        else:
            # just pull races after today
            return Rider.objects.all()

class RiderView(DetailView):

    model = User
    template_name = 'rider_detail.html'
    context_object_name = 'user'

class RiderUpdateView(UpdateView,ClubOfficialRequiredMixin):
    """View to allow update of rider and user details as well
    as grades and other associated objects"""

    template_name = "rider_update.html"
    model = User

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):

        # only ok if logged in user is this rider or
        # a club official
        if str(self.request.user.pk) == kwargs['pk'] or self.request.user.rider.official:
            return super(RiderUpdateView, self).dispatch(*args, **kwargs)
        else:
            return HttpResponseBadRequest()

    def get_form_class(self):

        if self.request.user.rider.official:
            return RiderUpdateFormOfficial
        else:
            return RiderUpdateForm

    def get_initial(self):
        """Return a dictionary with the initial values for the
        form, those for the rider, since the user fields are taken from
        self.object"""

        result = {
            'dutyofficer': len(self.object.userrole_set.filter(role__name__exact="Duty Officer")) > 0,
            'dutyhelper': len(self.object.userrole_set.filter(role__name__exact="Duty Helper")) > 0
        }

        riderdict = self.object.rider.__dict__

        result.update(riderdict)
        return result


    def form_valid(self, form):
        """Handle a valid form submission"""

        # update the rider object

        self.object.rider.__dict__.update(form.cleaned_data)
        self.object.rider.save()

        form.save()

        # userroles
        roles = UserRole.objects.filter(user=self.object, club=self.object.rider.club)
        print roles
        if form.cleaned_data['dutyofficer']:
            if not roles.filter(role__name__exact="Duty Officier"):
                dorole = ClubRole.objects.get(name="Duty Officer")
                do = UserRole(user=self.object, club=self.object.rider.club, role=dorole)
                do.save()
        else:
            if roles.filter(role__name__exact="Duty Officer"):
                roles.filter(role__name__exact="Duty Officer").delete()

        if form.cleaned_data['dutyhelper']:
            if not roles.filter(role__name__exact="Duty Helper"):
                dorole = ClubRole.objects.get(name="Duty Helper")
                do = UserRole(user=self.object, club=self.object.rider.club, role=dorole)
                do.save()
        else:
            if roles.filter(role__name__exact="Duty Helper"):
                roles.filter(role__name__exact="Duty Helper").delete()

        return HttpResponseRedirect(reverse('rider', kwargs={'pk': self.object.pk}))

class RaceListDateView(ListView):
    model = Race
    template_name = 'race_list.html'
    context_object_name = 'races'

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

    def post(self, request, **kwargs):
        """Handle the submission of a race update form to
        add or modify """

        pass


class RaceOfficialUpdateView(View):
    """Update the officials associated with a race

    Accept a POST request with a JSON payload and
    replace any existing officials with those in the
    JSON.

    Eg:
    {
    "<rolename>": [{ "id": "16574", "name": "Joe Bloggs"}],
    ...
    }
    """

    def post(self, request, *args, **kwargs):

        race = get_object_or_404(Race, **kwargs)

        try:
            officials = json.loads(request.body)
            nofficials = dict()
            for role in officials.keys():
                clubrole, created = ClubRole.objects.get_or_create(name=role)
                # find existing racestaff for this role
                staff = RaceStaff.objects.filter(race=race, role__name__exact=role)
                # remove them
                staff.delete()
                # create new ones corresponding to officials[role]
                # and add to newofficials
                nofficials[role] = []
                for person in officials[role]:
                    rider = get_object_or_404(Rider, id__exact=person['id'])
                    newracestaff = RaceStaff(rider=rider, role=clubrole, race=race)
                    newracestaff.save()
                    nofficials[role].append({'id': rider.id, 'name': str(rider)})

            return JsonResponse(nofficials)
        except ValueError as e:
            print e
            return HttpResponseBadRequest("could not parse JSON body")


class RaceUpdateView(ClubOfficialRequiredMixin, UpdateView):
    model = Race
    template_name = "race_form.html"
    fields = ['title', 'date', 'signontime', 'starttime', 'website', 'location', 'status', 'description']

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):

        race = get_object_or_404(Race, **kwargs)

        if self.request.user.rider.club == race.club and self.request.user.rider.official:
            return super(RaceUpdateView, self).dispatch(*args, **kwargs)
        else:
            return HttpResponseRedirect('/login/?next=%s' % self.request.path)

class RaceUploadExcelView(FormView):

    form_class = RaceCSVForm
    template_name = ''

    def form_valid(self, form):

        # need to work out what race we're in - from the URL pk
        race = get_object_or_404(Race, pk=self.kwargs['pk'])

        name, filetype = os.path.splitext(self.request.FILES['excelfile'].name)

        if filetype not in ['.xls', 'xlsx']:
            return HttpResponseBadRequest('Unknown file type, please use .xls or .xlsx')

        race.load_excel_results(self.request.FILES['excelfile'], filetype[1:])

        return HttpResponseRedirect(reverse('race', kwargs=self.kwargs))

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

class ClubRaceResultsView(DetailView):
    model = Club
    template_name = "club_results.html"
    context_object_name = 'club'

    def get_context_data(self, **kwargs):

        context = super(ClubRaceResultsView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the past races
        slug = self.kwargs['slug']
        club = Club.objects.get(slug=slug)

        context['races'] = Race.objects.filter(date__lt=datetime.date.today(), club__exact=club, status__exact='p')

        return context


class ClubRacesView(DetailView):
    model = Club
    template_name = "club_races_ajax.html"
    context_object_name = 'club'

    def get_context_data(self, **kwargs):

        context = super(ClubRacesView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the future races
        slug = self.kwargs['slug']
        club = Club.objects.get(slug=slug)

        if self.request.user.is_authenticated():
            context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club)
        else:
            context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club, status__exact='p')

        context['racecreateform'] = RaceCreateForm()

        context['commissaires'] = Rider.objects.filter(club__exact=club, commissaire_valid__gt=datetime.date.today()).order_by('user__last_name')
        context['dutyofficers'] = Rider.objects.filter(club__exact=club, user__userrole__role__name__exact='Duty Officer').order_by('user__last_name')
        context['dutyhelpers'] = Rider.objects.filter(club__exact=club, user__userrole__role__name__exact='Duty Helper').order_by('user__last_name')

        return context

    def post(self, request, **kwargs):
        """POST request handler to create new races for this club"""

        form = RaceCreateForm(request.POST)

        slug = self.kwargs['slug']
        club = Club.objects.get(slug=slug)

        if not request.user.rider or not request.user.rider.official or  request.user.rider.club != club:
            return HttpResponseBadRequest("Only available for club officials")

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
                    else:
                        # invalid option, raise an error
                        return HttpResponseBadRequest("Invalid repeat option")

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
        else:
            return HttpResponseBadRequest("Only Ajax requests supported")
