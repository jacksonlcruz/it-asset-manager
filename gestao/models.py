# gestao/models.py - VERSIONE CORRETTA E COMPLETA
from django.db import models
from django.contrib.auth.models import User

class Dipartimento(models.Model):
    nome = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome
    
class Sede(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    indirizzo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Utente(models.Model):
    TIPO_CONTRATTO_CHOICES = [
        ('Interno', 'Interno'),
        ('Esterno', 'Esterno'),
        ('Stagista', 'Stagista'),
        ('Interinale', 'Interinale'),
    ]

    nome = models.CharField(max_length=100)
    cognome = models.CharField(max_length=100)
    dipartimento = models.ForeignKey(Dipartimento, on_delete=models.SET_NULL, blank=True, null=True)
    tipo_contratto = models.CharField(max_length=50, choices=TIPO_CONTRATTO_CHOICES, default='Interno') # <-- NUOVO CAMPO
    attivo = models.BooleanField(default=True)

    class Meta:
        ordering = ['cognome', 'nome']

    def __str__(self):
        return f"{self.cognome}, {self.nome}"

class Dispositivo(models.Model):
    # --- Nuove Liste di Opzioni ---
    STATO_CHOICES = [
        ('Disponibile', 'Disponibile'),
        ('Riservato', 'Riservato'),
        ('Assegnato', 'Assegnato'),
        ('In Bonifica', 'In Bonifica'),
        ('Rottamato', 'Rottamato'),
    ]
    TIPO_CHOICES = [
        ('Office', 'Office'),
        ('CAD', 'CAD'),
        ('Notebook', 'Notebook generico'),
        ('PC Fisso', 'PC Fisso generico'),
        ('Wacom', 'Wacom'),
        ('Altro', 'Altro'),
    ]

    cespite = models.CharField(max_length=255, unique=True, blank=True, null=True, verbose_name="Cespite / N° Patrimônio")
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES) # Aggiunta lista di scelte
    marca = models.CharField(max_length=100)
    modello = models.CharField(max_length=100)
    numero_serie = models.CharField(max_length=255, unique=True, blank=True, null=True)
    hostname = models.CharField(max_length=255, unique=True)
    stato = models.CharField(max_length=50, choices=STATO_CHOICES, default='Disponibile') # Aggiunta lista di scelte
    data_acquisto = models.DateField(blank=True, null=True)
    data_sostituzione_prevista = models.DateField(blank=True, null=True)
    password_administrator = models.CharField(max_length=255, blank=True, null=True, verbose_name="Password Admin")
    locazione_magazzino = models.CharField(max_length=100, blank=True, null=True, verbose_name="Locazione in Magazzino")
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.hostname} ({self.modello})"
    
    # --- PROPRIETÀ INTELLIGENTE: UTENTE ATTUALE ---
    @property
    def utente_attuale(self):
        # Trova l'assegnazione attiva (senza data di restituzione) per questo dispositivo
        assegnazione_attiva = self.assegnazione_set.filter(data_restituzione__isnull=True).first()
        if assegnazione_attiva:
            return assegnazione_attiva.utente
        # Se non esiste un'assegnazione attiva, verifica se esiste una Preparazione
        # che ha riservato questo dispositivo e che contiene informazioni sull'utente.
        # Preferisce l'assegnazione collegata alla preparazione, poi il campo `utente`
        # della preparazione, poi nome/cognome del nuovo utente.
        prep = self.assegnazioni_come_nuovo.select_related('assegnazione').order_by('-id').first()
        if prep:
            # Se la preparazione ha un'assegnazione collegata, usa quell'utente
            if getattr(prep, 'assegnazione', None):
                return prep.assegnazione.utente
            # Se la preparazione ha un riferimento a un Utente (sostituzione), usalo
            if prep.utente:
                return prep.utente
            # Se è una nuova assunzione, prova a comporre il nome dal campo testo
            if prep.cognome_nuovo_utente or prep.nome_nuovo_utente:
                cognome = prep.cognome_nuovo_utente or ''
                nome = prep.nome_nuovo_utente or ''
                if cognome and nome:
                    return f"{cognome}, {nome}"
                return (cognome or nome).strip()

        return None # Restituisce None se non c'è un'assegnazione o preparazione utile

