"""Serializers for the REST API"""

from rest_framework import serializers, generics
from models import Club, Race, RaceCourse
from usermodel import Rider, PointScore, RaceResult

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'clubs': reverse('club-list', request=request, format=format),
        'races': reverse('race-list', request=request, format=format),
        'racecourses': reverse('racecourse-list', request=request, format=format),
        'riders': reverse('rider-list', request=request, format=format),
        'pointscores': reverse('pointscore-list', request=request, format=format),
        'raceresults': reverse('raceresult-list', request=request, format=format),

    })

#---------------Club------------------

class ClubSerializer(serializers.HyperlinkedModelSerializer):

    races = serializers.HyperlinkedRelatedField(many=True, queryset=Race.objects.all(), view_name='race-detail')

    class Meta:
        model = Club
        #fields = ('id', 'name', 'url', 'slug', 'contact', 'races')

class ClubList(generics.ListCreateAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer

class ClubDetail(generics.RetrieveUpdateDestroyAPIView):
        queryset = Club.objects.all()
        serializer_class = ClubSerializer

#---------------Race------------------

class RaceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Race


class RaceList(generics.ListCreateAPIView):
    serializer_class = RaceSerializer

    def get_queryset(self):

        clubid = self.request.query_params.get('club', None)

        if clubid is not None:
            return Race.objects.filter(club__pk__exact=clubid)
        else:
            return Race.objects.all()


class RaceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Race.objects.all()
    serializer_class = RaceSerializer

#---------------RaceCourse------------------

class RaceCourseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceCourse

class RaceCourseList(generics.ListCreateAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer

class RaceCourseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer

#---------------Rider------------------

class RiderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Rider

class RiderList(generics.ListCreateAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer

class RiderDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer

from django.contrib.auth.models import User

class UserSerializer(serializers.HyperlinkedModelSerializer):
    rider = serializers.HyperlinkedRelatedField(many=False, queryset=Rider.objects.all(), view_name='rider-detail')

    class Meta:
        model = User
        fields = ('id', 'username', 'rider')

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

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