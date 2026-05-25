# gestao/admin.py - VERSIONE MIGLIORATA

from django.contrib import admin
from .models import Dipartimento, Utente, Dispositivo, Assegnazione, Preparazione, Sede

# Personalizzazione per il modello Dispositivo
@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'tipo', 'stato', 'utente_attuale', 'locazione_magazzino')
    list_filter = ('stato', 'tipo', 'marca')
    search_fields = ('hostname', 'cespite', 'numero_serie', 'modello')
    ordering = ('hostname',)

# Personalizzazione per il modello Utente
@admin.register(Utente)
class UtenteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'dipartimento', 'attivo')
    list_filter = ('attivo', 'dipartimento')
    search_fields = ('nome', 'cognome')
    ordering = ('cognome', 'nome')

# Personalizzazione per il modello Preparazione
@admin.register(Preparazione)
class PreparazioneAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tipo_richiesta', 'categoria', 'stato_preparazione', 'data_pianificazione')
    list_filter = ('stato_preparazione', 'tipo_richiesta', 'categoria')
    search_fields = ('nome_nuovo_utente', 'cognome_nuovo_utente', 'utente__nome', 'utente__cognome')
    ordering = ('-id',)

# Personalizzazione per il modello Assegnazione
@admin.register(Assegnazione)
class AssegnazioneAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'utente', 'data_assegnazione', 'data_restituzione')
    list_filter = ('data_assegnazione', 'data_restituzione')
    search_fields = ('dispositivo__hostname', 'utente__nome', 'utente__cognome')
    ordering = ('-data_assegnazione',)


# Registra i modelli Dipartimento e Sede in modo semplice
admin.site.register(Dipartimento)
admin.site.register(Sede)