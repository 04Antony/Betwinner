from celery import shared_task
from .utils import auto_activate_game

@shared_task
def manage_aviator_game():
    auto_activate_game()
