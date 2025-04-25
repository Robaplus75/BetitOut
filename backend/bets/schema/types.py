import graphene
from graphene_django import DjangoObjectType
from ..models import Bet, BetParticipant, Wallet, BetOption
from django.contrib.auth import get_user_model

User = get_user_model()

class UserType(DjangoObjectType):
	class Meta:
		model =User
		fields = "__all__"

class BetOptionType(DjangoObjectType):
	class Meta:
		model=BetOption
		fields = "__all__"

class BetParticipantType(DjangoObjectType):
	class Meta:
		model = BetParticipant
		fields = "__all__"

class BetType(DjangoObjectType):
	class Meta:
		model = Bet
		fields = "__all__"



class WalletType(DjangoObjectType):
	class Meta:
		model = Wallet
		fields = "__all__"
