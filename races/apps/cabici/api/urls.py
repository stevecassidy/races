"""URLs for the contract-first v1 API."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from races.apps.cabici.api.views import ClubViewSet, PointScoreViewSet, RaceViewSet, RiderViewSet, api_root

app_name = "v1"

urlpatterns = [
    path("", api_root, name="api-v1-root"),
    path("schema/", SpectacularAPIView.as_view(urlconf="races.apps.cabici.api.urls"), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="v1:schema"), name="swagger-ui"),
    path("clubs/", ClubViewSet.as_view({"get": "list", "post": "create"}), name="club-list"),
    path(
        "clubs/<int:pk>/",
        ClubViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="club-detail",
    ),
    path("riders/", RiderViewSet.as_view({"get": "list", "post": "create"}), name="rider-list"),
    path(
        "riders/<int:pk>/",
        RiderViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="rider-detail",
    ),
    path("races/", RaceViewSet.as_view({"get": "list", "post": "create"}), name="race-list"),
    path(
        "races/<int:pk>/",
        RaceViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="race-detail",
    ),
    path("pointscores/", PointScoreViewSet.as_view({"get": "list", "post": "create"}), name="pointscore-list"),
    path(
        "pointscores/<int:pk>/",
        PointScoreViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="pointscore-detail",
    ),
    path(
        "pointscores/<int:pk>/recalculate/",
        PointScoreViewSet.as_view({"post": "recalculate"}),
        name="pointscore-recalculate",
    ),
]
