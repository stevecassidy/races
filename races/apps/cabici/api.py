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

"""Serializers for the REST API"""

import datetime
import json
import os
import time

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, permissions, relations, serializers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException, ParseError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse

from .models import (
    Club,
    ClubRole,
    PointScore,
    Race,
    RaceCourse,
    RaceResult,
    RaceStaff,
    Rider,
    UserRole,
)
from .services.officials import classification as rider_classification
from .services.results import ResultUploadError, upload_results


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination class for requests that return large numbers of results"""

    page_size = 200
    page_size_query_param = "page_size"
    max_page_size = 1000


@api_view(("GET",))
@permission_classes((permissions.AllowAny,))
def api_root(request, format=None):
    return Response(
        {
            "clubs": reverse("club-list", request=request, format=format),
            "races": reverse("race-list", request=request, format=format),
            "racecourses": reverse("racecourse-list", request=request, format=format),
            "riders": reverse("rider-list", request=request, format=format),
            "pointscores": reverse("pointscore-list", request=request, format=format),
            "raceresults": reverse("raceresult-list", request=request, format=format),
        }
    )


class CustomAuthTokenSerializer(serializers.Serializer):
    """Provide a custom response to a request for an auth token
    uses email rather than username to authenticate and
    returns a slightly richer JSON response than the
    default"""

    email = serializers.CharField(label=_("Email"))
    password = serializers.CharField(label=_("Password"), style={"input_type": "password"}, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:

            user_from_email = User.objects.get(email__iexact=email)
            if not user_from_email:
                msg = _("Email not valid")
                raise serializers.ValidationError(msg, code="authorization")

            username = user_from_email.username

            user = authenticate(request=self.context.get("request"), username=username, password=password)
            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            if not user:
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg, code="authorization")
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class CustomAuthToken(ObtainAuthToken):
    """Define a custom response to token authentication request
    Use email rather than username and return some additional user
    information"""

    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "club": user.rider.club.slug,
                "official": user.rider.official,
            }
        )


# TODO: authentication for create/update/delete views
# ---------------Permissions-----------------


class ClubOfficialPermission(permissions.BasePermission):
    """Permission only for officials of a club"""

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        # anonymous user can't do anything unsafe
        if not request.user.is_authenticated:
            return False

        # superuser can do anything
        if request.user.is_superuser:
            return True

        # user should be an official of the club referenced in the view
        return request.user.rider.official

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        # anonymous user can't do anything unsafe
        if not request.user.is_authenticated:
            return False

        # superuser can do anything
        if request.user.is_superuser:
            return True

        # user should be an official of the club referenced in the view
        if not request.user.rider.official:
            return False

        # if they are an official then they can operate on their club
        # races or members
        if isinstance(obj, Race | Rider):
            club = obj.club
        elif isinstance(obj, RaceResult):
            club = obj.race.club
        elif isinstance(obj, UserRole):
            club = obj.club
        else:
            return False

        return request.user.rider.club == club


class RaceResultPermission(permissions.BasePermission):
    """Write access to race results belongs to officials of the race's club.

    Reads stay open (the result list is public). The upload is a
    collection-level write whose race arrives in the request body, so the club
    check has to happen in ``has_permission``; the detail route checks the
    result's own race in ``has_object_permission`` (D3).
    """

    message = "Only officials of the race's club may change results."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        race = self._race_from_body(request)
        return self._is_club_official(request, race.club_id if race is not None else None)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not isinstance(obj, RaceResult):
            return False

        return self._is_club_official(request, obj.race.club_id)

    @staticmethod
    def _race_from_body(request):
        """Resolve the race named in an upload body, or None.

        A missing or malformed race is left for the view to reject with its
        usual error; validating the payload is not this permission's job.
        """

        data = getattr(request, "data", None)
        if not isinstance(data, dict) or not data.get("race"):
            return None
        try:
            return Race.objects.filter(pk=data["race"]).first()
        except TypeError, ValueError:
            return None

    @staticmethod
    def _is_club_official(request, club_id):
        """Is the request user an official of ``club_id`` (or a superuser)?

        ``getattr`` is deliberate: a User need not have a Rider, and an
        unguarded ``request.user.rider`` raises inside the permission check,
        turning a 403 into a 500.
        """

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        rider = getattr(user, "rider", None)
        if rider is None or not rider.official:
            return False
        if club_id is None:
            # no race to compare against; the view will reject the payload
            return True
        return rider.club_id == club_id


# ---------------Club------------------


class ClubSerializer(serializers.HyperlinkedModelSerializer):

    races = serializers.HyperlinkedRelatedField(many=True, queryset=Race.objects.all(), view_name="race-detail")
    url = relations.HyperlinkedIdentityField(lookup_field="slug", view_name="club-detail")

    class Meta:
        model = Club
        fields = ("url", "name", "slug", "website", "races")


class ClubBriefSerializer(serializers.ModelSerializer):

    class Meta:
        model = Club
        fields = ("name", "id", "slug", "manage_members")


class ClubList(generics.ListCreateAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer


class ClubDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    lookup_field = "slug"


class UserRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserRole
        fields = ("id", "user", "club", "role")

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["role"] = instance.role.name
        result["club"] = instance.club.slug
        return result

    def to_internal_value(self, data):
        role, created = ClubRole.objects.get_or_create(name=data["role"])

        rider = Rider.objects.filter(pk=data["rider"])
        club = Club.objects.filter(slug=data["club"])

        errors = {}
        if rider.count() == 0:
            errors["rider"] = "invalid rider id"
        if club.count() == 0:
            errors["club"] = "invalid club id"
        if errors != {}:
            raise serializers.ValidationError(errors)

        return {"user": rider[0].user, "club": club[0], "role": role}


class UserRolesView(generics.ListCreateAPIView):

    serializer_class = UserRoleSerializer

    def get_queryset(self):

        slug = self.request.resolver_match.kwargs["slug"]
        return UserRole.objects.filter(club__slug__exact=slug)


@permission_classes((ClubOfficialPermission,))
class UserRoleDestroyView(generics.RetrieveDestroyAPIView):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer


# ---------------RaceCourse------------------


class RaceCourseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceCourse
        fields = "__all__"


class RaceCourseBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = RaceCourse
        fields = "__all__"


class RaceCourseList(generics.ListCreateAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer


class RaceCourseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer


# ---------------Race------------------


class RaceOfficialField(serializers.Field):
    """Custom field to return a representation of officials at a race
    note: read only, to modify officials use racesstaff-detail view"""

    def to_representation(self, obj):

        result = {}
        for role in obj.distinct():
            entry = {"id": role.rider.id, "name": role.rider.user.first_name + " " + role.rider.user.last_name}
            if role.role.name not in result:
                result[role.role.name] = [entry]
            else:
                result[role.role.name].append(entry)

        return result

    def to_internal_value(self, data):

        print("TIV", data)

        return []


class RaceSerializer(serializers.ModelSerializer):
    # TODO: we want these fields to be expanded when we read the data
    # but we only want to specify the ID when we update/create
    club = ClubBriefSerializer(read_only=True)
    location = RaceCourseBriefSerializer(read_only=True)
    officials = RaceOfficialField(read_only=True)

    discipline = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    licencereq = serializers.SerializerMethodField()
    pointscore = serializers.SerializerMethodField()

    class Meta:
        model = Race
        fields = (
            "id",
            "url",
            "club",
            "location",
            "title",
            "date",
            "signontime",
            "starttime",
            "website",
            "status",
            "description",
            "officials",
            "discipline",
            "category",
            "licencereq",
            "grading",
            "pointscore",
        )

    def get_discipline(self, obj):
        return {"key": obj.discipline, "display": obj.get_discipline_display()}

    def get_category(self, obj):
        return {"key": obj.category, "display": obj.get_category_display()}

    def get_licencereq(self, obj):
        return {"key": obj.licencereq, "display": obj.get_licencereq_display()}

    def get_pointscore(self, obj):
        pointscore = obj.pointscore_set.all()
        if pointscore.count() > 0:
            return {"key": pointscore[0].id, "display": str(pointscore[0])}
        else:
            return {"key": None, "display": ""}


@permission_classes((ClubOfficialPermission,))
class RaceList(generics.ListCreateAPIView):
    serializer_class = RaceSerializer

    def get_queryset(self):

        clubslug = self.request.query_params.get("club", None)
        select = self.request.query_params.get("select", None)
        count = self.request.query_params.get("count", None)

        races = Race.objects.all()

        # if user is a club official, include draft races
        if getattr(self.request.user, "rider", None) is not None and self.request.user.rider.official:
            pass
        else:
            # no draft or withdrawn races
            races = races.exclude(status__exact="d").exclude(status__exact="w")

        if clubslug is not None:
            races = races.filter(club__slug__exact=clubslug)

        if select == "future":
            races = races.filter(date__gte=datetime.date.today())
        elif select == "recent":
            races = races.filter(date__lte=datetime.date.today()).order_by("-date")
        elif select == "raceday":
            today = datetime.date.today()
            future = today + datetime.timedelta(days=30)
            past = today - datetime.timedelta(days=30)
            races = races.filter(date__lte=future, date__gte=past).order_by("-date")
        elif select == "results":
            races = races.filter(raceresult__rider__isnull=False).distinct().order_by("-date")

        # count needs to be an integer
        if count is not None:
            try:
                count = int(count)
            except TypeError, ValueError:
                count = None
            if count is not None:
                races = races[:count]

        return races


@permission_classes((ClubOfficialPermission,))
class RaceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Race.objects.all()
    serializer_class = RaceSerializer


# ---------------RaceStaff------------------


class RaceStaffSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceStaff
        fields = "__all__"

    role = serializers.SlugRelatedField(slug_field="name", queryset=ClubRole.objects.all())


class RaceStaffList(generics.ListCreateAPIView):
    queryset = RaceStaff.objects.all()
    serializer_class = RaceStaffSerializer


@permission_classes((ClubOfficialPermission,))
class RaceStaffDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceStaff.objects.all()
    serializer_class = RaceStaffSerializer


# ---------------Rider------------------


class RiderSerializer(serializers.HyperlinkedModelSerializer):

    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    club = serializers.CharField(source="club.name", read_only=True)
    clubslug = serializers.CharField(source="club.slug", read_only=True)
    classification = serializers.SerializerMethodField()

    def get_classification(self, rider):
        return rider_classification(rider)

    class Meta:
        model = Rider
        fields = (
            "id",
            "first_name",
            "last_name",
            "club",
            "clubslug",
            "licenceno",
            "classification",
            "member_category",
            "member_date",
            "grades",
            "gender",
            "emergencyphone",
            "emergencyname",
            "updated",
        )


class RiderList(generics.ListCreateAPIView):
    # require authentication to access rider list API
    permission_classes = (IsAuthenticated,)
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):

        clubid = self.request.query_params.get("club", None)
        commissaire = self.request.query_params.get("commissaire", None)
        prefix = self.request.query_params.get("prefix", None)
        changed = self.request.query_params.get("changed", None)

        if clubid is not None:
            if commissaire is not None:
                riders = Rider.objects.filter(club__pk__exact=clubid, commissaire_valid__gt=datetime.date.today())
            else:
                riders = Rider.objects.filter(club__pk__exact=clubid)
        else:
            riders = Rider.objects.all()

        if prefix is not None:
            riders = riders.filter(user__last_name__istartswith=prefix)

        if changed:
            try:
                changed = datetime.datetime.fromtimestamp(int(changed), datetime.UTC)
                riders = riders.filter(user__rider__updated__gt=changed)
            except ValueError as exc:
                raise APIException("Bad timestamp format for changed argument") from exc

        riders = riders.select_related("user", "club")

        return riders.order_by("user__last_name")


@permission_classes((ClubOfficialPermission,))
class RiderDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer


# ---------------PointScore------------------


class PointScoreBriefSerializer(serializers.HyperlinkedModelSerializer):

    club = ClubBriefSerializer(read_only=True)

    class Meta:
        model = PointScore
        fields = ("url", "club", "name")


class PointScoreList(generics.ListCreateAPIView):
    serializer_class = PointScoreBriefSerializer

    def get_queryset(self):
        """Allow filtering of queryset by a URL query
        parameter ?club=SLUG
        """

        clubslug = self.request.query_params.get("club", None)
        ps = PointScore.objects.all()

        if clubslug is not None:
            ps = ps.filter(club__slug__exact=clubslug)

        return ps


class PointScoreSerializer(serializers.HyperlinkedModelSerializer):

    results = serializers.SerializerMethodField("result_list")
    club = serializers.SerializerMethodField("club_name")

    def club_name(self, ps):
        return ps.club.name

    def result_list(self, ps):

        queryset = ps.tabulate()

        return [
            {
                "rider": " ".join((tally.rider.user.first_name, tally.rider.user.last_name)),
                "riderid": tally.rider.user.id,
                "club": tally.rider.club.slug if tally.rider.club else "Unknown",  # avoid crash if no club
                "grade": tally.pointscore.club.grade(tally.rider),
                "points": tally.points,
                "eventcount": tally.eventcount,
            }
            for tally in queryset
        ]

    class Meta:
        model = PointScore
        fields = ("name", "club", "results")


@permission_classes((ClubOfficialPermission,))
class PointScoreDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PointScore.objects.all()
    serializer_class = PointScoreSerializer


# ---------------RaceResult------------------


class RaceResultSerializer(serializers.ModelSerializer):

    rider = serializers.SerializerMethodField("rider_name")
    riderid = serializers.SerializerMethodField("rider_id")
    club = serializers.SerializerMethodField("club_name")
    grade_change = serializers.SerializerMethodField("grade_change_flag")

    def grade_change_flag(self, result):
        """A9: did this result move the rider's grade?

        Derived rather than stored, so a download/upload round trip keeps the
        flag instead of resetting it to false -- the old response omitted it.
        """

        return bool(result.usual_grade) and result.grade != result.usual_grade

    def club_name(self, result):
        if result.rider.club is not None:
            return result.rider.club.name
        else:
            return "Unknown"

    def rider_name(self, result):
        return str(result.rider)

    def rider_id(self, result):
        return result.rider.id

    class Meta:
        model = RaceResult
        fields = "__all__"


@permission_classes((RaceResultPermission,))
class RaceResultList(generics.ListCreateAPIView):

    serializer_class = RaceResultSerializer

    def get_queryset(self):

        raceid = self.request.query_params.get("race", None)
        placed = self.request.query_params.get("placed", None)

        try:
            if raceid is not None:
                if placed is not None:
                    return RaceResult.objects.filter(race__pk__exact=raceid, place__gt=0).select_related(
                        "rider", "rider__user"
                    )
                else:
                    return RaceResult.objects.filter(race__pk__exact=raceid).select_related("rider", "rider__user")
            else:
                # should be all results but that would be too many
                # and we'd never actually want that so return nothing
                return RaceResult.objects.none()

        except ValueError as exc:
            # given a non integer for raceid
            raise Http404("Invalid Race ID") from exc

    def post(self, request, *args, **kwargs):
        """Handle post payload containing entries and new riders.

        The operation itself lives in ``services.results``; this is only the
        HTTP projection -- stash the payload for debugging, map a rejected
        payload to a 400, and shape the response.
        """

        data = request.data

        # stash the payload in a file for later analysis
        if settings.SAVE_RESULT_UPLOADS:
            if not os.path.exists(settings.SAVE_RESULT_UPLOADS_DIR):
                os.makedirs(settings.SAVE_RESULT_UPLOADS_DIR)
            filename = os.path.join(settings.SAVE_RESULT_UPLOADS_DIR, f"{data.get('race')}-{time.time()}.json")
            with open(filename, "w") as fd:
                json.dump(data, fd, indent=2)

        try:
            result = upload_results(data)
        except ResultUploadError as exc:
            raise ParseError(str(exc)) from exc

        return Response(
            {
                "message": "race results uploaded",
                "errors": result.errors,
                "ridermap": result.ridermap,
                "deleted": result.deleted,
                "created": result.created,
            }
        )


@permission_classes((RaceResultPermission,))
class RaceResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceResult.objects.all()
    serializer_class = RaceResultSerializer
