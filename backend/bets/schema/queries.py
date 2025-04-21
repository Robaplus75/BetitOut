import graphene
from .types import BetType
from ..models import Bet 

class Query(graphene.ObjectType):
    all_bets = graphene.List(BetType)

    def resolve_all_bets(root, info):
    	return Bet.objects.all()