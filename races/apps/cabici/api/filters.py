"""FilterSet definitions for the v1 API contract."""

import django_filters

from races.apps.cabici.models import Club, PointScore, Race, Rider


class ClubFilter(django_filters.FilterSet):
    class Meta:
        model = Club
        fields = {
            "slug": ["exact", "icontains"],
            "manage_races": ["exact"],
            "manage_members": ["exact"],
            "manage_results": ["exact"],
        }


class RiderFilter(django_filters.FilterSet):
    club = django_filters.NumberFilter(field_name="club_id")
    official = django_filters.BooleanFilter()
    gender = django_filters.CharFilter()
    email = django_filters.CharFilter(field_name="user__email", lookup_expr="icontains")

    class Meta:
        model = Rider
        fields = {
            "club": ["exact"],
            "official": ["exact"],
            "gender": ["exact", "icontains"],
            "licenceno": ["exact", "icontains"],
            "user__first_name": ["icontains"],
            "user__last_name": ["icontains"],
        }


class RaceFilter(django_filters.FilterSet):
    club = django_filters.NumberFilter(field_name="club_id")
    date_after = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_before = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Race
        fields = {
            "club": ["exact"],
            "status": ["exact", "in"],
            "discipline": ["exact", "in"],
            "category": ["exact", "in"],
            "date": ["exact", "gte", "lte"],
        }


class PointScoreFilter(django_filters.FilterSet):
    club = django_filters.NumberFilter(field_name="club_id")

    class Meta:
        model = PointScore
        fields = {
            "club": ["exact"],
            "name": ["exact", "icontains"],
        }
