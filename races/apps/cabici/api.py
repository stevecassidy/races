"""Serializers for the REST API"""

from rest_framework import serializers, generics, permissions, relations
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
import datetime

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
        for role in obj.all():
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

    class Meta:
        model = Race
        fields = ('id', 'url', 'club', 'location', 'title', 'date', 'signontime', 'starttime', 'website', 'status', 'description', 'officials')

@permission_classes((ClubOfficialPermission,))
class RaceList(generics.ListCreateAPIView):
    serializer_class = RaceSerializer

    def get_queryset(self):

        clubid = self.request.query_params.get('club', None)
        scheduled = self.request.query_params.get('scheduled', None)

        if clubid is not None:
            races = Race.objects.filter(club__pk__exact=clubid)
        else:
            races = Race.objects.all()

        if scheduled is not None:
            return races.filter(date__gte=datetime.date.today())
        else:
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

class PointScoreResultSerializer(serializers.Serializer):

    def to_representation(self, tally):

        return {'rider': " ".join((tally.rider.user.first_name, tally.rider.user.last_name)),
                'riderid': tally.rider.user.id,
                'grade': tally.rider.clubgrade_set.get(club__exact=tally.pointscore.club).grade,
                'points': tally.points,
                'eventcount': tally.eventcount}


class PointScoreSerializer(serializers.HyperlinkedModelSerializer):

    results = serializers.SerializerMethodField('result_list')
    club = serializers.SerializerMethodField('club_name')

    def club_name(self, ps):
        return ps.club.name

    def result_list(self, ps):

        queryset = ps.tabulate()[:100]

        return [{'rider': " ".join((tally.rider.user.first_name, tally.rider.user.last_name)),
                'riderid': tally.rider.user.id,
                'grade': tally.rider.clubgrade_set.get(club__exact=tally.pointscore.club).grade,
                'points': tally.points,
                'eventcount': tally.eventcount}
                for tally in queryset]

    class Meta:
        model = PointScore
        fields = ('name', 'club', 'results')

class PointScoreList(generics.ListCreateAPIView):
    queryset = PointScore.objects.all()
    serializer_class = PointScoreSerializer

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

        if raceid is not None:
            if placed is not None:
                return RaceResult.objects.filter(race__pk__exact=raceid, place__gt=0)
            else:
                return RaceResult.objects.filter(race__pk__exact=raceid)
        else:
            return RaceResult.objects.all()

class RaceResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceResult.objects.all()
    serializer_class = RaceResultSerializer
