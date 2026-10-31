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

"""Keep ``Rider.updated`` honest for delta sync (C8).

The race-day app caches riders and refreshes with ``?changed=<timestamp>``, so a
rider has to be touched when their membership or grade changes, not only when
the Rider row itself is saved. The upload used to paper over this by calling
``rider.save()`` purely to bump the timestamp.

``update()`` is used deliberately: it touches the column without firing
``auto_now`` on another save, so there is no recursion.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ClubGrade, Membership, Rider


def touch_rider(rider_id):
    Rider.objects.filter(pk=rider_id).update(updated=timezone.now())


@receiver(post_save, sender=Membership)
@receiver(post_delete, sender=Membership)
def membership_changed(sender, instance, **kwargs):
    touch_rider(instance.rider_id)


@receiver(post_save, sender=ClubGrade)
@receiver(post_delete, sender=ClubGrade)
def clubgrade_changed(sender, instance, **kwargs):
    touch_rider(instance.rider_id)
