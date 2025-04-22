import graphene
from .types import BetType
from django.contrib.auth import get_user_model
from ..models import Bet
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import logging

debug_logger = logging.getLogger("debugger")
logger = logging.getLogger("django")

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

            try:
                expires_at_dt = parse_datetime(kwargs.get("expires_at"))
            except ValueError:
                return UpdateBetMutation(success=False, message="Invalid datetime.", bet=None)

            if not expires_at_dt:
                return CreateBetMutation(success=False, message="Invalid datetime format.", bet=None)

            if timezone.is_naive(expires_at_dt):
                expires_at_dt = timezone.make_aware(expires_at_dt)

            if expires_at_dt <= timezone.now():
                return CreateBetMutation(success=False, message="Expiry date must be in the future.", bet=None)

            bet = Bet.objects.create(
                creator = user,
                title = kwargs.get('title'),
                description = kwargs.get('description'),
                option_one = kwargs.get('option_one'),
                option_two = kwargs.get('option_two'),
                expires_at = expires_at_dt
            )

            debug_logger.debug(f"Bet Created Successfully: {bet}")
            return CreateBetMutation(bet=bet, success=True, message=None)
        
        except User.DoesNotExist:
            return CreateBetMutation(bet=None, success=False, message="User Not Found.")

        except Exception as e:
            logger.error(f"Unexpected Error ocurred while creating a Bet: {str(e)}")
            return CreateBetMutation(bet=None, success=False, message="Unexpected error occurred.")


class UpdateBetMutation(graphene.Mutation):
    class Arguments:
        bet_id = graphene.ID(required=True)
        title = graphene.String()
        description = graphene.String()
        option_one = graphene.String()
        option_two = graphene.String()
        expires_at = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()
    bet = graphene.Field(BetType)

    @classmethod
    def mutate(cls, root, info, *args, **kwargs):
        try:
            bet = Bet.objects.get(pk=kwargs.get('bet_id'))
            updated_fields = []

            if kwargs.get("title"):
                bet.title = kwargs.get("title")
                updated_fields.append("title")

            if kwargs.get("description"):
                bet.description = kwargs.get('description')
                updated_fields.append("description")

            if kwargs.get("option_one"):
                bet.option_one = kwargs.get("option_one")
                updated_fields.append("option_one")

            if kwargs.get("option_two"):
                bet.option_two = kwargs.get("option_two")
                updated_fields.append("option_two")

            if kwargs.get("expires_at"):
                try:
                    expires_at_dt = parse_datetime(kwargs.get("expires_at"))
                except ValueError:
                    return UpdateBetMutation(success=False, message="Invalid datetime.", bet=None)
                if not expires_at_dt:
                    return UpdateBetMutation(success=False, message="Invalid datetime format.", bet=None)

                updated_fields.append("expires_at")

            bet.save(update_fields=updated_fields)

            debug_logger.debug(f"Bet Updated Successfully: {bet}")
            return UpdateBetMutation(success=True, message=None, bet=bet)

        except Bet.DoesNotExist:
            return UpdateBetMutation(success=False, message="Bet Not Found.", bet=None)

        except Exception as e:
            logger.error(f"Unexpected Error ocurred while updating a Bet: {str(e)}")
            return UpdateBetMutation(success=False, message="Unexpected error occurred.", bet=None)


class DeleteBetMutation(graphene.Mutation):
    class Arguments:
        bet_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, bet_id):
        try:
            bet = Bet.objects.get(pk=bet_id)
            bet.delete()
            debug_logger.debug(f"Bet Deleted Successfully: {bet}")
            return DeleteBetMutation(success=True, message="Bet deleted successfully.")
        except Bet.DoesNotExist:
            return DeleteBetMutation(success=False, message="Bet not found.")
        except Exception as e:
            logger.error(f"Unexpected error occurred while deleting bet ID {bet_id}: {str(e)}")
            return DeleteBetMutation(success=False, message="Unexpected error occurred.")



class Mutation(graphene.ObjectType):
    create_bet = CreateBetMutation.Field(name="Bet_Create")
    update_bet = UpdateBetMutation.Field(name="Bet_Update")
    delete_bet = DeleteBetMutation.Field(name="Bet_Delete")
