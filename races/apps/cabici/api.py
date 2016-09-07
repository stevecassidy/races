"""Serializers for the REST API"""

from rest_framework import serializers, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
import datetime

from models import Club, Race, RaceCourse
from usermodel import Rider, PointScore, RaceResult, RaceStaff, ClubRole




@api_view(('GET',))
@permission_classes((permissions.AllowAny,))
def api_root(request, format=None):
    return Response({
        'clubs': reverse('club-list', request=request, format=format),
        'races': reverse('race-list', request=request, format=format),
        'racecourses': reverse('racecourse-list', request=request, format=format),
        'riders': reverse('rider-list', request=request, format=format),
        'pointscores': reverse('pointscore-list', request=request, format=format),
        'raceresults': reverse('raceresult-list', request=request, format=format),
    })


# TODO: authentication for create/update/delete views

#---------------Club------------------

class ClubSerializer(serializers.HyperlinkedModelSerializer):

    races = serializers.HyperlinkedRelatedField(many=True, queryset=Race.objects.all(), view_name='race-detail')

    class Meta:
        model = Club
        #fields = ('id', 'name', 'url', 'slug', 'contact', 'races')

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


class RaceSerializer(serializers.ModelSerializer):
    # TODO: we want these fields to be expanded when we read the data
    # but we only want to specify the ID when we update/create
    club = ClubBriefSerializer(read_only=True)
    location = RaceCourseBriefSerializer(read_only=True)
    officials = RaceOfficialField()

    class Meta:
        model = Race
        fields = ('id', 'url', 'club', 'location', 'title', 'date', 'signontime', 'starttime', 'website', 'status', 'description', 'officials')

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



class RiderDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer



#---------------PointScore------------------

class PointScoreSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PointScore

class PointScoreList(generics.ListCreateAPIView):
    queryset = PointScore.objects.all()
    serializer_class = PointScoreSerializer

class PointScoreDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PointScore.objects.all()
    serializer_class = PointScoreSerializer

#---------------RaceResult------------------

class RaceResultSerializer(serializers.HyperlinkedModelSerializer):

    rider = RiderSerializer(read_only=True)

    class Meta:
        model = RaceResult

class RaceResultList(generics.ListCreateAPIView):

    serializer_class = RaceResultSerializer

    def get_queryset(self):

        raceid = self.request.query_params.get('race', None)

        if raceid is not None:
            return RaceResult.objects.filter(race__pk__exact=raceid)
        else:
            return RaceResult.objects.all()

class RaceResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceResult.objects.all()
    serializer_class = RaceResultSerializer
