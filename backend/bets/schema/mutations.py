import graphene
from .types import BetType, BetParticipantType
from django.contrib.auth import get_user_model
from ..models import Bet, BetOption, BetParticipant
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from decimal import Decimal
import logging
from django.db import transaction

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
        judge_id = graphene.ID(required=True)

    bet = graphene.Field(BetType)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, *args, **kwargs):
        try:
            debug_logger.debug(f"CreateBet called with data: {kwargs}")

            # get the creator user
            user = User.objects.get(pk=kwargs.get('creator_id'))
            debug_logger.debug(f"User found: {user.username}")

            # get the judge user
            judge = User.objects.get(pk=kwargs.get('judge_id'))
            debug_logger.debug(f"Judge found: {judge.username}")

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
                judge=judge,
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
            logger.error(f"User or Judge not found with id {kwargs.get('creator_id')} or {kwargs.get('judge_id')}")
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

class CreateBetParticipant(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID(required=True)
        bet_id = graphene.ID(required=True)
        stake = graphene.Decimal(required=True)
        bet_option_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    bet_participant = graphene.Field(BetParticipantType)

    @classmethod
    def mutate(cls, root, info, user_id, bet_id, stake, bet_option_id):
        try:
            user = User.objects.get(pk=user_id)
            bet = Bet.objects.get(pk=bet_id)
            betOption = BetOption.objects.get(pk=bet_option_id)

            # Check if user is not the judge
            if bet.judge_id == user.id:
                return CreateBetParticipant(
                    success=False,
                    message="The judge cannot participate in the bet.",
                    bet_participant=None
                )
            # Check if the bet is resolved
            if bet.is_resolved:
                return CreateBetParticipant(success=False, message="This bet has already been resolved.", bet_participant=None)

            if BetParticipant.objects.filter(bet=bet, user=user).exists():
                return CreateBetParticipant(success=False, message="User has already participated in this bet.", bet_participant=None)

            # Check if it's expired
            if bet.expires_at < timezone.now():
                return CreateBetParticipant(success=False, message="This bet has expired.", bet_participant=None)

            # Check if the option belongs to the right bet
            if betOption.bet_id != bet.id:
                return CreateBetParticipant(success=False, message="This option does not belong to the selected bet.", bet_participant=None)

            # Check if stake is valid
            stake = Decimal(stake)
            if stake <= 0:
                return CreateBetParticipant(success=False, message="Stake must be greater than 0.", bet_participant=None)

            with transaction.atomic():
                betparticipant = BetParticipant.objects.create(
                    user=user,
                    bet=bet,
                    chosen_option=betOption,
                    stake=stake
                )
            debug_logger.debug("Bet Participant Created Successfully")

            return CreateBetParticipant(success=True, message=None, bet_participant=betparticipant)

        except User.DoesNotExist:
            logger.error(f"CreateBetParticipant: user not found: {user_id}, bet_id: {bet_id}")
            return CreateBetParticipant(success=False, message="User not found.", bet_participant=None)
        except Bet.DoesNotExist:
            logger.error(f"CreateBetParticipant: bet not found: {bet_id}")
            return CreateBetParticipant(success=False, message="Bet not found.", bet_participant=None)
        except BetOption.DoesNotExist:
            logger.error(f"CreateBetParticipant: betOption not found: {bet_option_id}")
            return CreateBetParticipant(success=False, message="BetOption not found.", bet_participant=None)
        except IntegrityError:
            logger.error(f"Integrity error while creating BetParticipant")
            return CreateBetParticipant(success=False, message="Database integrity error.", bet_participant=None)
        except TransactionManagementError:
            logger.error(f"Error managing transaction while creating BetParticipant")
            return CreateBetParticipant(success=False, message="Transaction management error.", bet_participant=None)
        except Exception as e:
            logger.error(f"Unexpected error while creating a bet Participant: {str(e)}", exc_info=True)
            return CreateBetParticipant(success=False, message="Unexpected error occurred.", bet_participant=None)


class ResolveBetMutation(graphene.Mutation):
    class Arguments:
        judge_id = graphene.ID(required=True)
        bet_id = graphene.ID(required=True)
        winning_option_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    bet = graphene.Field(BetType)

    @classmethod
    def mutate(cls, root, info, judge_id, bet_id, winning_option_id):
        try:
            judge = User.objects.get(pk=judge_id)
            bet = Bet.objects.get(pk=bet_id)
            winning_option = BetOption.objects.get(pk=winning_option_id)

            if bet.judge_id != judge.id:
                debug_logger.debug(f"User {judge.id} attempted to resolve bet {bet.id} but is not the judge.")
                return ResolveBetMutation(success=False, message="Only the judge can resolve this bet.", bet=None)

            if bet.is_resolved:
                debug_logger.debug(f"Bet {bet.id} already resolved.")
                return ResolveBetMutation(success=False, message="This bet is already resolved.", bet=None)

            if winning_option.bet_id != bet.id:
                debug_logger.debug(f"Option {winning_option.id} does not belong to Bet {bet.id}.")
                return ResolveBetMutation(success=False, message="Selected option does not belong to this bet.", bet=None)

            bet.is_resolved = True
            bet.winner_option = winning_option
            bet.resolved_at = timezone.now()
            bet.save(update_fields=["is_resolved", "winner_option", "resolved_at"])

            debug_logger.debug(
                f"Bet {bet.id} resolved successfully by judge {judge.username}. "
                f"Winning option: {winning_option.id} - '{winning_option.text}'"
            )

            return ResolveBetMutation(success=True, message="Bet resolved successfully.", bet=bet)

        except User.DoesNotExist:
            logger.warning(f"Judge with ID {judge_id} not found while resolving bet {bet_id}.")
            return ResolveBetMutation(success=False, message="Judge not found.", bet=None)

        except Bet.DoesNotExist:
            logger.warning(f"Bet with ID {bet_id} not found.")
            return ResolveBetMutation(success=False, message="Bet not found.", bet=None)

        except BetOption.DoesNotExist:
            logger.warning(f"Option with ID {winning_option_id} not found while resolving bet {bet_id}.")
            return ResolveBetMutation(success=False, message="Winning option not found.", bet=None)

        except Exception as e:
            logger.error(f"Unexpected error while resolving bet {bet_id}: {str(e)}", exc_info=True)
            return ResolveBetMutation(success=False, message="Unexpected error occurred.", bet=None)



# Register mutations in the schema
class Mutation(graphene.ObjectType):
    create_bet = CreateBetMutation.Field(name="Bet_Create")
    update_bet = UpdateBetMutation.Field(name="Bet_Update")
    delete_bet = DeleteBetMutation.Field(name="Bet_Delete")
    create_bet_participant = CreateBetParticipant.Field(name="Bet_Participant_Create")
    resolve_bet = ResolveBetMutation.Field(name="Bet_Resolve")
