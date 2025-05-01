from django.contrib import admin
from .models import Bet, BetOption, BetParticipant, Wallet


admin.site.register(Bet)
admin.site.register(BetOption)
admin.site.register(BetParticipant)
admin.site.register(Wallet)