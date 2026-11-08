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

"""Report (and optionally fix) data that would violate the integrity constraints.

Run against a production copy before applying migrations 0020/0021:

    python manage.py checkconstraints          # report only; non-zero exit if any
    python manage.py checkconstraints --fix    # resolve the unambiguous duplicates

Migration 0020 adds the constraints; if duplicates remain it fails, and because
the container runs ``migrate`` on start, so does the deploy. This command is the
pre-deploy gate.

``--fix`` resolves only cases with one obvious answer:

- Membership and UserRole exact duplicates: keep the first row, delete the rest
- ClubRole duplicates sharing a name: merge onto the first role

Everything else -- Club.slug, ClubGrade(rider, club), PointscoreTally and
non-blank RaceResult bibs -- needs a human decision, so it is reported for
manual resolution rather than guessed at.
"""

import collections

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from races.apps.cabici.models import (
    Club,
    ClubGrade,
    ClubRole,
    Membership,
    PointscoreTally,
    RaceResult,
    RaceStaff,
    UserRole,
)


def duplicate_keys(rows, fields):
    """Return ``{key: [pk, ...]}`` for rows sharing the same key.

    ``rows`` is an iterable of dicts with a ``pk`` and each of ``fields``.
    """

    groups = collections.defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row["pk"])
    return {key: pks for key, pks in groups.items() if len(pks) > 1}


class Command(BaseCommand):

    help = "Report (and optionally fix) rows that would violate the integrity constraints."

    def add_arguments(self, parser):
        parser.add_argument("--fix", action="store_true", help="delete/merge the unambiguous duplicates")

    def handle(self, *args, **options):
        fix = options["fix"]
        unresolved = 0

        # the fixes commit on clean exit; the CommandError below is raised after,
        # so a partial cleanup is still kept
        with transaction.atomic():
            unresolved += self.check(Club, ["slug"], "Club.slug", fix=None)
            unresolved += self.check(ClubRole, ["name"], "ClubRole.name", fix=self.merge_clubroles if fix else None)
            unresolved += self.check(ClubGrade, ["rider", "club"], "ClubGrade(rider, club)", fix=None)
            unresolved += self.check(
                Membership,
                ["rider", "club", "category", "date"],
                "Membership(rider, club, category, date)",
                fix=self.delete_extras if fix else None,
            )
            unresolved += self.check(
                UserRole,
                ["user", "club", "role"],
                "UserRole(user, club, role)",
                fix=self.delete_extras if fix else None,
            )
            unresolved += self.check(
                PointscoreTally, ["pointscore", "rider"], "PointscoreTally(pointscore, rider)", fix=None
            )
            unresolved += self.check(
                RaceResult,
                ["race", "grade", "number"],
                "RaceResult(race, grade, number)",
                fix=None,
                queryset=RaceResult.objects.exclude(number__isnull=True),
            )

        if unresolved:
            raise CommandError("%d duplicate group(s) remain; see the report above" % unresolved)

        self.stdout.write(self.style.SUCCESS("No duplicate data found."))

    def check(self, model, fields, label, fix, queryset=None):
        """Report duplicate groups for one constraint; return how many remain."""

        source = model.objects.all() if queryset is None else queryset
        groups = duplicate_keys(source.values("pk", *fields), fields)

        if not groups:
            return 0

        self.stdout.write("%s: %d duplicate group(s)" % (label, len(groups)))
        for key, pks in list(groups.items())[:5]:
            self.stdout.write("    %s -> %s" % (key, sorted(pks)))
        if len(groups) > 5:
            self.stdout.write("    ... and %d more" % (len(groups) - 5))

        if fix is None:
            self.stdout.write(self.style.WARNING("    needs manual resolution"))
            return len(groups)

        fix(model, groups)
        self.stdout.write(self.style.SUCCESS("    fixed"))
        return 0

    @staticmethod
    def delete_extras(model, groups):
        """Keep the lowest-pk row in each group and delete the rest."""

        for pks in groups.values():
            model.objects.filter(pk__in=sorted(pks)[1:]).delete()

    @staticmethod
    def merge_clubroles(model, groups):
        """Merge same-named roles onto the lowest pk, repointing their users."""

        for pks in groups.values():
            keep, *others = sorted(pks)
            UserRole.objects.filter(role_id__in=others).update(role_id=keep)
            RaceStaff.objects.filter(role_id__in=others).update(role_id=keep)
            model.objects.filter(pk__in=others).delete()
