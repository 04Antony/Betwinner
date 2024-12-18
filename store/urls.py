from django.urls import path

from . import views
from store.views import get_active_game
urlpatterns = [
 path('', views.home, name="home"),

 path('register/', views.register, name='register'),
 path('account/', views.account, name='account'),
 path('aviator/', views.aviator, name="aviator"),
 path('submit-betslip/', views.submit_betslip, name='submit_betslip'),
 path('my-bets/', views.my_bets, name='my_bets'),
 path('bet-confirmation/', views.bet_confirmation, name='bet_confirmation'),
 path('login/', views.user_login, name='login'),
 path("aviator/place-bet/", views.place_bet, name="place_bet"),
 path('api/active-game/', get_active_game, name='active-game'),
 path('aviator/end/<str:round_id>/', views.end_game_round, name='end_game_round'),
 path('aviator/cash-out/<int:bet_id>/', views.cash_out, name='cash_out'),
    
]


