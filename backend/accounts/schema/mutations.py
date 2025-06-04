import logging
import graphene
import re
from graphene_django.types import DjangoObjectType
from accounts.models import Wallet
from .types import UserType, WalletType
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.validators import validate_email
from django.contrib.auth import authenticate
from graphql_jwt.shortcuts import get_token

User = get_user_model()

debug_logger = logging.getLogger("debugger")
logger = logging.getLogger("django")


class CreateUser(graphene.Mutation):
    user = graphene.Field(UserType)
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        phone = graphene.String(required=True)
        email = graphene.String(required=False)
        first_name = graphene.String(required=True)
        last_name = graphene.String(required=True)
        password = graphene.String(required=True)

    def mutate(self, info, phone, first_name, last_name, password, email=None):
        try:
            # Validate phone number format
            debug_logger.debug("Validating Phone")
            phone_pattern = r"^(?:\+251|0)?9\d{8}$"
            if not re.match(phone_pattern, phone):
                return CreateUser(success=False, message="Invalid phone number format.")

            debug_logger.debug("Validating Phone If it already Exists")
            if User.objects.filter(phone=phone).exists():
                return CreateUser(success=False, message="Phone number already in use.")

            # Validate email if provided
            debug_logger.debug("Validating Email")
            if email:
                try:
                    validate_email(email)
                except ValidationError:
                    return CreateUser(success=False, message="Invalid email format.")
                if User.objects.filter(email=email).exists():
                    return CreateUser(success=False, message="Email already in use.")

            debug_logger.debug("Creating user with phone=%s", phone)

            with transaction.atomic():
                user = User.objects.create_user(
                    phone=phone,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password
                )
                Wallet.objects.create(user=user)

            debug_logger.debug("User and wallet created: user_id=%s", user.id)
            return CreateUser(user=user, success=True, message="User created successfully.")

        except Exception as e:
            logger.error("Error creating user: %s", str(e), exc_info=True)
            return CreateUser(success=False, message="Server error. Please try again.")


class PhoneLogin(graphene.Mutation):
    user = graphene.Field(UserType)
    token = graphene.String()
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        phone = graphene.String(required=True)
        password = graphene.String(required=True)

    def mutate(self, info, phone, password):
        # Validate phone number format
        debug_logger.debug("Validating Phone")
        phone_pattern = r"^(?:\+251|0)?9\d{8}$"
        if not re.match(phone_pattern, phone):
            return PhoneLogin(success=False, message="Invalid phone number format.")

        user = User.objects.get(phone=phone)

        if not user.is_active:
            return PhoneLogin(success=False, message="Account is inactive.")

        user = authenticate(username=phone, password=password)

        if user is None:
            return PhoneLogin(success=False, message="Invalid credentials.") 

        token = get_token(user)
        return PhoneLogin(user=user, token=token, success=True)

class SoftDeleteUser(graphene.Mutation):
    user = graphene.Field(UserType)
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        phone = graphene.String(required=True)

    def mutate(self, info, phone):
        try:
            # Validate phone number format
            debug_logger.debug("Validating Phone")
            phone_pattern = r"^(?:\+251|0)?9\d{8}$"
            if not re.match(phone_pattern, phone):
                return SoftDeleteUser(success=False, message="Invalid phone number format.")

            debug_logger.debug("Attempting to soft delete user with ID: %s", id)
            user = User.objects.get(phone=phone)

            if user.is_deleted:
                logger.warning("User %s already soft-deleted", id)
                return SoftDeleteUser(success=False, message="User already deleted.")

            user.is_deleted = True
            user.is_active = False
            user.save()

            debug_logger.debug("User %s soft-deleted successfully", id)
            return SoftDeleteUser(user=user, success=True)

        except User.DoesNotExist:
            logger.warning("User with Phone %s not found for deletion", phone)
            return SoftDeleteUser(success=False, message="User does not exist.")

        except Exception as e:
            logger.error("Unexpected error while soft deleting user %s: %s", id, str(e), exc_info=True)
            raise SoftDeleteUser(success=False, message="Failed to delete user.")

class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field(name="User_Create")
    soft_delete_user = SoftDeleteUser.Field(name="User_Delete_Soft")
    phone_login = PhoneLogin.Field(name="User_Login")