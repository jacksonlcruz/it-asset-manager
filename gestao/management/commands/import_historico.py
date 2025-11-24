# gestao/management/commands/import_historico.py - VERSÃO COM LÓGICA DE TIPOLOGIA

import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from gestao.models import Utente, Dipartimento, Dispositivo, Assegnazione, Preparazione

class Command(BaseCommand):
    help = 'Importa o histórico do arquivo padronizado Storico.csv'

    def handle(self, *args, **kwargs):
        file_path = 'Storico.csv'
        self.stdout.write(self.style.SUCCESS(f'Iniciando importação do arquivo {file_path}...'))

        try:
            with open(file_path, mode='r', encoding='latin-1', errors='ignore') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                
                for i, row in enumerate(reader, start=2):
                    self.stdout.write(f'--- Processando linha {i} ---')
                    try:
                        hostname = row.get('Hostname', '').strip()
                        if not hostname or Dispositivo.objects.filter(hostname=hostname).exists():
                            continue

                        # ... (Busca de objetos relacionados continua a mesma) ...
                        dipartimento_obj = None
                        nome_dipartimento = row.get('Dipartimento', '').strip()
                        if nome_dipartimento:
                            dipartimento_obj, _ = Dipartimento.objects.get_or_create(nome=nome_dipartimento)
                        tecnico_nome = row.get('In carico a', '').strip()
                        tecnico_obj = User.objects.filter(username__iexact=tecnico_nome).first() if tecnico_nome else None
                        
                        utente_obj, _ = Utente.objects.get_or_create(
                            nome=row.get('Nome', '').strip(),
                            cognome=row.get('Cognome', '').strip(),
                            defaults={'dipartimento': dipartimento_obj}
                        )
                        
                        try:
                            data_acquisto = datetime.strptime(row.get('Data Arrivo', '').strip(), '%d/%m/%Y').date()
                        except (ValueError, TypeError):
                            data_acquisto = None
                        
                        # --- NOVA LÓGICA INTELIGENTE PARA TIPOLOGIA ---
                        modello_str = row.get('Modello', '').lower()
                        if any(term in modello_str for term in ['zbook', 'fury', 'z2', 'z16']):
                            tipologia = 'CAD'
                        else:
                            tipologia = 'Office'

                        dispositivo_obj = Dispositivo.objects.create(
                            hostname=hostname,
                            cespite=row.get('Cespite', '').strip() or None,
                            numero_serie=row.get('Cespite', '').strip() or hostname,
                            marca=row.get('Brand', '').strip(),
                            modello=row.get('Modello', '').strip(),
                            tipo=tipologia, # <-- USA A NOVA LÓGICA
                            password_administrator=row.get('PSW CIRESON', '').strip(),
                            data_acquisto=data_acquisto,
                            stato='Disponibile'
                        )
                        
                        # ... (O resto da criação da Preparazione e Assegnazione continua o mesmo) ...
                        
                        try:
                            data_assegnazione_str = row.get('Data pianificazione', '').split(' ')[0]
                            dt_obj = datetime.strptime(data_assegnazione_str, '%d/%m/%Y')
                            data_pianificazione = timezone.make_aware(dt_obj, timezone.get_default_timezone())
                            data_assegnazione = data_pianificazione.date()
                        except (ValueError, TypeError):
                            data_pianificazione = None
                            data_assegnazione = data_acquisto or timezone.now().date()
                        
                        status_raw = row.get('Status', 'Standard').strip()
                        preparazione = Preparazione.objects.create(
                            tipo_richiesta='Sostituzione' if 'Sostituzione' in status_raw else 'Nuova Assunzione',
                            stato_preparazione='Completato',
                            categoria=status_raw if status_raw in [c[0] for c in Preparazione.CATEGORIA_CHOICES] else 'Standard',
                            tecnico_responsabile=tecnico_obj,
                            utente=utente_obj,
                            dispositivo_nuovo=dispositivo_obj,
                            note_software=row.get('Note', '').strip(),
                            data_pianificazione=data_pianificazione,
                        )
                        
                        assegnazione = Assegnazione.objects.create(dispositivo=dispositivo_obj, utente=utente_obj, data_assegnazione=data_assegnazione)
                        preparazione.assegnazione = assegnazione
                        preparazione.save()
                        self.stdout.write(self.style.SUCCESS(f'Importado: Atribuição de "{hostname}" para "{utente_obj}" como tipo "{tipologia}".'))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Erro ao processar linha {i}: {e}'))
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'ERRO: Arquivo "{file_path}" não encontrado.'))
        
        self.stdout.write(self.style.SUCCESS('--- Importação Finalizada! ---'))