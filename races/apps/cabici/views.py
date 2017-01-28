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
from django.core.mail import EmailMessage, BadHeaderError
from django.contrib import messages
from django.db.models import Count


from django.contrib.auth.models import User
from races.apps.cabici.models import Race, Club, RaceCourse
from races.apps.cabici.usermodel import PointScore, Rider, RaceResult, ClubRole, RaceStaff, parse_img_members, UserRole, ClubGrade
from races.apps.cabici.forms import RaceCreateForm, RaceCSVForm, RaceRiderForm, MembershipUploadForm, RiderSearchForm, RiderUpdateForm, RiderUpdateFormOfficial, RacePublishDraftForm, ClubMemberEmailForm

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

        context['races'] = Race.objects.filter(date__gte=datetime.date.today(), club__exact=club).exclude(status__exact='w')[:5]

        context['form'] = RaceCreateForm()

        return context

class ClubOfficialRequiredMixin(AccessMixin):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        # superuser can do anything
        if not request.user.is_superuser:
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

class ClubRidersPromotionView(ListView):

    model = Club
    template_name = 'club_riders_primotion.html'

    def get_context_data(self, **kwargs):

        thisyear = datetime.date.today().year

        context = super(ClubRidersView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all riders who could be promoted
        slug = self.kwargs['slug']
        club = Club.objects.get(slug=slug)
        context['club'] = club
        # find riders who have won or placed with this club in the last 12 months
        # and count the number of wins/places
        riders = Rider.objects.filter(raceresult__race__date__gt=lastyear,
                                      raceresult__place__gte=5)
        riders = riders.annotate(Count('raceresult')).order_by('-raceresult__count')
        riders = riders.filter(raceresult__count__gt=3)



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
        thisyear = datetime.date.today().year

        # eventno won't be used but the java desktop app requires
        # a numer, make one out of the date
        eventno = str(datetime.date.today().strftime('%Y%m%d'))

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

        riders = Rider.objects.active_riders(club)

        for r in riders:

            grades = r.clubgrade_set.filter(club=club)
            if grades.count() > 0:
                grade = grades[0].grade
            else:
                grade = ''

            try:
                clubslug = r.club.slug
            except:
                clubslug = 'Unknown'

            # is the rider currently licenced?
            if r.membership_set.filter(year__exact=thisyear).count() == 1:
                registered = 'R'
            else:
                registered = 'U'

            row = (r.user.last_name,
                   r.user.first_name,
                   registered,
                   grade,
                   2,
                   'F',
                   '',
                   2,
                   r.licenceno,  # must be numeric
                   clubslug,
                   r.user.email,
                   r.id,
                   eventno  # must be numeric
                  )
            ws.append(row)

        sheet = pyexcel.Sheet(ws)
        io = StringIO()
        sheet.save_to_memory("xls", io)

        response = HttpResponse(io.getvalue(), content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="riders-%s.xls"' % eventno
        response['Content-Length'] = len(io.getvalue())

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

        riders = Rider.objects.all().order_by('user__last_name')

        # search by name just returns directly
        if self.request.GET.has_key('name') and self.request.GET['name'] != '':
            name = self.request.GET['name']
            riders = riders.filter(user__last_name__icontains=name).order_by('user__last_name')
            return riders

        # recent
        if self.request.GET.has_key('recent_wins'):
            # riders with a race win in the last 12 months
            lastyear = datetime.date.today()-datetime.timedelta(365)
            riders = riders.filter(raceresult__race__date__gt=lastyear,
                                          raceresult__place__exact=1)
            riders = riders.annotate(Count('raceresult')).order_by('-raceresult__count')
        elif self.request.GET.has_key('recent_places'):
            # riders with a race win in the last 12 months
            lastyear = datetime.date.today()-datetime.timedelta(365)
            riders = riders.filter(raceresult__race__date__gt=lastyear,
                                          raceresult__place__gte=5)
            riders = riders.annotate(Count('raceresult')).order_by('-raceresult__count')

        if self.request.GET.has_key('grade') and self.request.GET['grade'] != '':
            print "Filtering on grade", grade
            riders = riders.filter(raceresult__grade__exact=self.request.GET['grade'])

        if self.request.GET.has_key('club') and self.request.GET['club'] != '':
            club = get_object_or_404(Club, pk=self.request.GET['club'])
            riders = riders.filter(club__exact=club)

        return riders

class RiderView(DetailView):

    model = User
    template_name = 'rider_detail.html'
    context_object_name = 'user'

class RiderUpdateView(UpdateView,ClubOfficialRequiredMixin):
    """View to allow update of rider and user details as well
    as grades and other associated objects"""

    template_name = "rider_update.html"
    model = User
    context_object_name = 'user'

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
        # not sure why club doesn't update but let's do it explicitly
        result['club'] = self.object.rider.club
        return result


    def form_valid(self, form):
        """Handle a valid form submission"""

        # update the rider object

        self.object.rider.__dict__.update(form.cleaned_data)
        # not sure why I need to do this separately but it doesn't get
        # updated if I don't
        self.object.rider.club = form.cleaned_data['club']
        self.object.rider.save()

        form.save()

        # userroles
        roles = UserRole.objects.filter(user=self.object, club=self.object.rider.club)

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

            return Race.objects.filter(date__year=year, date__month=month).exclude(status__exact='w')
        else:
            # just pull races after today
            return Race.objects.filter(date__gte=datetime.date.today()).exclude(status__exact='w')

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
            return HttpResponseBadRequest("could not parse JSON body")


class RaceUpdateView(ClubOfficialRequiredMixin, UpdateView):
    model = Race
    template_name = "race_form.html"
    fields = ['title', 'date', 'signontime', 'starttime',
              'website', 'location', 'status', 'description',
              'licencereq', 'category', 'discipline']


class RaceUploadExcelView(FormView):

    form_class = RaceCSVForm
    template_name = ''

    def form_invalid(self, form):
        msgtext = 'Error: no file uploaded.'
        messages.add_message(self.request, messages.ERROR, msgtext, extra_tags='safe')
        return HttpResponseRedirect(reverse('race', kwargs=self.kwargs))


    def form_valid(self, form):

        # need to work out what race we're in - from the URL pk
        race = get_object_or_404(Race, pk=self.kwargs['pk'])

        name, filetype = os.path.splitext(self.request.FILES['excelfile'].name)

        if filetype not in ['.xls', 'xlsx']:
            msgtext = 'Error: Unknown file type, please use .xls or .xlsx'
            messages.add_message(self.request, messages.ERROR, msgtext, extra_tags='safe')
        else:
            try:
                user_messages = race.load_excel_results(self.request.FILES['excelfile'], filetype[1:])
                # pass the messages to the user
                if messages != []:
                    msgtext = '<h4>Upload Complete</h4><ul><li>' + '</li><li>'.join(user_messages) + '</li></ul>'
                    messages.add_message(self.request, messages.INFO, msgtext, extra_tags='safe')
            except Exception as e:
                msgtext = "Error reading file, please check format."
                print e
                messages.add_message(self.request, messages.ERROR, msgtext, extra_tags='safe')

        return HttpResponseRedirect(reverse('race', kwargs=self.kwargs))


class RacePublishDraftView(FormView,ClubOfficialRequiredMixin):
    """View to publish all draft races for a club"""

    form_class = RacePublishDraftForm
    template_name = 'index.html'

    def form_valid(self, form):

        club = get_object_or_404(Club, slug=self.kwargs['slug'])

        # find all draft races and make them Published
        for race in club.races.filter(status__exact='d'):
            race.status = 'p'
            race.save()

        return HttpResponseRedirect(reverse('club_races', kwargs=self.kwargs))

    def form_invalid(self, form):

        return HttpResponseRedirect(reverse('club_races', kwargs=self.kwargs))

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

        context['races'] = Race.objects.filter(date__lt=datetime.date.today(),
                                               club__exact=club,
                                               raceresult__rider__isnull=False,
                                               status__exact='p').distinct()

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

        # are we allowed to do this?
        if not request.user.is_superuser and \
           (not request.user.rider or \
           not request.user.rider.official or \
           request.user.rider.club != club):
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

class ClubRacesOfficalUpdateView(DetailView):
    model = Club
    template_name = "club_races_officials.html"
    context_object_name = 'club'

    def get_context_data(self, **kwargs):

        context = super(ClubRacesOfficalUpdateView, self).get_context_data(**kwargs)
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


    def post(self, request, *args, **kwargs):
        """Allocate officials at random to
        all future races"""

        slug = self.kwargs['slug']
        club = Club.objects.get(slug=slug)

        user = self.request.user

        if not (user.is_authenticated() and user.rider.official and user.rider.club == club):
            return HttpResponseBadRequest('Not authorised.')

        # find future races
        races = club.races.filter(date__gte=datetime.date.today())

        # allocate duty helpers
        club.allocate_officials('Duty Helper', 2, races, replace=False)

        # and duty officers
        club.allocate_officials('Duty Officer', 1, races, replace=False)

        # commisaires?

        # redirect to race schedule page
        return HttpResponseRedirect(reverse('club_races', kwargs={'slug': club.slug}))

class ClubMemberEmailView(FormView,ClubOfficialRequiredMixin):
    """View to send emails to some or all members of a club"""

    form_class = ClubMemberEmailForm
    template_name = 'send_email.html'

    def get_context_data(self, **kwargs):

        context = super(ClubMemberEmailView, self).get_context_data(**kwargs)
        slug = self.kwargs['slug']
        context['club'] = Club.objects.get(slug=slug)

        return context

    def form_valid(self, form):

        club = get_object_or_404(Club, slug=self.kwargs['slug'])

        thisyear = datetime.date.today().year
        # sender will be the logged in user
        sender = self.request.user.email

        sendto = form.cleaned_data['sendto']
        reply_to = 'dontreply@cabici.net'

        if sendto == 'members':
            recipients = Rider.objects.filter(club__exact=club, membership__year__gte=thisyear)
        elif sendto == 'commisaires':
            uroles = UserRole.objects.filter(club__exact=club, role__name__exact='Commissaire')
            recipients = [ur.user.rider for ur in uroles]
        elif sendto == 'dutyofficers':
            uroles = UserRole.objects.filter(club__exact=club, role__name__exact='Duty Officer')
            recipients = [ur.user.rider for ur in uroles]
        elif sendto == 'self':
            recipients = [self.request.user.rider]

        subject = form.cleaned_data['subject']

        email = EmailMessage(
                             subject,
                             form.cleaned_data['message'],
                             sender,
                             [],
                             [r.user.email for r in recipients],
                             reply_to=(reply_to,)
                             )

        try:
            email.send(fail_silently=False)
        except BadHeaderError:
            return HttpResponseBadRequest('Invalid email header found.')

        messages.add_message(self.request, messages.INFO, 'Message sent to %d recipients' % (len(recipients)))
        return HttpResponseRedirect(reverse('club_dashboard', kwargs=self.kwargs))

    def form_invalid(self, form):

        return HttpResponseRedirect(reverse('club_dashboard', kwargs=self.kwargs))
