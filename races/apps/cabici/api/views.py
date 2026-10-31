"""Read-only v1 resource layer with schema-first endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse

from races.apps.cabici.api.serializers import ClubSerializer, RaceSerializer, RiderSerializer
from races.apps.cabici.models import Club, Race, Rider


@extend_schema(description="The canonical v1 API root for public resources.", responses={200: {"type": "object"}})
@api_view(("GET",))
@permission_classes((AllowAny,))
def api_root(request, format=None):
    return Response(
        {
            "clubs": reverse("v1:club-list", request=request, format=format),
            "riders": reverse("v1:rider-list", request=request, format=format),
            "races": reverse("v1:race-list", request=request, format=format),
            "schema": reverse("v1:schema", request=request, format=format),
            "documentation": reverse("v1:swagger-ui", request=request, format=format),
        }
    )


class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.order_by("name")
    serializer_class = ClubSerializer
    permission_classes = (AllowAny,)


class RiderViewSet(viewsets.ModelViewSet):
    queryset = Rider.objects.select_related("user", "club").order_by("user__last_name", "user__first_name")
    serializer_class = RiderSerializer
    permission_classes = (AllowAny,)


class RaceViewSet(viewsets.ModelViewSet):
    queryset = Race.objects.select_related("club", "location").order_by("date", "signontime")
    serializer_class = RaceSerializer
    permission_classes = (AllowAny,)
