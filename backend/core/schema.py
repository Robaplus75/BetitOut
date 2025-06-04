import graphene
from accounts.schema.mutations import Mutation as AccountsMutation
# from accounts.schema.queries import Query as AccountsQuery
from bets.schema.mutations import Mutation as BetsMutation
from bets.schema.queries import Query as BetsQuery

class Query(BetsQuery, graphene.ObjectType):
    pass

class Mutation(AccountsMutation, BetsMutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)
