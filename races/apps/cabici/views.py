#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import csv
import datetime
from io import BytesIO

import pyexcel
from dateutil.rrule import FR, MO, SA, SU, TH, TU, WE
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.contrib.flatpages.models import FlatPage
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import ListView, View

from races.apps.cabici.models import Club, Race
from races.apps.cabici.usermodel import RaceResult, Rider

DAYS = [MO, TU, WE, TH, FR, SA, SU]


class HomePage(ListView):
    model = Race
    template_name = "index.html"

    def get_queryset(self):
        # show the races for the next week
        startdate = datetime.date.today()
        enddate = startdate + datetime.timedelta(days=14)
        return Race.objects.filter(date__gte=startdate, date__lt=enddate, status__exact="p")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        pages = FlatPage.objects.filter(url="/")
        if len(pages) == 1:
            context["page"] = pages[0]
        else:
            context["page"] = {
                "title": "Content",
            }
        return context


class ClubOfficialRequiredMixin(AccessMixin):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        # superuser can do anything
        if not request.user.is_superuser:
            # any user who has no rider object can't get access
            if not hasattr(request.user, "rider"):
                return self.handle_no_permission()
            rider = request.user.rider

            # user should be an official of the club referenced in the view
            if not rider.official:
                return self.handle_no_permission()

            # if there is a club slug in the kwargs then verify that
            # the official is a member of that club
            if "slug" in kwargs:
                clublist = Club.objects.filter(slug=kwargs["slug"])
                if len(clublist) == 1:
                    club = clublist[0]
                    if rider.club != club:
                        return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


@login_required()
def club_riders_csv_view(request, slug):
    """View of club members as a csv file"""

    today = datetime.date.today()

    club = get_object_or_404(Club, slug=slug)

    # validate the user
    if (
        not hasattr(request.user, "rider")
        or request.user.rider.club != club
        and not request.user.rider.official
        and not request.user.is_staff
    ):
        return HttpResponseNotAllowed("Must be a Club Official")

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="members.csv"'

    members = club.rider_set.filter(membership__date__gte=today).distinct().order_by("user__last_name")

    writer = csv.writer(response)
    writer.writerow(["Name", "Grade", "State Grade", "Phone", "Email", "Membership", "Date"])
    for member in members:
        grade = member.clubgrade_set.filter(club__exact=club)
        if grade.count() == 0:
            grade = ""
        else:
            grade = grade[0].grade

        stategrade = member.clubgrade_set.filter(club__slug__exact="CNSW")
        if stategrade.count() == 0:
            stategrade = ""
        else:
            stategrade = stategrade[0].grade

        row = [
            str(member),
            grade,
            stategrade,
            member.phone,
            member.user.email,
            member.member_category,
            member.member_date,
        ]
        writer.writerow(row)

    return response


class ClubRidersExcelView(View):

    def get(self, request, *args, **kwargs):

        club = get_object_or_404(Club, slug=kwargs["slug"])

        # worksheet is a list of row tuples
        ws = []
        today = datetime.date.today()

        # eventno won't be used but the java desktop app requires
        # a number, make one out of the date
        eventno = str(datetime.date.today().strftime("%Y%m%d"))

        header = (
            "LastName",
            "FirstName",
            "Regd",  # U/R
            "Grade",
            "HCap",
            "Fee",
            "ShirtNo",
            "Points",
            "LicenceNo",
            "Club",
            "Email",
            "Id",
            "EventNo",
        )

        ws.append(header)

        riders = Rider.objects.all().select_related("user", "club")

        for r in riders:

            grades = r.clubgrade_set.filter(club=club)
            if grades.count() > 0:
                grade = grades[0].grade
            else:
                grade = ""

            clubslug = r.club.slug if r.club else "Unknown"

            # is the rider currently licenced to race?
            if r.membership_set.filter(category="race", date__gte=today).count() == 1:
                registered = "R"
            else:
                registered = "U"

            row = (
                r.user.last_name,
                r.user.first_name,
                registered,
                grade,
                2,
                "F",
                "",
                2,
                r.licenceno,  # must be numeric
                clubslug,
                r.user.email,
                r.id,
                eventno,  # must be numeric
            )
            ws.append(row)

        sheet = pyexcel.Sheet(ws)
        io = BytesIO()
        sheet.save_to_memory("xls", io)

        response = HttpResponse(io.getvalue(), content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename="riders-%s.xls"' % eventno
        response["Content-Length"] = len(io.getvalue())

        return response


class RaceSummarySpreadsheet(View):
    model = Race

    def get(self, request, *args, **kwargs):

        race = get_object_or_404(Race, pk=kwargs["pk"])

        # worksheet is a list of row tuples
        ws = []

        results = RaceResult.objects.filter(race__exact=race)

        ws.append(("Race Date", race.date, "", "", "", "", "", "", "", ""))
        ws.append(("Race Name", race.title, "", "", "", "", "", "", "", ""))
        ws.append(("Club", race.club.slug, "", "", "", "", "", "", "", ""))
        ws.append(("Venue", race.location.name, "", "", "", "", "", "", "", ""))
        ws.append(("", "", "", "", "", "", "", "", "", ""))

        header = (
            "LastName",
            "FirstName",
            "Grade",
            "ShirtNo",
            "Place",
            "LicenceNo",
            "Club",
            "Email",
            "Id",
            "Date",
        )

        ws.append(header)

        for result in results:

            rider = result.rider
            clubslug = rider.club.slug if rider.club else "Unknown"

            row = (
                rider.user.last_name,
                rider.user.first_name,
                result.grade,
                result.number,
                result.place or "",
                rider.licenceno,
                clubslug,
                rider.user.email,
                rider.id,
                race.date,
            )
            assert len(row) == len(header)
            ws.append(row)

        sheet = pyexcel.Sheet(ws)
        io = BytesIO()
        sheet.save_to_memory("xls", io)

        response = HttpResponse(io.getvalue(), content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename="%s-%s-%s.xls"' % (
            race.date,
            race.club.slug,
            race.location.name,
        )
        response["Content-Length"] = len(io.getvalue())

        return response
