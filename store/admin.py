from django.contrib import admin

# Register your models here.
from .models import CustomUser, BetSlip, Bet, AviatorBet, AviatorGame, AviatorRoundSummary,  GameAnalytics, Leaderboard


# Register your models here.
admin.site.register(CustomUser)
admin.site.register(BetSlip)
admin.site.register(Bet)
admin.site.register(AviatorGame)
admin.site.register(AviatorBet)
admin.site.register(AviatorRoundSummary)
admin.site.register(GameAnalytics)
admin.site.register(Leaderboard)