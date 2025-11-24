# gestao/management/commands/import_sccm.py - VERSÃO FINAL COM CORREÇÃO DE USUÁRIO EXTERNO

import csv
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from gestao.models import Utente, Dipartimento, Dispositivo, Assegnazione

class Command(BaseCommand):
    help = 'Importa o inventário completo do arquivo de exportação do SCCM.'

    def parse_owner_string(self, raw_string):
        """Função auxiliar para extrair dados do campo Owner (versão corrigida)."""
        if not raw_string or '\\' in raw_string:
            return None, None, None, 'Interno'

        cognome, nome, dipartimento_nome, tipo_contratto = '', '', None, 'Interno'
        
        # 1. Primeiro, verifica se é um usuário externo para definir o tipo
        if ', extern)' in raw_string.lower():
            tipo_contratto = 'Esterno'

        # 2. Extrai o conteúdo de dentro dos parênteses (seja qual for)
        match_dip = re.search(r'\((.*?)\)', raw_string)
        if match_dip:
            # Pega tudo que está dentro dos parênteses
            full_dip_string = match_dip.group(1).strip()
            # O nome do departamento é a primeira parte antes da vírgula
            dipartimento_nome = full_dip_string.split(',')[0].strip()
            # Remove o conteúdo dos parênteses da string original para facilitar o parsing do nome
            raw_string = re.sub(r'\s*\([^)]+\)', '', raw_string)
        
        # 3. Extrai o nome e o sobrenome do que sobrou
        match_nome = re.match(r'([^,]+),\s*(.+)', raw_string)
        if match_nome:
            cognome = match_nome.group(1).strip()
            nome = match_nome.group(2).strip()
        else:
            # Fallback se o formato não tiver vírgula
            cognome = raw_string.strip()

        return nome, cognome, dipartimento_nome, tipo_contratto

    def handle(self, *args, **kwargs):
        file_path = 'sccm_export.csv'
        warehouse_locations = ["ICT DHS", "ICT DHS Nizza", "ICT DHS Nichelino"]
        self.stdout.write(self.style.SUCCESS(f'Iniciando importação do arquivo {file_path}...'))

        try:
            with open(file_path, mode='r', encoding='latin-1', errors='ignore') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                
                for i, row in enumerate(reader, start=2):
                    hostname = row.get('Asset Name', '').strip()
                    if not hostname: continue
                    
                    self.stdout.write(f'--- Processando {hostname} (linha {i}) ---')

                    # A lógica para criar/atualizar dispositivo e atribuição continua a mesma...
                    cespite_val = row.get('Asset IDG', '').strip()
                    serial_val = row.get('Serial Number', '').strip()
                    if cespite_val.upper() == 'NO' or not cespite_val: cespite_val = None
                    if serial_val.upper() == 'NO' or not serial_val: serial_val = None

                    if Dispositivo.objects.filter(hostname=hostname).exists():
                        self.stdout.write(self.style.NOTICE(f'Dispositivo com hostname "{hostname}" já existe. Pulando.'))
                        continue
                    if cespite_val and Dispositivo.objects.filter(cespite=cespite_val).exists():
                        self.stdout.write(self.style.NOTICE(f'Dispositivo com cespite "{cespite_val}" já existe. Pulando.'))
                        continue
                    if serial_val and Dispositivo.objects.filter(numero_serie=serial_val).exists():
                         self.stdout.write(self.style.NOTICE(f'Dispositivo com S/N "{serial_val}" já existe. Pulando.'))
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
                    self.stdout.write(f'-> Dispositivo "{hostname}" criado com status "{stato}".')

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
                            self.stdout.write(self.style.SUCCESS(f'-> Atribuído a "{utente_obj}", Tipo: {tipo_contratto}'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'ERRO: Arquivo "{file_path}" não encontrado.'))
        
        self.stdout.write(self.style.SUCCESS('--- Importação Finalizada! ---'))