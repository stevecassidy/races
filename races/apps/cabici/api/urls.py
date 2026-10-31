"""URLs for the contract-first v1 API."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from races.apps.cabici.api.views import (
    AuthLogoutView,
    AuthMeView,
    AuthPasswordResetConfirmView,
    AuthPasswordResetView,
    AuthProfileView,
    AuthRegisterView,
    AuthTokenObtainView,
    AuthTokenRefreshView,
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
    path("auth/token/", AuthTokenObtainView.as_view(), name="auth-token-obtain"),
    path("auth/token/refresh/", AuthTokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
    path("auth/register/", AuthRegisterView.as_view(), name="auth-register"),
    path("auth/profile/", AuthProfileView.as_view(), name="auth-profile"),
    path("auth/password-reset/", AuthPasswordResetView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm/", AuthPasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
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
