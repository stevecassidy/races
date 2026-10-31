"""Serializers defining the canonical v1 API contract."""

from rest_framework import serializers

from races.apps.cabici.models import Club, Race, Rider


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
