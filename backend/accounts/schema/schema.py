import graphene
# from .queries import Query
from .mutations import Mutation


schema = graphene.Schema(mutation=Mutation)