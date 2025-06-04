import graphene
from graphene_django.types import DjangoObjectType
from accounts.models import User, Wallet

class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude = ('password',)

class WalletType(DjangoObjectType):
    class Meta:
        model = Wallet
        fields = "__all__"
