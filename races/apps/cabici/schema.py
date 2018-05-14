import graphene
from graphene import relay, ObjectType
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.contrib.auth.models import User


from .models import Club, Race
from .usermodel import Rider, ClubGrade


class ClubNode(DjangoObjectType):
    class Meta:
        model = Club
        filter_fields = {
            'name': ['exact', 'istartswith', 'icontains'],
            'slug': ['exact']
        }
        interfaces = (relay.Node,)


class RaceNode(DjangoObjectType):
    class Meta:
        model = Race
        filter_fields = ['date', 'club']
        interfaces = (relay.Node,)


class RiderNode(DjangoObjectType):

    firstName = graphene.String()
    lastName = graphene.String()

    def resolve_firstName(self, info, **kwargs):
        return self.user.first_name

    def resolve_lastName(self, info, **kwargs):
        return self.user.last_name

    class Meta:
        model = Rider
        filter_fields = {
            'licenceno': ['exact', 'istartswith'],
        }
        interfaces = (relay.Node,)


class ClubGradeNode(DjangoObjectType):
    class Meta:
        model = ClubGrade
        filter_fields = []
        interfaces = (relay.Node,)


class Query(object):
    club = relay.Node.Field(ClubNode)
    all_clubs = DjangoFilterConnectionField(ClubNode)
    race = relay.Node.Field(RaceNode)
    all_races = DjangoFilterConnectionField(RaceNode)
    rider = relay.Node.Field(RiderNode)
    all_riders = DjangoFilterConnectionField(RiderNode)
    clubgrade = relay.Node.Field(ClubGradeNode)
    all_clubgrades = DjangoFilterConnectionField(ClubGradeNode)

