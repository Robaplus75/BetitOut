import graphene
from .types import BetType
from ..models import Bet
from graphql import GraphQLError

class Query(graphene.ObjectType):
    all_bets = graphene.List(BetType)
    bet_get = graphene.Field(BetType, id=graphene.ID(required=True))

    def resolve_all_bets(root, info):
    	return Bet.objects.all()

    def resolve_bet_get(root, info, id):
        try:
            return Bet.objects.get(pk=id)
        except Bet.DoesNotExist:
            raise GraphQLError("Bet Not Found")