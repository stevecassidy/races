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
import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.contrib.flatpages.models import FlatPage
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from races.apps.cabici.models import Club, Race


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
