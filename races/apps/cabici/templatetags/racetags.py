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

from django import template

from races.apps.cabici.models import ClubGrade
from races.apps.cabici.services.officials import performance_report

register = template.Library()


@register.simple_tag
def clubgrade(club, rider):
    """Return the grade of this rider for this club"""

    try:
        return ClubGrade.objects.get(club=club, rider=rider).grade
    except Exception:
        return ""


@register.simple_tag
def clubwins(club, rider):
    """Return the number of wins of this rider for this club"""

    try:
        return performance_report(club, rider)["wins"]
    except Exception:
        return 0


@register.simple_tag
def clubplaces(club, rider):
    """Return the number of places (1-3) of this rider for this club"""

    try:
        return performance_report(club, rider)["places"]
    except Exception:
        return 0
