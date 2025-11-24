# gestao/models.py - VERSÃO CORRIGIDA E COMPLETA
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
    tipo_contratto = models.CharField(max_length=50, choices=TIPO_CONTRATTO_CHOICES, default='Interno') # <-- NOSSO NOVO CAMPO
    attivo = models.BooleanField(default=True)

    class Meta:
        ordering = ['cognome', 'nome']

    def __str__(self):
        return f"{self.cognome}, {self.nome}"

class Dispositivo(models.Model):
    # --- Nossas Novas Listas de Opções ---
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
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES) # Adicionamos as escolhas aqui
    marca = models.CharField(max_length=100)
    modello = models.CharField(max_length=100)
    numero_serie = models.CharField(max_length=255, unique=True, blank=True, null=True)
    hostname = models.CharField(max_length=255, unique=True)
    stato = models.CharField(max_length=50, choices=STATO_CHOICES, default='Disponibile') # Adicionamos as escolhas aqui
    data_acquisto = models.DateField(blank=True, null=True)
    data_sostituzione_prevista = models.DateField(blank=True, null=True)
    password_administrator = models.CharField(max_length=255, blank=True, null=True, verbose_name="Password Admin")
    locazione_magazzino = models.CharField(max_length=100, blank=True, null=True, verbose_name="Locazione in Magazzino")
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.hostname} ({self.modello})"
    
    # --- NOSSA NOVA PROPRIEDADE INTELIGENTE ---
    @property
    def utente_attuale(self):
        # Encontra a atribuição ativa (sem data de devolução) para este dispositivo
        assegnazione_attiva = self.assegnazione_set.filter(data_restituzione__isnull=True).first()
        if assegnazione_attiva:
            return assegnazione_attiva.utente
        return None # Retorna nada se não houver atribuição ativa

# gestao/models.py

class Assegnazione(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE)
    data_assegnazione = models.DateField()
    data_restituzione = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.dispositivo.hostname} -> {self.utente}"

    # --- NOSSA NOVA REGRA INTELIGENTE ---
    def save(self, *args, **kwargs):
        # Se a atribuição está sendo criada (e não apenas modificada) E não tem data de devolução...
        if self.pk is None and self.data_restituzione is None:
            # ...então mude o status do dispositivo para 'Assegnato'
            self.dispositivo.stato = 'Assegnato'
            self.dispositivo.save() # Salva a mudança no dispositivo

        # Se uma data de devolução for adicionada, mude o status para 'In Bonifica'
        elif self.data_restituzione is not None:
            self.dispositivo.stato = 'In Bonifica'
            self.dispositivo.save() # Salva a mudança no dispositivo

        super().save(*args, **kwargs) # Finalmente, continua com o processo normal de salvar a atribuição

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
        choices=Utente.TIPO_CONTRATTO_CHOICES, # Reutiliza as escolhas do modelo Utente
        default='Interno',
        verbose_name="Tipo Contratto (Nuovo Utente)"
    )

    # Campos de Sostituzione
    utente = models.ForeignKey(Utente, on_delete=models.SET_NULL, blank=True, null=True)
    dispositivo_vecchio = models.ForeignKey(Dispositivo, related_name='sostituzioni_come_vecchio', on_delete=models.SET_NULL, blank=True, null=True)
    # O campo manual foi removido do modelo para simplificar
    # dispositivo_vecchio_manuale = models.CharField(max_length=255, blank=True, null=True)
    motivo_sostituzione = models.TextField(blank=True, null=True)

    # --- NOSSO NOVO CAMPO ---
    dispositivo_nuovo = models.ForeignKey(Dispositivo, related_name='assegnazioni_come_nuovo', verbose_name="Nuovo Dispositivo dal Magazzino", on_delete=models.SET_NULL, blank=True, null=True)
    

    # Campos Comuns
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