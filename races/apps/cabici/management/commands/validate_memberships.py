"""
Management command to validate rider memberships using AusCycling API

Usage:
    python manage.py validate_memberships [--club SLUG] [--months N] [--dry-run]
"""

from django.core.management.base import BaseCommand
from races.apps.cabici.models import Club
from races.apps.cabici.usermodel import Rider, RaceResult
import datetime
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Validate rider memberships using AusCycling API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--club',
            type=str,
            help='Club slug to validate (default: all clubs with API credentials)',
        )
        parser.add_argument(
            '--months',
            type=int,
            default=6,
            help='Validate riders who have raced in the last N months (default: 6)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be validated without making API calls',
        )
        parser.add_argument(
            '--check-date',
            type=str,
            help='Date to validate for (YYYY-MM-DD format, default: next Sunday)',
        )

    def handle(self, *args, **options):
        club_slug = options['club']
        months = options['months']
        dry_run = options['dry_run']
        check_date_str = options['check_date']
        
        # Calculate check date if provided
        if check_date_str:
            try:
                check_date = datetime.datetime.strptime(check_date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Invalid date format: {check_date_str}'))
                return
        else:
            ## will default to next Sunday
            check_date = None
        
        # Get clubs to process
        if club_slug:
            clubs = Club.objects.filter(slug=club_slug)
            if not clubs.exists():
                self.stdout.write(self.style.ERROR(f'Club not found: {club_slug}'))
                return
        else:
            clubs = Club.objects.exclude(auscycling_client_id='').exclude(auscycling_client_secret='')
        
        if not clubs.exists():
            self.stdout.write(self.style.WARNING('No clubs with AusCycling API credentials found'))
            return
        
        # Calculate cutoff date for recent racers
        cutoff_date = datetime.date.today() - datetime.timedelta(days=months * 30)
        
        total_validated = 0
        total_success = 0
        total_failed = 0
        total_errors = 0
        
        for club in clubs:
            self.stdout.write(f'\n{self.style.SUCCESS(f"Processing club: {club.name} ({club.slug})")}')
            
            # Find riders who have raced recently for this club
            riders = Rider.objects.filter(  
                raceresult__race__club=club,  
                raceresult__race__date__gte=cutoff_date,  
                licenceno__isnull=False  
            ).exclude(licenceno='').select_related('user', 'club').distinct()[:10]
            
            rider_count = riders.count()
            self.stdout.write(f'Found {rider_count} riders who have raced in the last {months} months')
            
            if dry_run:
                for rider in riders:
                    self.stdout.write(f'  Would validate: {rider} (Licence: {rider.licenceno})')
                continue
            
            # Validate each rider
            for i, rider in enumerate(riders, 1):
                self.stdout.write(f'  [{i}/{rider_count}] Validating {rider} (Licence: {rider.licenceno})...', ending='')
                
                try:
                    success, message = club.validate_membership(rider, check_date)
                    total_validated += 1
                    
                    if success:
                        total_success += 1
                        self.stdout.write(self.style.SUCCESS(' ✓'))
                        self.stdout.write(f'      {message}')
                    else:
                        total_failed += 1
                        self.stdout.write(self.style.WARNING(' ✗'))
                        self.stdout.write(f'      {message}')
                        
                except Exception as e:
                    total_errors += 1
                    self.stdout.write(self.style.ERROR(' ERROR'))
                    self.stdout.write(f'      {str(e)}')
                    logger.error(f'Error validating {rider}: {e}', exc_info=True)
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Validation complete'))
        self.stdout.write(f'Total validated: {total_validated}')
        self.stdout.write(self.style.SUCCESS(f'Successful: {total_success}'))
        self.stdout.write(self.style.WARNING(f'Failed: {total_failed}'))
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {total_errors}'))