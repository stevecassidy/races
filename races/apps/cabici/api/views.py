"""Read-only v1 resource layer with schema-first endpoints."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse

from races.apps.cabici.api.filters import ClubFilter, PointScoreFilter, RaceFilter, RiderFilter
from races.apps.cabici.api.serializers import ClubSerializer, PointScoreSerializer, RaceSerializer, RiderSerializer
from races.apps.cabici.models import Club, PointScore, Race, Rider
from races.apps.cabici.services.pointscore import recalculate as recalculate_points


@extend_schema(description="The canonical v1 API root for public resources.", responses={200: {"type": "object"}})
@api_view(("GET",))
@permission_classes((AllowAny,))
def api_root(request, format=None):
    return Response(
        {
            "clubs": reverse("v1:club-list", request=request, format=format),
            "riders": reverse("v1:rider-list", request=request, format=format),
            "races": reverse("v1:race-list", request=request, format=format),
            "pointscores": reverse("v1:pointscore-list", request=request, format=format),
            "schema": reverse("v1:schema", request=request, format=format),
            "documentation": reverse("v1:swagger-ui", request=request, format=format),
        }
    )


class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.order_by("name")
    serializer_class = ClubSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ClubFilter
    search_fields = ["name", "slug", "contact"]
    ordering_fields = ["name", "slug"]


class RiderViewSet(viewsets.ModelViewSet):
    queryset = Rider.objects.select_related("user", "club").order_by("user__last_name", "user__first_name")
    serializer_class = RiderSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RiderFilter
    search_fields = ["user__first_name", "user__last_name", "user__email", "licenceno"]
    ordering_fields = ["user__last_name", "user__first_name", "club__name", "licenceno"]


class RaceViewSet(viewsets.ModelViewSet):
    queryset = Race.objects.select_related("club", "location").order_by("date", "signontime")
    serializer_class = RaceSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RaceFilter
    search_fields = ["title", "description", "club__name"]
    ordering_fields = ["date", "signontime", "title", "club__name"]


class PointScoreViewSet(viewsets.ModelViewSet):
    queryset = PointScore.objects.select_related("club").prefetch_related("races").order_by("club__name", "name")
    serializer_class = PointScoreSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PointScoreFilter
    search_fields = ["name", "club__name"]
    ordering_fields = ["name", "club__name"]

    @extend_schema(summary="Recalculate a pointscore", description="Rebuild the tally table from the races attached to the pointscore.", responses={200: {"type": "object"}})
    @action(detail=True, methods=["post"], url_path="recalculate")
    def recalculate(self, request, pk=None):
        pointscore = self.get_object()
        recalculate_points(pointscore)
        return Response({
            "status": "ok",
            "pointscore": pointscore.id,
            "name": pointscore.name,
            "tallies": pointscore.results.count(),
        })
