from django import template
from races.apps.cabici.usermodel import ClubGrade
from races.apps.cabici.models import Club

register = template.Library()


@register.simple_tag
def clubgrade(club, rider):
    """Return the grade of this rider for this club"""

    try:
        return ClubGrade.objects.get(club=club, rider=rider).grade
    except:
        return "None"

@register.simple_tag
def clubwins(club, rider):
    """Return the number of wins of this rider for this club"""

    try:
        return club.performancereport(rider=rider)['wins']
    except:
        return 0

@register.simple_tag
def clubplaces(club, rider):
    """Return the number of places (1-3) of this rider for this club"""

    try:
        return club.performancereport(rider=rider)['places']
    except:
        return 0
