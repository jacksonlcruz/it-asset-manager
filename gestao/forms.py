# gestao/forms.py
from django import forms
from .models import Preparazione, Dispositivo, Dipartimento # Importiamo il Dispositivo
from datetime import date

class PreparazioneForm(forms.ModelForm):
    # Trasforma il campo di testo in un menu a tendina che recupera dati dalla tabella Dipartimento
    dipartimento_nuovo_utente = forms.ModelChoiceField(
        queryset=Dipartimento.objects.none(),
        required=False,
        label="Dipartimento (Nuovo Utente)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dipartimento_nuovo_utente'].queryset = Dipartimento.objects.all().order_by('nome')
        # Filtra il campo per mostrare solo i dispositivi con stato 'Disponibile'
        self.fields['dispositivo_nuovo'].queryset = Dispositivo.objects.filter(stato='Disponibile').order_by('hostname')
        # Limita anche il campo del vecchio dispositivo per mostrare solo quelli assegnati
        self.fields['dispositivo_vecchio'].queryset = Dispositivo.objects.filter(stato='Assegnato').order_by('hostname')


    class Meta:
        model = Preparazione
        # Lista di campi aggiornata
        fields = [
            'tipo_richiesta', 'categoria', 'luogo_intervento', # <-- Nuovo campo aggiunto
            'nome_nuovo_utente', 'cognome_nuovo_utente', 'data_ingresso', 'dipartimento_nuovo_utente', 'tipo_contratto_nuovo_utente',
            'utente', 'dispositivo_vecchio', 
            'motivo_sostituzione',
            'dispositivo_nuovo',
            'ticket_helpdesk', 'tipologia_pc_richiesta', 'note_software', 'data_pianificazione'
        ]
        # Il campo manuale è stato rimosso dalla lista 'fields'

        widgets = {
            'data_ingresso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_pianificazione': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'tipo_richiesta': forms.Select(attrs={'class': 'form-select'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo_contratto_nuovo_utente': forms.Select(attrs={'class': 'form-select'}),
            'utente': forms.Select(attrs={'class': 'form-select'}),
            'dispositivo_vecchio': forms.Select(attrs={'class': 'form-select'}),
            'dispositivo_nuovo': forms.Select(attrs={'class': 'form-select'}), # Widget per il nuovo campo
            'motivo_sostituzione': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'luogo_intervento': forms.Select(attrs={'class': 'form-select'}),
            'note_software': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'tipo_richiesta': 'Tipo di Richiesta', 
            'categoria': 'Categoria della Richiesta',
            'nome_nuovo_utente': 'Nome (Nuovo Utente)',
            'cognome_nuovo_utente': 'Cognome (Nuovo Utente)',
            'data_ingresso': 'Data di Ingresso',
            'dipartimento_nuovo_utente': 'Dipartimento (Nuovo Utente)',
            'utente': 'Utente Esistente (per Sostituzione)',
            'dispositivo_vecchio': 'Dispositivo da Sostituire',
            'dispositivo_nuovo': 'Nuovo Dispositivo (dal Magazzino)', # Label per il nuovo campo
            'motivo_sostituzione': 'Motivo della Sostituzione',
            'ticket_helpdesk': 'Ticket Help Desk',
            'tipologia_pc_richiesta': 'Tipologia PC Richiesta',
            'note_software': 'Note / Software Richiesti',
            'data_pianificazione': 'Data Pianificata per l\'intervento',
        }



class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        # Definisce i campi del formulario
        fields = ['hostname', 'cespite', 'numero_serie', 'marca', 'modello', 'tipo', 'stato', 'data_acquisto', 'note']

        # Aggiunge i widget Bootstrap
        widgets = {
            'hostname': forms.TextInput(attrs={'class': 'form-control'}),
            'cespite': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            # Usa il datalist suggerito: aggiunge l'attributo 'list' per mostrare le opzioni
            'marca': forms.TextInput(attrs={'class': 'form-control', 'list': 'marca_options'}),
            'modello': forms.TextInput(attrs={'class': 'form-control', 'list': 'modello_options'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'stato': forms.Select(attrs={'class': 'form-select'}),
            'data_acquisto': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    # Metodo speciale per rendere alcuni campi non obbligatori
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campi non obbligatori
        self.fields['cespite'].required = False
        self.fields['numero_serie'].required = False
        self.fields['data_acquisto'].required = False
        self.fields['note'].required = False

        # --- NUOVA LOGICA ---
        # Se stiamo creando un nuovo dispositivo (non modificando uno esistente)
        if not self.instance.pk:
            # Imposta il valore iniziale del campo 'stato' su 'Disponibile'
            self.fields['stato'].initial = 'Disponibile'
            # Disabilita il campo in modo che non sia modificabile nella schermata di creazione
            self.fields['stato'].disabled = True


class LottoDispositiviForm(forms.Form):
    TIPO_PC_CHOICES = [('Notebook', 'Notebook'), ('PC Fisso', 'PC Fisso')]

    # Il campo 'tipo' nel modello Dispositivo è per Office/CAD. Questo è per l'hardware.
    # I nomi sono distinti per chiarezza: tipo_pc vs tipo_dettaglio
    tipo_pc = forms.ChoiceField(choices=TIPO_PC_CHOICES, label="Tipo di PC (per generare Hostname)", widget=forms.Select(attrs={'class': 'form-select'}))

    # Usa le scelte già definite nel modello Dispositivo
    tipo_dettaglio = forms.ChoiceField(choices=Dispositivo.TIPO_CHOICES, label="Tipologia (Office/CAD, ecc)", widget=forms.Select(attrs={'class': 'form-select'}))

    # Fornisce suggerimenti ma permette comunque l'inserimento libero tramite datalist
    marca = forms.CharField(max_length=100, label="Marca", widget=forms.TextInput(attrs={'class': 'form-control', 'list': 'marca_options'}))
    modello = forms.CharField(max_length=100, label="Modello", widget=forms.TextInput(attrs={'class': 'form-control', 'list': 'modello_options'}))
    cespite_iniziale = forms.IntegerField(label="Cespite Iniziale", help_text="Es. 78500", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    quantita = forms.IntegerField(label="Quantità di PC da creare", help_text="Es. 50", min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    data_acquisto = forms.DateField(label="Data di Acquisto", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))


#Classe per la restituzione del PC
class RestituzioneForm(forms.Form):
    dispositivo = forms.ModelChoiceField(
        queryset=Dispositivo.objects.none(),
        label="Dispositivo a restituire",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_restituzione = forms.DateField(
        label="Data di Restituzione",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=date.today
    )
    locazione_magazzino = forms.CharField(
        label="Locazione in Magazzino (opzionale)",
        help_text="Es. Scaffale A-03",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    note = forms.CharField(
        label="Note sulla restituzione",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dispositivo'].queryset = Dispositivo.objects.filter(stato='Assegnato').order_by('hostname')