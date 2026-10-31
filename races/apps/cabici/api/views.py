"""Read-only v1 resource layer with schema-first endpoints."""

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from races.apps.cabici.api.filters import (
    ClubFilter,
    ClubRoleFilter,
    PointScoreFilter,
    RaceCourseFilter,
    RaceFilter,
    RaceResultFilter,
    RiderFilter,
    UserRoleFilter,
)
from races.apps.cabici.api.serializers import (
    AuthPasswordResetConfirmSerializer,
    AuthPasswordResetRequestSerializer,
    AuthProfileSerializer,
    AuthRegisterSerializer,
    ClubRoleSerializer,
    ClubSerializer,
    PointScoreSerializer,
    RaceCourseSerializer,
    RaceResultSerializer,
    RaceSerializer,
    RiderSerializer,
    UserRoleSerializer,
)
from races.apps.cabici.models import Club, ClubRole, PointScore, Race, RaceCourse, RaceResult, Rider, UserRole
from races.apps.cabici.services.pointscore import recalculate as recalculate_points

AUTH_REQUIRED_SCHEMES = ["jwtAuth", "tokenAuth", "cookieAuth"]


class AuthTokenObtainView(TokenObtainPairView):
    permission_classes = (AllowAny,)

    @extend_schema(auth=[], summary="Obtain JWT access and refresh tokens")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AuthTokenRefreshView(TokenRefreshView):
    permission_classes = (AllowAny,)

    @extend_schema(auth=[], summary="Refresh JWT access token")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(description="The canonical v1 API root for public resources.", responses={200: {"type": "object"}})
@api_view(("GET",))
@permission_classes((AllowAny,))
def api_root(request, format=None):
    return Response(
        {
            "clubs": reverse("v1:club-list", request=request, format=format),
            "club_roles": reverse("v1:club-role-list", request=request, format=format),
            "riders": reverse("v1:rider-list", request=request, format=format),
            "user_roles": reverse("v1:user-role-list", request=request, format=format),
            "races": reverse("v1:race-list", request=request, format=format),
            "race_courses": reverse("v1:race-course-list", request=request, format=format),
            "race_results": reverse("v1:race-result-list", request=request, format=format),
            "pointscores": reverse("v1:pointscore-list", request=request, format=format),
            "auth_token": reverse("v1:auth-token-obtain", request=request, format=format),
            "auth_refresh": reverse("v1:auth-token-refresh", request=request, format=format),
            "auth_me": reverse("v1:auth-me", request=request, format=format),
            "auth_register": reverse("v1:auth-register", request=request, format=format),
            "auth_profile": reverse("v1:auth-profile", request=request, format=format),
            "auth_password_reset": reverse("v1:auth-password-reset", request=request, format=format),
            "auth_password_reset_confirm": reverse("v1:auth-password-reset-confirm", request=request, format=format),
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

    @extend_schema(
        summary="Recalculate a pointscore",
        description="Rebuild the tally table from the races attached to the pointscore.",
        responses={200: {"type": "object"}},
    )
    @action(detail=True, methods=["post"], url_path="recalculate")
    def recalculate(self, request, pk=None):
        pointscore = self.get_object()
        recalculate_points(pointscore)
        return Response(
            {
                "status": "ok",
                "pointscore": pointscore.id,
                "name": pointscore.name,
                "tallies": pointscore.results.count(),
            }
        )


class RaceCourseViewSet(viewsets.ModelViewSet):
    queryset = RaceCourse.objects.order_by("name")
    serializer_class = RaceCourseSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RaceCourseFilter
    search_fields = ["name", "shortname"]
    ordering_fields = ["name", "shortname"]


class RaceResultViewSet(viewsets.ModelViewSet):
    queryset = RaceResult.objects.select_related("race", "rider", "rider__user").order_by(
        "race_id", "grade", "place", "number"
    )
    serializer_class = RaceResultSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RaceResultFilter
    search_fields = ["rider__user__first_name", "rider__user__last_name", "grade", "usual_grade"]
    ordering_fields = ["race_id", "grade", "place", "number"]


class ClubRoleViewSet(viewsets.ModelViewSet):
    queryset = ClubRole.objects.order_by("name")
    serializer_class = ClubRoleSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ClubRoleFilter
    search_fields = ["name"]
    ordering_fields = ["name"]


class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.select_related("user", "club", "role").order_by(
        "club__name", "role__name", "user__username"
    )
    serializer_class = UserRoleSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserRoleFilter
    search_fields = ["user__username", "user__first_name", "user__last_name", "club__name", "role__name"]
    ordering_fields = ["club__name", "role__name", "user__username"]


class AuthMeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get current authenticated user", auth=AUTH_REQUIRED_SCHEMES, responses={200: {"type": "object"}}
    )
    def get(self, request):
        rider = Rider.objects.select_related("club").filter(user=request.user).first()
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "rider_id": rider.id if rider else None,
                "club_id": rider.club_id if rider else None,
                "official": bool(rider and rider.official),
            }
        )


class AuthRegisterView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Register user", auth=[], request=AuthRegisterSerializer, responses={201: {"type": "object"}}
    )
    @transaction.atomic
    def post(self, request):
        serializer = AuthRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        rider = Rider.objects.filter(user=user).first()
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "rider_id": rider.id if rider else None,
            },
            status=status.HTTP_201_CREATED,
        )


class AuthProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _profile_payload(user: User) -> dict:
        rider = Rider.objects.select_related("club").filter(user=user).first()
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "rider_id": rider.id if rider else None,
            "club_id": rider.club_id if rider else None,
            "official": bool(rider and rider.official),
        }

    @extend_schema(
        summary="Get authenticated profile", auth=AUTH_REQUIRED_SCHEMES, responses={200: AuthProfileSerializer}
    )
    def get(self, request):
        return Response(self._profile_payload(request.user))

    @extend_schema(
        summary="Update authenticated profile",
        auth=AUTH_REQUIRED_SCHEMES,
        request=AuthProfileSerializer,
        responses={200: AuthProfileSerializer},
    )
    def patch(self, request):
        serializer = AuthProfileSerializer(data=request.data, context={"user": request.user}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response(self._profile_payload(request.user))


class AuthPasswordResetView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Request password reset",
        auth=[],
        request=AuthPasswordResetRequestSerializer,
        responses={200: {"type": "object"}},
    )
    def post(self, request):
        serializer = AuthPasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        form = PasswordResetForm({"email": email})
        if form.is_valid():
            form.save(request=request, use_https=request.is_secure())
        return Response({"detail": "If this email exists, a reset email has been sent."})


class AuthPasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Confirm password reset",
        auth=[],
        request=AuthPasswordResetConfirmSerializer,
        responses={200: {"type": "object"}},
    )
    def post(self, request):
        serializer = AuthPasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.context["reset_user"]
        token = serializer.validated_data["token"]
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({"token": "Invalid or expired reset token."})
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "Password reset successful."})
