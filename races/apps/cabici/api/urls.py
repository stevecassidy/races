"""URLs for the contract-first v1 API."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from races.apps.cabici.api.views import (
    AuthMeView,
    ClubRoleViewSet,
    ClubViewSet,
    PointScoreViewSet,
    RaceCourseViewSet,
    RaceResultViewSet,
    RaceViewSet,
    RiderViewSet,
    UserRoleViewSet,
    api_root,
)

app_name = "v1"

urlpatterns = [
    path("", api_root, name="api-v1-root"),
    path("schema/", SpectacularAPIView.as_view(urlconf="races.apps.cabici.api.urls"), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="v1:schema"), name="swagger-ui"),
    path("auth/token/", TokenObtainPairView.as_view(), name="auth-token-obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
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
    path("racecourses/", RaceCourseViewSet.as_view({"get": "list", "post": "create"}), name="race-course-list"),
    path(
        "racecourses/<int:pk>/",
        RaceCourseViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="race-course-detail",
    ),
    path("race-results/", RaceResultViewSet.as_view({"get": "list", "post": "create"}), name="race-result-list"),
    path(
        "race-results/<int:pk>/",
        RaceResultViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="race-result-detail",
    ),
    path("club-roles/", ClubRoleViewSet.as_view({"get": "list", "post": "create"}), name="club-role-list"),
    path(
        "club-roles/<int:pk>/",
        ClubRoleViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="club-role-detail",
    ),
    path("user-roles/", UserRoleViewSet.as_view({"get": "list", "post": "create"}), name="user-role-list"),
    path(
        "user-roles/<int:pk>/",
        UserRoleViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="user-role-detail",
    ),
]
