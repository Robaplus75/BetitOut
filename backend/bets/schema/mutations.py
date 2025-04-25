import graphene
from .types import BetType
from django.contrib.auth import get_user_model
from ..models import Bet, BetOption, BetParticipant
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import logging

# Set up loggers for debugging and error tracking
debug_logger = logging.getLogger("debugger")
logger = logging.getLogger("django")

User = get_user_model()

class CreateBetMutation(graphene.Mutation):
    class Arguments:
        creator_id = graphene.ID(required=True)
        title = graphene.String(required=True)
        description = graphene.String(required=True)
        options = graphene.List(graphene.String, required=True)
        expires_at = graphene.String(required=True)

    bet = graphene.Field(BetType)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, *args, **kwargs):
        try:
            debug_logger.debug(f"CreateBet called with data: {kwargs}")

            user = User.objects.get(pk=kwargs.get('creator_id'))
            debug_logger.debug(f"User found: {user.username}")

            # Parse and validate the datetime
            try:
                expires_at_dt = parse_datetime(kwargs.get("expires_at"))
            except ValueError:
                logger.error("Invalid datetime value received.")
                return CreateBetMutation(success=False, message="Invalid datetime.", bet=None)

            if not expires_at_dt:
                logger.error("Datetime parsing failed.")
                return CreateBetMutation(success=False, message="Invalid datetime format. Use ISO 8601 format like '2025-04-25T15:30:00Z'.", bet=None)

            # Make timezone-aware and ensure it's in the future
            if timezone.is_naive(expires_at_dt):
                expires_at_dt = timezone.make_aware(expires_at_dt)
            if expires_at_dt <= timezone.now():
                logger.error("Expiry datetime is in the past.")
                return CreateBetMutation(success=False, message="Expiry date must be in the future.", bet=None)

            # Validate and clean title
            title = kwargs.get("title", "").strip()
            if not title:
                return CreateBetMutation(success=False, message="Title cannot be empty.", bet=None)

            # Validate and clean description
            description = kwargs.get("description", "").strip()
            if not description:
                return CreateBetMutation(success=False, message="Description cannot be empty.", bet=None)

            # Validate and deduplicate options
            options = kwargs.get("options", [])
            options = [opt.strip() for opt in options if opt.strip()]
            seen = set()
            unique_options = []
            for opt in options:
                normalized = opt.lower()
                if normalized not in seen:
                    seen.add(normalized)
                    unique_options.append(opt)
            options = unique_options

            if len(options) < 2:
                return CreateBetMutation(success=False, message="At least two options are required.", bet=None)

            # Create the bet
            bet = Bet.objects.create(
                creator=user,
                title=title,
                description=description,
                expires_at=expires_at_dt
            )
            debug_logger.debug(f"Bet created: {bet}")

            # Create associated bet options
            BetOption.objects.bulk_create([
                BetOption(bet=bet, text=option_text) for option_text in options
            ])
            debug_logger.debug(f"BetOptions created: {options}")

            return CreateBetMutation(bet=bet, success=True, message=None)

        except User.DoesNotExist:
            logger.error(f"User not found with id {kwargs.get('creator_id')}")
            return CreateBetMutation(bet=None, success=False, message="User Not Found.")

        except Exception as e:
            logger.error(f"Unexpected Error while creating a Bet: {str(e)}", exc_info=True)
            return CreateBetMutation(bet=None, success=False, message="Unexpected error occurred.")

