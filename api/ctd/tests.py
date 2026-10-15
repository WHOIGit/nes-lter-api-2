import csv
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

import pandas as pd
from django.core.management import call_command
from django.test import TestCase

from core.models import Cruise, Vessel
from ctd.management.commands.importcruise import Command as ImportCruiseCommand
from ctd.services import CtdService


class ImportCruiseTypeTests(TestCase):
    """Cruise type resolution: types file row, else existing type, else NES-LTER."""

    @classmethod
    def setUpTestData(cls):
        cls.ar = Vessel.objects.create(designation='R/V', name='Neil Armstrong', short_name='Armstrong', code='ar')
        cls.en = Vessel.objects.create(designation='R/V', name='Endeavor', short_name='Endeavor', code='en')

    def run_import(self, cruise_name, types):
        """Run importcruise for one cruise with a canned types file and no elog."""
        load = mock.patch.object(ImportCruiseCommand, 'load_cruise_types',
                                 side_effect=types if isinstance(types, Exception) else None,
                                 return_value=None if isinstance(types, Exception) else types)
        elog = mock.patch.object(ImportCruiseCommand, 'parse_elog', return_value=(None, None))
        out = StringIO()
        with load, elog:
            call_command('importcruise', cruise_name=cruise_name, stdout=out)
        return out.getvalue()

    def cruise_type(self, name):
        return Cruise.objects.get(name=name).type

    def test_row_applies_to_non_ar_vessel(self):
        self.run_import('en700', {'en700': 'Opportunistic'})
        self.assertEqual(self.cruise_type('en700'), Cruise.CruiseType.OPPORTUNISTIC)

    def test_row_applies_to_ar_vessel(self):
        self.run_import('ar22', {'ar22': 'JP Student'})
        self.assertEqual(self.cruise_type('ar22'), Cruise.CruiseType.JP_STUDENT)

    def test_row_overrides_existing_type(self):
        Cruise.objects.create(name='en700', vessel=self.en, type=Cruise.CruiseType.NESLTER)
        self.run_import('en700', {'en700': 'OOI-NES'})
        self.assertEqual(self.cruise_type('en700'), Cruise.CruiseType.OOI_NES)

    def test_no_row_keeps_existing_type(self):
        Cruise.objects.create(name='en685', vessel=self.en, type=Cruise.CruiseType.OPPORTUNISTIC)
        self.run_import('en685', {})
        self.assertEqual(self.cruise_type('en685'), Cruise.CruiseType.OPPORTUNISTIC)

    def test_no_row_new_cruise_defaults_to_nes_lter(self):
        self.run_import('en701', {})
        self.assertEqual(self.cruise_type('en701'), Cruise.CruiseType.NESLTER)

    def test_missing_row_warns_for_ar_only(self):
        self.assertIn('type not defined', self.run_import('ar99', {}))
        self.assertNotIn('type not defined', self.run_import('en702', {}))

    def test_unreadable_types_file_keeps_existing_type(self):
        Cruise.objects.create(name='ar22', vessel=self.ar, type=Cruise.CruiseType.JP_STUDENT)
        Cruise.objects.create(name='en685', vessel=self.en, type=Cruise.CruiseType.OPPORTUNISTIC)
        self.run_import('ar22', FileNotFoundError('missing'))
        self.run_import('en685', FileNotFoundError('missing'))
        self.assertEqual(self.cruise_type('ar22'), Cruise.CruiseType.JP_STUDENT)
        self.assertEqual(self.cruise_type('en685'), Cruise.CruiseType.OPPORTUNISTIC)

    def test_unreadable_types_file_new_cruise_defaults(self):
        self.run_import('ar50', FileNotFoundError('missing'))
        self.assertEqual(self.cruise_type('ar50'), Cruise.CruiseType.NESLTER)


class LoadCruiseTypesTests(TestCase):
    def load(self, rows):
        df = pd.DataFrame(rows, columns=['Cruise', 'Cruise Type'])
        cmd = ImportCruiseCommand(stdout=StringIO())
        with mock.patch('ctd.management.commands.importcruise.pd.read_csv', return_value=df):
            return cmd.load_cruise_types(), cmd.stdout.getvalue()

    def test_valid_rows_loaded_and_normalized(self):
        types, _ = self.load([[' EN685 ', ' Opportunistic '], ['ar22', 'JP Student']])
        self.assertEqual(types, {'en685': 'Opportunistic', 'ar22': 'JP Student'})

    def test_invalid_type_row_skipped_rest_kept(self):
        types, out = self.load([['ar22', 'JP Student'], ['ar23', 'Bogus'], ['ar24', 'OOI-NES']])
        self.assertEqual(types, {'ar22': 'JP Student', 'ar24': 'OOI-NES'})
        self.assertIn("invalid cruise type 'Bogus'", out)

    def test_blank_cruise_name_row_skipped(self):
        types, out = self.load([[None, 'OOI-NES'], ['ar22', 'JP Student']])
        self.assertEqual(types, {'ar22': 'JP Student'})
        self.assertIn('no cruise name', out)


class UpdateCruiseTypeFileTests(TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.file = Path(self.dir.name) / 'NES-LTER_cruise_types.csv'
        patcher = mock.patch.object(CtdService, 'CRUISE_TYPES_FILE', self.file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def rows(self):
        with self.file.open(newline='') as f:
            return list(csv.DictReader(f))

    def test_creates_file_when_missing(self):
        CtdService.update_cruise_type_file('en685', 'Opportunistic')
        self.assertEqual(self.rows(), [{'Cruise': 'en685', 'Cruise Type': 'Opportunistic'}])

    def test_update_is_case_insensitive_and_does_not_duplicate(self):
        self.file.write_text('Cruise,Cruise Type\nen685,NES-LTER\nar22,JP Student\n')
        CtdService.update_cruise_type_file('EN685', 'Opportunistic')
        self.assertEqual(self.rows(), [
            {'Cruise': 'en685', 'Cruise Type': 'Opportunistic'},
            {'Cruise': 'ar22', 'Cruise Type': 'JP Student'},
        ])

    def test_appends_new_cruise(self):
        self.file.write_text('Cruise,Cruise Type\nar22,JP Student\n')
        CtdService.update_cruise_type_file('en700', 'OOI-NES')
        self.assertEqual(self.rows()[-1], {'Cruise': 'en700', 'Cruise Type': 'OOI-NES'})


class BroadscaleCruiseListTests(TestCase):
    URL = '/api/ctd/broadscale_cruise_list.csv'

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.file = Path(self.dir.name) / 'NESLTER_broadscale_cruise_list.csv'
        patcher = mock.patch.object(CtdService, 'BROADSCALE_CRUISE_LIST_FILE', self.file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_downloads_file_as_csv_attachment(self):
        self.file.write_text('cruise,note\nar77,ok\n')
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="NESLTER_broadscale_cruise_list.csv"',
        )
        self.assertEqual(b''.join(response.streaming_content), b'cruise,note\nar77,ok\n')

    def test_missing_file_is_404(self):
        self.assertEqual(self.client.get(self.URL).status_code, 404)

    def test_landing_page_links_to_download(self):
        response = self.client.get('/')
        self.assertContains(response, self.URL)
