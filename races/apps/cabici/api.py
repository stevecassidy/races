"""Serializers for the REST API"""

from rest_framework import serializers, generics, permissions, relations
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
import datetime
from django.db import models
from django.http import Http404

from models import Club, Race, RaceCourse
from usermodel import Rider, PointScore, RaceResult, RaceStaff, ClubRole, PointscoreTally


@api_view(('GET',))
@permission_classes((permissions.AllowAny,))
def api_root(request, format=None):
    return Response({
        'clubs': reverse('club-list', request=request, format=format),
        'races': reverse('race-list', request=request, format=format),
        'racecourses': reverse('racecourse-list', request=request, format=format),
        #'riders': reverse('rider-list', request=request, format=format),
        'pointscores': reverse('pointscore-list', request=request, format=format),
        'raceresults': reverse('raceresult-list', request=request, format=format),
    })


# TODO: authentication for create/update/delete views
#---------------Permissions-----------------

class ClubOfficialPermission(permissions.BasePermission):
    """Permission only for officials of a club"""

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        # anonymous user can't do anything unsafe
        if not request.user.is_authenticated():
            return False

        # superuser can do anything
        if request.user.is_superuser:
            return True

        # user should be an official of the club referenced in the view
        if not request.user.rider.official:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        # anonymous user can't do anything unsafe
        if not request.user.is_authenticated():
            return False

        # superuser can do anything
        if request.user.is_superuser:
            return True

        # user should be an official of the club referenced in the view
        if not request.user.rider.official:
            return False

        # if they are an official then they can operate on their club
        # races or members
        if isinstance(obj, Race) or isinstance(obj, Rider):
            club = obj.club
        elif isinstance(obj, RaceResult):
            club = obj.race.club
        else:
            print request.user, "not whatever"
            return False

        return request.user.rider.club == club

#---------------Club------------------

class ClubSerializer(serializers.HyperlinkedModelSerializer):

    races = serializers.HyperlinkedRelatedField(many=True, queryset=Race.objects.all(), view_name='race-detail')
    url = relations.HyperlinkedIdentityField(lookup_field='slug', view_name='club-detail')
    class Meta:
        model = Club
        fields = ('url', 'name','slug', 'website', 'races')

class ClubBriefSerializer(serializers.ModelSerializer):

    class Meta:
        model = Club
        fields = ('name', 'id', 'slug')

