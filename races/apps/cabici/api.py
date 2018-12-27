"""Serializers for the REST API"""
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers, generics, permissions, relations
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.compat import authenticate
from rest_framework.exceptions import APIException

import datetime
from django.http import Http404
from django.contrib.auth.models import User


from .models import Club, Race, RaceCourse
from .usermodel import Rider, PointScore, RaceResult, RaceStaff, ClubRole, ClubGrade, Membership


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination class for requests that return large numbers of results"""

    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


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


class CustomAuthTokenSerializer(serializers.Serializer):
    """Provide a custom response to a request for an auth token
    uses email rather than username to authenticate and
    returns a slightly richer JSON response than the
    default"""

    email = serializers.CharField(label=_("Email"))
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:

            user_from_email = User.objects.get(email=email)
            if not user_from_email:
                msg = _("Email not valid")
                raise serializers.ValidationError(msg, code='authorization')

            username = user_from_email.username

            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class CustomAuthToken(ObtainAuthToken):
    """Define a custom response to token authentication request
    Use email rather than username and return some additional user
    information"""

    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'club': user.rider.club.slug,
            'official': user.rider.official
        })


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
        if isinstance(obj, Race) or isinstance(obj, Rider):
            club = obj.club
        elif isinstance(obj, RaceResult):
            club = obj.race.club
        else:
            return False

        return request.user.rider.club == club

# ---------------Club------------------


class ClubSerializer(serializers.HyperlinkedModelSerializer):

    races = serializers.HyperlinkedRelatedField(many=True, queryset=Race.objects.all(), view_name='race-detail')
    url = relations.HyperlinkedIdentityField(lookup_field='slug', view_name='club-detail')

    class Meta:
        model = Club
        fields = ('url', 'name', 'slug', 'website', 'races')


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

# ---------------RaceCourse------------------


class RaceCourseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceCourse
        fields = '__all__'


class RaceCourseBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = RaceCourse
        fields = '__all__'


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

        result = dict()
        for role in obj.distinct():
            entry = {'id': role.rider.id, 'name': role.rider.user.first_name + " " + role.rider.user.last_name}
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

# ---------------RaceStaff------------------


class RaceStaffSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceStaff
        fields = '__all__'

    role = serializers.SlugRelatedField(slug_field='name', queryset=ClubRole.objects.all())


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

    class Meta:
        model = Rider
        fields = ('id', 'first_name', 'last_name', 'club', 'clubslug', 'licenceno',
                  'classification',
                  'member_category',
                  'member_date',
                  'grades',
                  'gender', 'emergencyphone', 'emergencyname' )


class RiderList(generics.ListCreateAPIView):
    # require authentication to access rider list API
    permission_classes = (IsAuthenticated, )
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):

        clubid = self.request.query_params.get('club', None)
        commissaire = self.request.query_params.get('commissaire', None)
        prefix = self.request.query_params.get('prefix', None)

        if clubid is not None:
            if commissaire is not None:
                riders = Rider.objects.filter(club__pk__exact=clubid, commissaire_valid__gt=datetime.date.today())
            else:
                riders = Rider.objects.filter(club__pk__exact=clubid)
        else:
            riders = Rider.objects.all()

        if prefix is not None:
            riders = riders.filter(user__last_name__istartswith=prefix)

        riders = riders.select_related('user', 'club')

        return riders.order_by('user__last_name')


@permission_classes((ClubOfficialPermission,))
class RiderDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer


# ---------------PointScore------------------

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
                'grade': tally.pointscore.club.grade(tally.rider),
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

# ---------------RaceResult------------------


class RaceResultSerializer(serializers.ModelSerializer):

    rider_name = serializers.CharField(source="rider", read_only=True)
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
        fields = '__all__'


class RaceResultList(generics.ListCreateAPIView):

    serializer_class = RaceResultSerializer

    def get_queryset(self):

        raceid = self.request.query_params.get('race', None)
        placed = self.request.query_params.get('placed', None)

        try:
            if raceid is not None:
                if placed is not None:
                    return RaceResult.objects.filter(race__pk__exact=raceid, place__gt=0).select_related('rider', 'rider__user')
                else:
                    return RaceResult.objects.filter(race__pk__exact=raceid).select_related('rider', 'rider__user')
            else:
                # should be all results but that would be too many
                # and we'd never actually want that so return nothing
                return RaceResult.objects.none()

        except ValueError:
            # given a non integer for raceid
            raise Http404("Invalid Race ID")

    def post(self, request, *args, **kwargs):
        """Handle post payload containing entries and new riders"""

        data = request.data
        if 'race' in data:
            raceid = data['race']
        else:
            raise APIException("Invalid JSON for race results: require 'race'")

        try:
            race = Race.objects.get(id=raceid)
        except Race.DoesNotExist:
            raise APIException("Invalid Race ID in JSON upload")

        ridermap = {}  # will hold a mapping between temporary and real ids for riders

        # handle new and updated riders
        for record in data.get('riders', []):
            # new rider id starts with "ID"
            if str(record['id']).startswith("ID"):
                # create a new rider record with these details
                username = Rider.objects.make_username(record['first_name'],
                                                       record['last_name'],
                                                       str(record['licenceno']))

                # just in case we know them already we use get_or_create
                user, created = User.objects.get_or_create(first_name=record['first_name'],
                                                           last_name=record['last_name'],
                                                           email=record['email'],
                                                           username=username)
                try:
                    club = Club.objects.get(slug=record['clubslug'])
                except Club.DoesNotExist:
                    raise APIException("Unknown club in rider record")

                if not created:
                    # guard against recreating the rider
                    rider = user.rider
                else:
                    rider = Rider(licenceno=record['licenceno'], club=club, user=user)
                    rider.save()

                # membership
                if 'member_date' in record:
                    memberdate = datetime.date.fromisoformat(record['member_date'])

                    m = Membership(rider=rider,
                                   club=rider.club,
                                   date=memberdate,
                                   category='race')
                    m.save()

                # grade
                if 'grade' in record:
                    cg = rider.clubgrade_set.filter(club=race.club)
                    if cg:
                        cg[0].grade = record['grade']
                        cg[0].save()
                    else:
                        ClubGrade(rider=rider, club=race.club, grade=record['grade']).save()

                # now remember the id of this rider for the results entry later
                ridermap[record['id']] = rider.id
            else:
                # existing rider updated
                print("Updated Rider", record)
                try:
                    rider = Rider.objects.get(id=record['id'])
                except Rider.DoesNotExist:
                    raise APIException("Unknown rider ID in new rider record")

                print("Updating Rider:", rider)

                # membership: club and date
                if 'clubslug' in record:
                    try:
                        record['club'] = Club.objects.get(slug=record['clubslug'])
                    except Club.DoesNotExist:
                        raise APIException("Club not found in updated rider record")

                if 'member_date' in record:
                    record['member_date'] = datetime.date.fromisoformat(record['member_date'])

                m = rider.current_membership
                if m:
                    # update club if different
                    if 'club' in record and m.club != record['club']:
                        m.club = record['club']
                        m.save()

                    # update membership date if more recent
                    if 'member_date' in record:
                        if record['member_date'] > m.date:
                            m.date = date
                            m.save()
                elif 'club' in record and 'member_date' in record:
                    # no current membership so make one
                    m = Membership(rider=rider, club=record['club'], date=record['member_date'])
                    m.save()

                # licenceno
                if 'licenceno' in record and rider.licenceno != record['licenceno']:
                    rider.licenceno = record['licenceno']
                    rider.save()

                # name
                if 'first_name' in record and rider.user.first_name != record['first_name']:
                    rider.user.first_name = record['first_name']
                    rider.user.save()

                if 'last_name' in record and rider.user.last_name != record['last_name']:
                    rider.user.last_name = record['last_name']
                    rider.user.save()



        # handle entries, first remove any existing results for this race
        # then create one result for each entry
        entryfields = ['rider', 'grade']

        race.raceresult_set.all().delete()
        for entry in data.get('entries', []):
            print("ENTRY", entry)
            # ensure all required fields
            if not all([f in entry for f in entryfields]):
                raise APIException("Missing fields in JSON entry")

            if str(entry['rider']).startswith("ID"):
                if entry['rider'] in ridermap:
                    entry['rider'] = ridermap[entry['rider']]
                else:
                    raise APIException("Result record with unknown temporary rider ID")

            try:
                rider = Rider.objects.get(id=entry['rider'])
            except Rider.DoesNotExist:
                raise APIException("Rider (id=%s) not found for result" % entry['rider'])

            print("Rider", rider)

            if race.club.slug in rider.grades:
                usual_grade = rider.grades[race.club.slug]
            else:
                if 'usual_grade' in entry:
                    usual_grade = entry['usual_grade']
                else:
                    usual_grade = entry['grade']
                # create a rider grade
                ClubGrade(rider=rider, club=race.club, grade=usual_grade).save()
                print("new grade", rider, race.club, usual_grade)

            if not usual_grade == entry['grade'] and 'grade_change' in entry and entry['grade_change']:
                # update rider grade
                grade = ClubGrade.objects.get(rider=rider, club=race.club)
                grade.grade = entry['grade']
                grade.save()
                print("Updated grade for ", rider, grade.grade)

            result = RaceResult(rider=rider, race=race,
                                grade=entry['grade'],
                                number=entry.get('number', 999),
                                usual_grade=usual_grade,
                                place=entry.get('place', 0))
            result.save()

        return Response({'message': 'something'})


class RaceResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceResult.objects.all()
    serializer_class = RaceResultSerializer
