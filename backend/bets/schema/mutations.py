import graphene
from .types import BetType
from django.contrib.auth import get_user_model
from ..models import Bet

User = get_user_model()

class CreateBetMutation(graphene.Mutation):
    class Arguments:
        creator_id = graphene.ID(required=True)
        title = graphene.String(required=True)
        description = graphene.String(required=True)
        option_one = graphene.String(required=True)
        option_two = graphene.String(required=True)
        expires_at = graphene.String(required=True)

    bet = graphene.Field(BetType)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, *args, **kwargs):
        try:
            user = User.objects.get(pk=kwargs.get('creator_id'))

            bet = Bet.objects.create(
                creator = user,
                title = kwargs.get('title'),
                description = kwargs.get('description'),
                option_one = kwargs.get('option_one'),
                option_two = kwargs.get('option_two'),
                expires_at = kwargs.get('expires_at')
            )

            return CreateBetMutation(bet=bet, success=True, message=None)
        
        except User.DoesNotExist:
            return CreateBetMutation(bet=None, success=False, message="User Not Found.")
        except Exception as e:
            return CreateBetMutation(bet=None, success=False, message=str(e))


class Mutation(graphene.ObjectType):
    create_bet = CreateBetMutation.Field(name="Bet_Create")