class UpdateBetMutation(graphene.Mutation):
    class Arguments:
        bet_id = graphene.ID(required=True)
        title = graphene.String()
        description = graphene.String()
        options = graphene.List(graphene.String)
        expires_at = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()
    bet = graphene.Field(BetType)

    @classmethod
    def mutate(cls, root, info, *args, **kwargs):
        try:
            debug_logger.debug(f"UpdateBet called with data: {kwargs}")
            bet = Bet.objects.get(pk=kwargs.get('bet_id'))
            updated_fields = []

            # Prevent updating options if bets have been placed
            if kwargs.get("options") and BetParticipant.objects.filter(bet=bet).exists():
                logger.error(f"Attempt to change options after participation: Bet ID {bet.id}")
                return UpdateBetMutation(
                    success=False,
                    message="Cannot update options because a user has already placed a bet.",
                    bet=None
                )

            # Update title if provided
            if kwargs.get("title"):
                bet.title = kwargs.get("title").strip()
                updated_fields.append("title")

            # Update description if provided
            if kwargs.get("description"):
                bet.description = kwargs.get('description').strip()
                updated_fields.append("description")

            # Update options if provided and valid
            if kwargs.get("options"):
                options = kwargs.get("options", [])
                options = [opt.strip() for opt in options if opt.strip()]
                seen = set()
                unique_options = []
                for opt in options:
                    normalized = opt.lower()
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_options.append(opt)
                options = unique_options

                if len(options) < 2:
                    return UpdateBetMutation(success=False, message="At least two options are required.", bet=None)

                # Replace old options
                bet.options.all().delete()
                for option_text in options:
                    BetOption.objects.create(bet=bet, text=option_text)
                debug_logger.debug(f"Updated options for Bet ID {bet.id}: {options}")

            # Update expiration if provided
            if kwargs.get("expires_at"):
                try:
                    expires_at_dt = parse_datetime(kwargs.get("expires_at"))
                except ValueError:
                    logger.error("Invalid datetime received while updating bet.")
                    return UpdateBetMutation(success=False, message="Invalid datetime format. Use ISO 8601 format like '2025-04-25T15:30:00Z'.", bet=None)

                if not expires_at_dt:
                    logger.error("Datetime parsing failed while updating bet.")
                    return UpdateBetMutation(success=False, message="Invalid datetime format.", bet=None)

                if timezone.is_naive(expires_at_dt):
                    expires_at_dt = timezone.make_aware(expires_at_dt)
                if expires_at_dt <= timezone.now():
                    return UpdateBetMutation(success=False, message="Expiry date must be in the future.", bet=None)

                bet.expires_at = expires_at_dt
                updated_fields.append("expires_at")

            bet.save(update_fields=updated_fields)
            debug_logger.debug(f"Bet Updated Successfully: {bet}")
            return UpdateBetMutation(success=True, message="Bet updated successfully.", bet=bet)

        except Bet.DoesNotExist:
            logger.error(f"Bet not found with ID: {kwargs.get('bet_id')}")
            return UpdateBetMutation(success=False, message="Bet Not Found.", bet=None)

        except Exception as e:
            logger.error(f"Unexpected Error while updating Bet ID {kwargs.get('bet_id')}: {str(e)}", exc_info=True)
            return UpdateBetMutation(success=False, message="Unexpected error occurred.", bet=None)

class DeleteBetMutation(graphene.Mutation):
    class Arguments:
        bet_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, bet_id):
        try:
            debug_logger.debug(f"DeleteBet called with ID: {bet_id}")
            bet = Bet.objects.get(pk=bet_id)
            bet.delete()
            debug_logger.debug(f"Bet Deleted Successfully: {bet}")
            return DeleteBetMutation(success=True, message="Bet deleted successfully.")
        except Bet.DoesNotExist:
            logger.error(f"Delete failed. Bet not found: {bet_id}")
            return DeleteBetMutation(success=False, message="Bet not found.")
        except Exception as e:
            logger.error(f"Unexpected error while deleting Bet ID {bet_id}: {str(e)}", exc_info=True)
            return DeleteBetMutation(success=False, message="Unexpected error occurred.")

# Register mutations in the schema
class Mutation(graphene.ObjectType):
    create_bet = CreateBetMutation.Field(name="Bet_Create")
    update_bet = UpdateBetMutation.Field(name="Bet_Update")
    delete_bet = DeleteBetMutation.Field(name="Bet_Delete")
