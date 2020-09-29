import graphene

from .generics_utils import (
    decorate_mutate_func,
    define_mutation_errors,
    create_default_create_function,
    default_update_function,
    default_delete_function,
)
from .types import MutationPayload


class DefaultMutationOptions(graphene.types.mutation.MutationOptions):
    checks: list = None  # iterable of tuples (error_class, checker (will receive mutate args))
    auth_required: bool = None
    # root: MutationRoot = None
    # root_name: str = None
    root_required: bool = None


class DefaultMutation(MutationPayload, graphene.Mutation):

    @classmethod
    def __init_subclass_with_meta__(
            cls, resolver=None, output=None, arguments=None, _meta=None,
            checks=None, auth_required=True, record_type=None, root_required=False,
            **options
    ):
        checks = checks or []
        if not _meta:
            _meta = DefaultMutationOptions(cls)

        _meta.auth_required = auth_required
        _meta.checks = checks
        _meta.root_required = root_required

        define_mutation_errors(cls, checks)
        if record_type:
            cls.record = graphene.Field(record_type, default_value=None, description='Обработанная сущность')

        super(DefaultMutation, cls).__init_subclass_with_meta__(
            resolver=resolver, output=output, arguments=arguments, _meta=_meta, **options
        )

    @classmethod
    def mutate(cls, root, info, **kwargs):
        raise NotImplementedError('Mutate is not implemented for {}'.format(cls.__name__))

    @classmethod
    def Field(cls, name=None, description=None, deprecation_reason=None, required=False):
        pre_mutate = getattr(cls, 'pre_mutate', lambda *args, **kwargs: None)

        return graphene.Field(
            cls._meta.output,
            args=cls._meta.arguments,
            resolver=decorate_mutate_func(cls._meta.resolver, pre_mutate, cls, cls._meta),
            name=name,
            description=description,
            deprecation_reason=deprecation_reason,
            required=required,
        )


class CreateMutationOptions(DefaultMutationOptions):
    create_function = None
    model = None
    include_user = None
    user_field_name = None


class CreateMutation(DefaultMutation):

    @classmethod
    def __init_subclass_with_meta__(
            cls, resolver=None, output=None, arguments=None,
            create_function=None, model=None, include_user=True, user_field_name='owner',
            _meta=None, **options
    ):
        if not _meta:
            _meta = CreateMutationOptions(cls)

        assert create_function or model, 'You must provide model or create_function in CreateMutation Meta'
        _meta.create_function = create_function or create_default_create_function(model, include_user, user_field_name)
        super(CreateMutation, cls).__init_subclass_with_meta__(
            resolver=resolver, output=output, arguments=arguments, _meta=_meta, **options
        )

    @classmethod
    def mutate(cls, root, info, input, **kwargs):
        instance = cls._meta.create_function(user=info.context.user, **input.__dict__)

        post_mutate = getattr(cls, 'post_mutate', None)
        if callable(post_mutate):
            return post_mutate(instance, user=info.context.user)

        return cls(record=instance)


class UpdateMutationOptions(graphene.types.objecttype.ObjectTypeOptions):
    pass


class UpdateMutation(DefaultMutation):

    @classmethod
    def mutate(cls, instance, info, input):
        instance = default_update_function(instance, user=info.context.user, **input.__dict__)

        post_mutate = getattr(cls, 'post_mutate', None)
        if callable(post_mutate):
            return post_mutate(instance, user=info.context.user)

        return cls(record=instance)


class DeleteMutationOptions(graphene.types.objecttype.ObjectTypeOptions):
    pass


class DeleteMutation(DefaultMutation):

    @classmethod
    def mutate(cls, instance, info, errors=None):
        errors = errors or set()
        default_delete_function(instance, user=info.context.user)
        return cls()