class Assegnazione(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE)
    data_assegnazione = models.DateField()
    data_restituzione = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.dispositivo.hostname} -> {self.utente}"

    # --- REGOLA INTELLIGENTE: AGGIORNAMENTO STATO DISPOSITIVO ---
    def save(self, *args, **kwargs):
        # Se l'assegnazione viene creata (e non solo modificata) E non ha data di restituzione...
        if self.pk is None and self.data_restituzione is None:
            # ...allora cambia lo stato del dispositivo in 'Assegnato'
            self.dispositivo.stato = 'Assegnato'
            self.dispositivo.save() # Salva la modifica sul dispositivo

        # Se viene aggiunta una data di restituzione, cambia lo stato in 'In Bonifica'
        elif self.data_restituzione is not None:
            self.dispositivo.stato = 'In Bonifica'
            self.dispositivo.save() # Salva la modifica sul dispositivo

        super().save(*args, **kwargs) # Infine, prosegue con il normale salvataggio dell'assegnazione

class Preparazione(models.Model):
    TIPO_RICHIESTA_CHOICES = [('Nuova Assunzione', 'Nuova Assunzione'), ('Sostituzione', 'Sostituzione')]
    STATO_PREPARAZIONE_CHOICES = [('In attesa specifiche', 'In attesa specifiche'), ('Pronto per preparazione', 'Pronto per preparazione'), ('Completato', 'Completato')]
    CATEGORIA_CHOICES = [('Standard', 'Standard'), ('Stagista', 'Stagista'), ('Interinale', 'Interinale'), ('Priorità', 'Priorità'), ('Riassegnazione', 'Riassegnazione'), ('Extra', 'Extra')]
    tipo_richiesta = models.CharField(max_length=50, choices=TIPO_RICHIESTA_CHOICES)
    stato_preparazione = models.CharField(max_length=50, choices=STATO_PREPARAZIONE_CHOICES, default='In attesa specifiche')
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, default='Standard', verbose_name="Categoria")
    luogo_intervento = models.ForeignKey(
        Sede, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Luogo Intervento"
    )
    tecnico_responsabile = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Tecnico Responsabile"
    )
    nome_nuovo_utente = models.CharField(max_length=100, blank=True, null=True)
    cognome_nuovo_utente = models.CharField(max_length=100, blank=True, null=True)
    data_ingresso = models.DateField(blank=True, null=True)
    dipartimento_nuovo_utente = models.CharField(max_length=100, blank=True, null=True)
    tipo_contratto_nuovo_utente = models.CharField(
        max_length=50, 
        choices=Utente.TIPO_CONTRATTO_CHOICES, # Riutilizza le scelte del modello Utente
        default='Interno',
        verbose_name="Tipo Contratto (Nuovo Utente)"
    )

    # Campi di Sostituzione
    utente = models.ForeignKey(Utente, on_delete=models.SET_NULL, blank=True, null=True)
    dispositivo_vecchio = models.ForeignKey(Dispositivo, related_name='sostituzioni_come_vecchio', on_delete=models.SET_NULL, blank=True, null=True)
    # Il campo manuale è stato rimosso dal modello per semplificare
    # dispositivo_vecchio_manuale = models.CharField(max_length=255, blank=True, null=True)
    motivo_sostituzione = models.TextField(blank=True, null=True)

    # --- NUOVO CAMPO ---
    dispositivo_nuovo = models.ForeignKey(Dispositivo, related_name='assegnazioni_come_nuovo', verbose_name="Nuovo Dispositivo dal Magazzino", on_delete=models.SET_NULL, blank=True, null=True)
    

    # Campi Comuni
    ticket_helpdesk = models.CharField(max_length=100, blank=True, null=True)
    TIPOLOGIA_PC_CHOICES = [
    ('Office', 'Office'),
    ('CAD', 'CAD'),
    ]
    tipologia_pc_richiesta = models.CharField(max_length=50, blank=True, null=True, choices=TIPOLOGIA_PC_CHOICES)
    note_software = models.TextField(blank=True, null=True)
    data_pianificazione = models.DateTimeField(blank=True, null=True, verbose_name="Data e Ora Pianificata")
    mail_inviata = models.BooleanField(default=False)
    dati_in_scsm = models.BooleanField(default=False)
    in_ars = models.BooleanField(default=False)
    delivery_inviato = models.BooleanField(default=False)
    assegnazione = models.OneToOneField(Assegnazione, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        if self.tipo_richiesta == 'Nuova Assunzione': return f"Preparazione per {self.nome_nuovo_utente} {self.cognome_nuovo_utente}"
        else: return f"Sostituzione per {self.utente}"