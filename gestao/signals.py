# gestao/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Preparazione

@receiver(post_save, sender=Preparazione)
def update_dispositivo_status_on_save(sender, instance, created, **kwargs):
    # Se un nuovo dispositivo è stato collegato, lo segna come riservato
    if instance.dispositivo_nuovo:
        dispositivo = instance.dispositivo_nuovo
        if dispositivo.stato == 'Disponibile':
            dispositivo.stato = 'Riservato'
            dispositivo.save()

@receiver(post_delete, sender=Preparazione)
def update_dispositivo_status_on_delete(sender, instance, **kwargs):
    # Se la preparazione eliminata aveva un dispositivo riservato, lo libera
    if instance.dispositivo_nuovo:
        dispositivo = instance.dispositivo_nuovo
        if dispositivo.stato == 'Riservato':
            dispositivo.stato = 'Disponibile'
            dispositivo.save()