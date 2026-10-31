"""FilterSet definitions for the v1 API contract."""

import django_filters

from races.apps.cabici.models import Club, ClubRole, PointScore, Race, RaceCourse, RaceResult, Rider, UserRole


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


class RaceCourseFilter(django_filters.FilterSet):
    class Meta:
        model = RaceCourse
        fields = {
            "name": ["exact", "icontains"],
            "shortname": ["exact", "icontains"],
        }


class RaceResultFilter(django_filters.FilterSet):
    race = django_filters.NumberFilter(field_name="race_id")
    rider = django_filters.NumberFilter(field_name="rider_id")
    place_after = django_filters.NumberFilter(field_name="place", lookup_expr="gte")
    place_before = django_filters.NumberFilter(field_name="place", lookup_expr="lte")
    dnf = django_filters.BooleanFilter()

    class Meta:
        model = RaceResult
        fields = {
            "race": ["exact"],
            "rider": ["exact"],
            "grade": ["exact", "icontains"],
            "usual_grade": ["exact", "icontains"],
            "dnf": ["exact"],
            "place": ["exact", "gte", "lte"],
        }


class ClubRoleFilter(django_filters.FilterSet):
    class Meta:
        model = ClubRole
        fields = {
            "name": ["exact", "icontains"],
        }


class UserRoleFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name="user_id")
    club = django_filters.NumberFilter(field_name="club_id")
    role = django_filters.NumberFilter(field_name="role_id")

    class Meta:
        model = UserRole
        fields = {
            "user": ["exact"],
            "club": ["exact"],
            "role": ["exact"],
        }
