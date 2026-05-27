from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = "Dump app data to gestao/fixtures/devdata.json to share DB state"

    def add_arguments(self, parser):
        parser.add_argument('--apps', nargs='+', default=['gestao'], help='App labels to dump')
        parser.add_argument('--output', default='gestao/fixtures/devdata.json', help='Output fixture file')

    def handle(self, *args, **options):
        apps = options['apps']
        output = options['output']
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            # Use Django's dumpdata to export app data as fixtures
            call_command('dumpdata', *apps, '--indent', '2', stdout=f)
        self.stdout.write(self.style.SUCCESS(f'Wrote fixtures to {output}'))
