# gestao/management/commands/import_sccm.py - VERSIONE FINALE CON CORREZIONE UTENTE ESTERNO

import csv
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from gestao.models import Utente, Dipartimento, Dispositivo, Assegnazione

class Command(BaseCommand):
    help = 'Importa l\'inventario completo dal file di esportazione SCCM.'

    def parse_owner_string(self, raw_string):
        """Funzione ausiliaria per estrarre i dati dal campo Owner."""
        if not raw_string or '\\' in raw_string:
            return None, None, None, 'Interno'

        cognome, nome, dipartimento_nome, tipo_contratto = '', '', None, 'Interno'
        
        # 1. Prima, verifica se è un utente esterno per definire il tipo
        if ', extern)' in raw_string.lower():
            tipo_contratto = 'Esterno'

        # 2. Estrae il contenuto all'interno delle parentesi
        match_dip = re.search(r'\((.*?)\)', raw_string)
        if match_dip:
            # Prende tutto ciò che è dentro le parentesi
            full_dip_string = match_dip.group(1).strip()
            # Il nome del dipartimento è la prima parte prima della virgola
            dipartimento_nome = full_dip_string.split(',')[0].strip()
            # Rimuove il contenuto delle parentesi dalla stringa originale per facilitare il parsing del nome
            raw_string = re.sub(r'\s*\([^)]+\)', '', raw_string)
        
        # 3. Estrae il nome e il cognome da ciò che rimane
        match_nome = re.match(r'([^,]+),\s*(.+)', raw_string)
        if match_nome:
            cognome = match_nome.group(1).strip()
            nome = match_nome.group(2).strip()
        else:
            # Fallback se il formato non ha la virgola
            cognome = raw_string.strip()

        return nome, cognome, dipartimento_nome, tipo_contratto

    def handle(self, *args, **kwargs):
        file_path = 'sccm_export.csv'
        warehouse_locations = ["ICT DHS", "ICT DHS Nizza", "ICT DHS Nichelino"]
        self.stdout.write(self.style.SUCCESS(f'Avvio importazione dal file {file_path}...'))

        try:
            with open(file_path, mode='r', encoding='latin-1', errors='ignore') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                
                for i, row in enumerate(reader, start=2):
                    hostname = row.get('Asset Name', '').strip()
                    if not hostname: continue
                    
                    self.stdout.write(f'--- Elaborazione {hostname} (riga {i}) ---')

                    # Logica per creare/aggiornare dispositivo e assegnazione...
                    cespite_val = row.get('Asset IDG', '').strip()
                    serial_val = row.get('Serial Number', '').strip()
                    if cespite_val.upper() == 'NO' or not cespite_val: cespite_val = None
                    if serial_val.upper() == 'NO' or not serial_val: serial_val = None

                    if Dispositivo.objects.filter(hostname=hostname).exists():
                        self.stdout.write(self.style.NOTICE(f'Dispositivo con hostname "{hostname}" già esistente. Saltato.'))
                        continue
                    if cespite_val and Dispositivo.objects.filter(cespite=cespite_val).exists():
                        self.stdout.write(self.style.NOTICE(f'Dispositivo con cespite "{cespite_val}" già esistente. Saltato.'))
                        continue
                    if serial_val and Dispositivo.objects.filter(numero_serie=serial_val).exists():
                         self.stdout.write(self.style.NOTICE(f'Dispositivo con S/N "{serial_val}" già esistente. Saltato.'))
                         continue

                    location = row.get('Location', '').strip()
                    stato = 'In Bonifica' if location in warehouse_locations else 'Assegnato'
                    locazione_magazzino = location if stato == 'In Bonifica' else ''
                    modello_str = row.get('Model', '').lower()
                    tipo_dispositivo = 'CAD' if any(term in modello_str for term in ['zbook', 'fury', 'z8', 'z4', 'z2']) else 'Office'
                    try: data_acquisto = datetime.strptime(row.get('Purchase Date', '').split(' ')[0], '%m/%d/%Y').date()
                    except (ValueError, TypeError): data_acquisto = None
                    
                    dispositivo_obj = Dispositivo.objects.create(
                        hostname=hostname, cespite=cespite_val, numero_serie=serial_val,
                        marca=row.get('Manufacturer', '').strip(), modello=row.get('Model', '').strip(),
                        tipo=tipo_dispositivo, stato=stato, locazione_magazzino=locazione_magazzino, data_acquisto=data_acquisto
                    )
                    self.stdout.write(f'-> Dispositivo "{hostname}" creato con stato "{stato}".')

                    if stato == 'Assegnato':
                        owner_raw = row.get('Owner', '').strip()
                        nome, cognome, dip_nome, tipo_contratto = self.parse_owner_string(owner_raw)
                        if nome and cognome:
                            dipartimento_obj = None
                            if dip_nome:
                                dipartimento_obj, _ = Dipartimento.objects.get_or_create(nome=dip_nome)
                            utente_obj, _ = Utente.objects.get_or_create(
                                nome=nome, cognome=cognome,
                                defaults={'dipartimento': dipartimento_obj, 'tipo_contratto': tipo_contratto}
                            )
                            Assegnazione.objects.get_or_create(
                                dispositivo=dispositivo_obj, utente=utente_obj,
                                defaults={'data_assegnazione': data_acquisto or datetime.now().date()}
                            )
                            self.stdout.write(self.style.SUCCESS(f'-> Assegnato a "{utente_obj}", Tipo: {tipo_contratto}'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'ERRORE: File "{file_path}" non trovato.'))
        
        self.stdout.write(self.style.SUCCESS('--- Importazione Completata! ---'))