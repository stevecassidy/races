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

from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.tests import MockedResponse, TestCase

from .provider import TidyHQProvider


# class TidyHQOAuth2Tests(OAuth2TestsMixin, TestCase):
#     provider_id = TidyHQProvider.id

#     def get_mocked_response(self):
#         return MockedResponse(200, """{
#     "id": 1,
#     "first_name": "First",
#     "last_name": "Last",
#     "email": "first@example.com",
#     "status":"active",
#     "created_at": "2012-12-16T21:01:22Z"
#   }""")  # noqa
