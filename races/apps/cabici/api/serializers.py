"""Serializers defining the canonical v1 API contract."""

from django.contrib.auth.models import User
from rest_framework import serializers

from races.apps.cabici.models import Club, ClubRole, PointScore, Race, RaceCourse, RaceResult, Rider, UserRole


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "slug",
            "website",
            "contact",
            "manage_races",
            "manage_members",
            "manage_results",
        ]


class RiderSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(read_only=True)
    club_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Rider
        fields = [
            "id",
            "full_name",
            "user_id",
            "club_id",
            "licenceno",
            "gender",
            "dob",
            "official",
            "phone",
            "email",
            "streetaddress",
            "suburb",
            "state",
            "postcode",
        ]

    def get_full_name(self, obj) -> str:
        return str(obj)

    def get_email(self, obj) -> str:
        return obj.user.email


class RaceSerializer(serializers.ModelSerializer):
    club_id = serializers.IntegerField(read_only=True)
    location_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Race
        fields = [
            "id",
            "title",
            "date",
            "signontime",
            "starttime",
            "status",
            "club_id",
            "location_id",
            "category",
            "discipline",
            "licencereq",
            "grading",
            "description",
        ]


class PointScoreSerializer(serializers.ModelSerializer):
    club_id = serializers.IntegerField(read_only=True)
    races = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = PointScore
        fields = [
            "id",
            "club_id",
            "name",
            "points",
            "smallpoints",
            "smallthreshold",
            "participation",
            "races",
        ]


class RaceCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RaceCourse
        fields = [
            "id",
            "name",
            "shortname",
            "location",
        ]


class RaceResultSerializer(serializers.ModelSerializer):
    race = serializers.PrimaryKeyRelatedField(queryset=Race.objects.all(), write_only=True)
    rider = serializers.PrimaryKeyRelatedField(queryset=Rider.objects.all(), write_only=True)
    rider_name = serializers.SerializerMethodField()
    rider_id = serializers.IntegerField(source="rider.pk", read_only=True)
    race_id = serializers.IntegerField(source="race.pk", read_only=True)
    grade_change = serializers.SerializerMethodField()

    class Meta:
        model = RaceResult
        fields = [
            "id",
            "race",
            "rider",
            "race_id",
            "rider_id",
            "rider_name",
            "grade",
            "usual_grade",
            "number",
            "place",
            "dnf",
            "grade_change",
        ]

    def get_rider_name(self, obj) -> str:
        return str(obj.rider)

    def get_grade_change(self, obj) -> bool:
        return bool(obj.usual_grade) and obj.grade != obj.usual_grade


class ClubRoleSerializer(serializers.ModelSerializer):
    shortname = serializers.CharField(read_only=True)

    class Meta:
        model = ClubRole
        fields = [
            "id",
            "name",
            "shortname",
        ]


class UserRoleSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)
    club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.all(), write_only=True)
    role = serializers.PrimaryKeyRelatedField(queryset=ClubRole.objects.all(), write_only=True)
    user_id = serializers.IntegerField(source="user.pk", read_only=True)
    club_id = serializers.IntegerField(source="club.pk", read_only=True)
    role_id = serializers.IntegerField(source="role.pk", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user",
            "club",
            "role",
            "user_id",
            "club_id",
            "role_id",
            "role_name",
        ]
