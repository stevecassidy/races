#!/usr/bin/python
#
# Copyright 2023 Google LLC
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

# from allauth.socialaccount.tests import OAuth2TestsMixin
# from allauth.tests import MockedResponse, TestCase

# from .provider import StravaProvider


# class StravaOAuth2Tests(OAuth2TestsMixin, TestCase):
#     provider_id = StravaProvider.id

#     def get_mocked_response(self):
#         return MockedResponse(200, """{
#           "id": 227615,
#           "resource_state": 3,
#           "firstname": "John",
#           "lastname": "Applestrava",
#           "profile_medium": "http://pics.com/227615/medium.jpg",
#           "profile": "http://pics.com/227615/large.jpg",
#           "city": "San Francisco",
#           "state": "California",
#           "country": "United States",
#           "sex": "M",
#           "friend": null,
#           "follower": null,
#           "premium": true,
#           "created_at": "2008-01-01T17:44:00Z",
#           "updated_at": "2013-09-04T20:00:50Z",
#           "follower_count": 273,
#           "friend_count": 19,
#           "mutual_friend_count": 0,
#           "athlete_type": 0,
#           "date_preference": "%m/%d/%Y",
#           "measurement_preference": "feet",
#           "email": "john@applestrava.com",
#           "ftp": 280,
#           "weight": 68.7,
#           "clubs": [
#             {
#               "id": 1,
#               "resource_state": 2,
#               "name": "Team Strava Cycling",
#               "profile_medium": "http://pics.com/clubs/1/medium.jpg",
#               "profile": "http://pics.com/clubs/1/large.jpg",
#               "cover_photo": "http://pics.com/clubs/1/cover/large.jpg",
#               "cover_photo_small": "http://pics.com/clubs/1/cover/small.jpg",
#               "sport_type": "cycling",
#               "city": "San Francisco",
#               "state": "California",
#               "country": "United States",
#               "private": true,
#               "member_count": 23,
#               "featured": false,
#               "url": "strava-cycling"
#             }
#           ],
#           "bikes": [
#             {
#               "id": "b105763",
#               "primary": false,
#               "name": "Cannondale TT",
#               "distance": 476612.9,
#               "resource_state": 2
#             },
#             {
#               "id": "b105762",
#               "primary": true,
#               "name": "Masi",
#               "distance": 9000578.2,
#               "resource_state": 2
#             }
#           ],
#           "shoes": [
#             {
#               "id": "g1",
#               "primary": true,
#               "name": "Running Shoes",
#               "distance": 67492.9,
#               "resource_state": 2
#             }
#           ]
#         }
# """)  # noqa
