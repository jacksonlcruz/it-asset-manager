import os
import re
from datetime import datetime

import pandas as pd
from dateutil.parser import parse as date_parse

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from gestao.models import Utente, Dipartimento, Dispositivo, Assegnazione


class Command(BaseCommand):
    help = 'Importa/aggiorna inventario dal file Excel IDG (xlsx).'

    def add_arguments(self, parser):
        parser.add_argument('file', nargs='?', help='Percorso al file Excel (default: IDG - Computer25_05_2026.xlsx)', default='IDG - Computer25_05_2026.xlsx')

    def parse_owner_string(self, raw_string):
        if not raw_string or '\\' in str(raw_string):
            return None, None, None, 'Interno'

        cognome, nome, dipartimento_nome, tipo_contratto = '', '', None, 'Interno'

        raw = str(raw_string)
        if ', extern)' in raw.lower():
            tipo_contratto = 'Esterno'

        match_dip = re.search(r'\((.*?)\)', raw)
        if match_dip:
            full_dip_string = match_dip.group(1).strip()
            dipartimento_nome = full_dip_string.split(',')[0].strip()
            raw = re.sub(r'\s*\([^)]*\)', '', raw)

        match_nome = re.match(r'([^,]+),\s*(.+)', raw)
        if match_nome:
            cognome = match_nome.group(1).strip()
            nome = match_nome.group(2).strip()
        else:
            cognome = raw.strip()

        return nome, cognome, dipartimento_nome, tipo_contratto

    def find_column(self, df_cols, candidates):
        # Cerca una colonna in df le cui sottostringhe corrispondono a candidate
        for cand in candidates:
            for col in df_cols:
                if cand.lower() in col.lower():
                    return col
        return None

    def parse_date(self, value):
        if value is None: return None
        try:
            if isinstance(value, (datetime,)):
                return value.date()
            s = str(value).strip()
            if s == '' or s.lower() == 'nan':
                return None
            # dateutil parser is robust for many formats
            dt = date_parse(s, dayfirst=False, fuzzy=True)
            return dt.date()
        except Exception:
            return None

    def handle(self, *args, **options):
        file_arg = options.get('file')
        file_path = file_arg
        if not os.path.isabs(file_path):
            # try project root
            project_root = getattr(settings, 'BASE_DIR', os.getcwd())
            alt = os.path.join(project_root, file_path)
            if os.path.exists(alt):
                file_path = alt

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File non trovato: {file_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Avvio importazione/aggiornamento da {file_path}'))

        # colonne possibili
        df = pd.read_excel(file_path, dtype=object)
        df_cols = list(df.columns)

        host_col = self.find_column(df_cols, ['Asset Name', 'Hostname', 'Host Name', 'Computer'])
        cespite_col = self.find_column(df_cols, ['Asset IDG', 'Asset ID', 'Cespite', 'Asset'])
        serial_col = self.find_column(df_cols, ['Serial Number', 'Serial', 'S/N', 'SerialNumber'])
        manuf_col = self.find_column(df_cols, ['Manufacturer', 'Vendor', 'Produttore'])
        model_col = self.find_column(df_cols, ['Model', 'Modello'])
        purchase_col = self.find_column(df_cols, ['Purchase Date', 'Acquisition', 'Purchase', 'Data Acquisto'])
        location_col = self.find_column(df_cols, ['Location', 'Locazione', 'Location Name'])
        owner_col = self.find_column(df_cols, ['Owner', 'User', 'Proprietario'])

        warehouse_locations = ["ICT DHS", "ICT DHS Nizza", "ICT DHS Nichelino"]

        created = 0
        updated = 0
        assigned = 0
        skipped = 0

        for idx, row in df.iterrows():
            try:
                hostname = str(row[host_col]).strip() if host_col and pd.notna(row[host_col]) else ''
                if not hostname:
                    skipped += 1
                    continue

                cespite_val = None
                if cespite_col and pd.notna(row[cespite_col]):
                    cespite_val = str(row[cespite_col]).strip()
                    if cespite_val.upper() == 'NO' or cespite_val == 'nan' or cespite_val == '':
                        cespite_val = None

                serial_val = None
                if serial_col and pd.notna(row[serial_col]):
                    serial_val = str(row[serial_col]).strip()
                    if serial_val.upper() == 'NO' or serial_val == 'nan' or serial_val == '':
                        serial_val = None

                marca = str(row[manuf_col]).strip() if manuf_col and pd.notna(row[manuf_col]) else ''
                modello = str(row[model_col]).strip() if model_col and pd.notna(row[model_col]) else ''
                locazione = str(row[location_col]).strip() if location_col and pd.notna(row[location_col]) else ''
                owner_raw = str(row[owner_col]).strip() if owner_col and pd.notna(row[owner_col]) else ''
                data_acq = None
                if purchase_col and pd.notna(row[purchase_col]):
                    data_acq = self.parse_date(row[purchase_col])

                modello_lower = modello.lower() if modello else ''
                tipo_dispositivo = 'CAD' if any(term in modello_lower for term in ['zbook', 'fury', 'z8', 'z4', 'z2']) else 'Office'

                stato = 'In Bonifica' if locazione in warehouse_locations else 'Assegnato'

                with transaction.atomic():
                    dispositivo = None
                    # try by hostname
                    dispositivo = Dispositivo.objects.filter(hostname=hostname).first()
                    # try by cespite or serial if not found
                    if not dispositivo and cespite_val:
                        dispositivo = Dispositivo.objects.filter(cespite=cespite_val).first()
                    if not dispositivo and serial_val:
                        dispositivo = Dispositivo.objects.filter(numero_serie=serial_val).first()

                    if dispositivo:
                        # update fields
                        dispositivo.cespite = cespite_val or dispositivo.cespite
                        dispositivo.numero_serie = serial_val or dispositivo.numero_serie
                        dispositivo.marca = marca or dispositivo.marca
                        dispositivo.modello = modello or dispositivo.modello
                        dispositivo.tipo = tipo_dispositivo or dispositivo.tipo
                        dispositivo.stato = stato or dispositivo.stato
                        dispositivo.locazione_magazzino = locazione or dispositivo.locazione_magazzino
                        if data_acq:
                            dispositivo.data_acquisto = data_acq
                        dispositivo.save()
                        updated += 1
                        self.stdout.write(f'-> Aggiornato: {hostname}')
                    else:
                        # create new
                        dispositivo = Dispositivo.objects.create(
                            hostname=hostname,
                            cespite=cespite_val,
                            numero_serie=serial_val,
                            marca=marca,
                            modello=modello,
                            tipo=tipo_dispositivo,
                            stato=stato,
                            locazione_magazzino=locazione,
                            data_acquisto=data_acq
                        )
                        created += 1
                        self.stdout.write(f'-> Creato: {hostname} con stato "{stato}"')

                    # gestione assegnazione se necessario
                    if stato == 'Assegnato' and owner_raw:
                        nome, cognome, dip_nome, tipo_contratto = self.parse_owner_string(owner_raw)
                        if nome and cognome:
                            dip_obj = None
                            if dip_nome:
                                dip_obj, _ = Dipartimento.objects.get_or_create(nome=dip_nome)
                            utente_obj, _ = Utente.objects.get_or_create(
                                nome=nome, cognome=cognome,
                                defaults={'dipartimento': dip_obj, 'tipo_contratto': tipo_contratto}
                            )
                            # crea assegnazione attiva se non esiste
                            active = Assegnazione.objects.filter(dispositivo=dispositivo, data_restituzione__isnull=True).first()
                            if not active:
                                Assegnazione.objects.create(
                                    dispositivo=dispositivo,
                                    utente=utente_obj,
                                    data_assegnazione=data_acq or datetime.now().date()
                                )
                                assigned += 1
                                self.stdout.write(self.style.SUCCESS(f'-> Assegnato a "{utente_obj}"'))

            except Exception as e:
                skipped += 1
                self.stdout.write(self.style.ERROR(f'Errore riga {idx+2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Importazione completata: {created} creati, {updated} aggiornati, {assigned} assegnazioni create, {skipped} saltati.'))