class ClubList(generics.ListCreateAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer

class ClubDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    lookup_field = 'slug'

#---------------RaceCourse------------------

class RaceCourseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceCourse

class RaceCourseBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = RaceCourse

class RaceCourseList(generics.ListCreateAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer

class RaceCourseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer

#---------------Race------------------


class RaceOfficialField(serializers.Field):
    """Custom field to return a representation of officials at a race
    note: read only, to modify officials use racesstaff-detail view"""

    def to_representation(self, obj):

        result = dict()
        for role in obj.distinct():
            entry = {'id': role.rider.id, 'name': role.rider.user.first_name + " " + role.rider.user.last_name}
            if role.role.name not in result:
                result[role.role.name] = [entry]
            else:
                result[role.role.name].append(entry)

        return result


    def to_internal_value(self, data):

        print "TIV", data

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

    class Meta:
        model = Race
        fields = ('id', 'url', 'club', 'location', 'title', 'date', 'signontime', 'starttime', 'website', 'status', 'description', 'officials', 'discipline', 'category', 'licencereq')

    def get_discipline(self, obj):
        return {'key': obj.discipline, 'display': obj.get_discipline_display()}

    def get_category(self, obj):
        return {'key': obj.category, 'display': obj.get_category_display()}

    def get_licencereq(self, obj):
        return {'key': obj.licencereq, 'display': obj.get_licencereq_display()}

@permission_classes((ClubOfficialPermission,))
class RaceList(generics.ListCreateAPIView):
    serializer_class = RaceSerializer

    def get_queryset(self):

        clubslug = self.request.query_params.get('club', None)
        select = self.request.query_params.get('select', None)
        count = self.request.query_params.get('count', None)

        races = Race.objects.all()

        # if user is a club official, include draft races
        if getattr(self.request.user, 'rider', None) is not None and self.request.user.rider.official:
            pass
        else:
            # no draft or withdrawn races
            races = races.exclude(status__exact="d").exclude(status__exact="w")

        if clubslug is not None:
            races = races.filter(club__slug__exact=clubslug)

        if select == 'future':
            races = races.filter(date__gte=datetime.date.today())
        elif select == 'recent':
            races = races.filter(date__lte=datetime.date.today()).order_by('-date')
        elif select == 'results':
            races = races.filter(raceresult__rider__isnull=False).distinct().order_by('-date')

        # count needs to be an integer
        if count is not None:
            try:
                count = int(count)
                races = races[:count]
            except:
                pass

        return races

@permission_classes((ClubOfficialPermission,))
class RaceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Race.objects.all()
    serializer_class = RaceSerializer

#---------------RaceStaff------------------

class RaceStaffSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceStaff

    role = serializers.SlugRelatedField(slug_field='name', queryset=ClubRole.objects.all())

class RaceStaffList(generics.ListCreateAPIView):
    queryset = RaceStaff.objects.all()
    serializer_class = RaceStaffSerializer

@permission_classes((ClubOfficialPermission,))
class RaceStaffDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceStaff.objects.all()
    serializer_class = RaceStaffSerializer

#---------------Rider------------------

from django.contrib.auth.models import User

class UserSerializer(serializers.HyperlinkedModelSerializer):
    #rider = serializers.HyperlinkedRelatedField(many=False, queryset=Rider.objects.all(), view_name='rider-detail')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name')

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class RiderSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer(read_only=True)
    club = ClubBriefSerializer(read_only=True)

    class Meta:
        model = Rider

class RiderList(generics.ListCreateAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer

    def get_queryset(self):

        clubid = self.request.query_params.get('club', None)
        commissaire = self.request.query_params.get('commissaire', None)

        if clubid is not None:
            if commissaire is not None:
                riders = Rider.objects.filter(club__pk__exact=clubid, commissaire_valid__gt=datetime.date.today())
            else:
                riders = Rider.objects.filter(club__pk__exact=clubid)
        else:
            riders = Rider.objects.all()

        return riders

@permission_classes((ClubOfficialPermission,))
class RiderDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer

#---------------PointScore------------------

class PointScoreBriefSerializer(serializers.HyperlinkedModelSerializer):

    club = ClubBriefSerializer(read_only=True)

    class Meta:
        model = PointScore
        fields = ('url', 'club', 'name')

class PointScoreList(generics.ListCreateAPIView):
    serializer_class = PointScoreBriefSerializer

    def get_queryset(self):
        """Allow filtering of queryset by a URL query
        parameter ?club=SLUG
        """

        clubslug = self.request.query_params.get('club', None)
        ps = PointScore.objects.all()

        if clubslug is not None:
            ps = ps.filter(club__slug__exact=clubslug)

        return ps

class PointScoreSerializer(serializers.HyperlinkedModelSerializer):

    results = serializers.SerializerMethodField('result_list')
    club = serializers.SerializerMethodField('club_name')

    def club_name(self, ps):
        return ps.club.name

    def result_list(self, ps):

        queryset = ps.tabulate()

        return [{'rider': " ".join((tally.rider.user.first_name, tally.rider.user.last_name)),
                'riderid': tally.rider.user.id,
                'club': tally.rider.club.slug,
                'grade': tally.rider.clubgrade_set.get(club__exact=tally.pointscore.club).grade,
                'points': tally.points,
                'eventcount': tally.eventcount}
                for tally in queryset]

    class Meta:
        model = PointScore
        fields = ('name', 'club', 'results')


@permission_classes((ClubOfficialPermission,))
class PointScoreDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PointScore.objects.all()
    serializer_class = PointScoreSerializer

#---------------RaceResult------------------

class RaceResultSerializer(serializers.ModelSerializer):

    rider = serializers.SerializerMethodField('rider_name')
    riderid = serializers.SerializerMethodField('rider_id')
    club = serializers.SerializerMethodField('club_name')

    def club_name(self, result):
        if result.rider.club != None:
            return result.rider.club.name
        else:
            return "Unknown"

    def rider_name(self, result):
        return str(result.rider)

    def rider_id(self, result):
        return result.rider.id

    class Meta:
        model = RaceResult

class RaceResultList(generics.ListCreateAPIView):

    serializer_class = RaceResultSerializer

    def get_queryset(self):

        raceid = self.request.query_params.get('race', None)
        placed = self.request.query_params.get('placed', None)

        try:
            if raceid is not None:
                if placed is not None:
                    return RaceResult.objects.filter(race__pk__exact=raceid, place__gt=0)
                else:
                    return RaceResult.objects.filter(race__pk__exact=raceid)
            else:
                return RaceResult.objects.all()
        except ValueError:
            # given a non integer for raceid
            raise Http404("Invalid Race ID")

class RaceResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceResult.objects.all()
    serializer_class = RaceResultSerializer
