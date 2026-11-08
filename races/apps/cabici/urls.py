#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.urls import path

from races.apps.cabici import legacy_api, views

urlpatterns = [
    path("", views.HomePage.as_view(), name="home"),
    # Legacy API paths remain available while the contract-first v1 API is developed.
    path("api/", legacy_api.api_root),
    path("api/token-auth/", legacy_api.CustomAuthToken.as_view()),
    path("api/clubs/", legacy_api.ClubList.as_view(), name="club-list"),
    path("api/clubs/<str:slug>/", legacy_api.ClubDetail.as_view(), name="club-detail"),
    path("api/clubroles/<slug:slug>/", legacy_api.UserRolesView.as_view(), name="club-roles"),
    path("api/clubroles/<slug:slug>/<int:pk>/", legacy_api.UserRoleDestroyView.as_view(), name="destroy-club-role"),
    path("api/races/", legacy_api.RaceList.as_view(), name="race-list"),
    path("api/races/<int:pk>/", legacy_api.RaceDetail.as_view(), name="race-detail"),
    path("api/racestaff/", legacy_api.RaceStaffList.as_view(), name="racestaff-list"),
    path("api/racestaff/<int:pk>/", legacy_api.RaceStaffDetail.as_view(), name="racestaff-detail"),
    path("api/racecourses/", legacy_api.RaceCourseList.as_view(), name="racecourse-list"),
    path("api/racecourses/<int:pk>/", legacy_api.RaceCourseDetail.as_view(), name="racecourse-detail"),
    path("api/riders/", legacy_api.RiderList.as_view(), name="rider-list"),
    path("api/riders/<int:pk>/", legacy_api.RiderDetail.as_view(), name="rider-detail"),
    # path('api/users/<int:pk>/', api.UserDetail.as_view(), name='user-detail'),
    path("api/pointscores/", legacy_api.PointScoreList.as_view(), name="pointscore-list"),
    path("api/pointscores/<int:pk>/", legacy_api.PointScoreDetail.as_view(), name="pointscore-detail"),
    path("api/raceresults/", legacy_api.RaceResultList.as_view(), name="raceresult-list"),
    path("api/raceresults/<int:pk>/", legacy_api.RaceResultDetail.as_view(), name="raceresult-detail"),
]
