from base64 import b32encode
from hashlib import sha3_224
from typing import Type, Tuple, Union, Optional

from pydantic import BaseModel
from tortoise import Model
from tortoise.contrib.pydantic import PydanticModel, PydanticListModel, pydantic_model_creator, \
    pydantic_queryset_creator
from tortoise.queryset import MODEL, QuerySet

from utils.exceptions import NotFound


class OrmModel(BaseModel):
    class Config:
        orm_mode = True


def _404_message(cls: Type[MODEL], kwargs: dict) -> str:
    message = ''
    for k, v in kwargs.items():
        message += f'{k}={v}, '
    return f'{cls.__name__} ({message[:-2]}) does not exist'


async def exists_or_404(cls: Type[MODEL], *args, **kwargs) -> bool:
    if not await cls.filter(*args, **kwargs).exists():
        raise NotFound(_404_message(cls, kwargs))
    return True


async def get_object_or_404(cls: Type[MODEL], *args, **kwargs) -> MODEL:
    instance = await cls.get_or_none(*args, **kwargs)
    if not instance:
        raise NotFound(_404_message(cls, kwargs))
    return instance


async def serialize(obj: Union[MODEL, QuerySet], cls: Union[PydanticModel, PydanticListModel]) -> dict:
    if isinstance(obj, Model):
        return (await cls.from_tortoise_orm(obj)).dict()
    elif isinstance(obj, QuerySet):
        model = await cls.from_queryset(obj)
        return model.dict()['__root__']


def models_creator(cls: Type[Model], **kwargs) -> Tuple[Type[PydanticModel], Type[PydanticListModel]]:
    return pmc(cls, **kwargs), pqc(cls, **kwargs)


# fix name bug

def pmc(
        cls: "Type[Model]",
        *,
        name: object = None,
        exclude: Tuple[str, ...] = (),
        include: Tuple[str, ...] = (),
        computed: Tuple[str, ...] = (),
        allow_cycles: Optional[bool] = None,
        sort_alphabetically: Optional[bool] = None,
        _stack: tuple = (),
        exclude_readonly: bool = False,
        meta_override: Optional[Type] = None,
) -> Type[PydanticModel]:
    fqname = cls.__module__ + "." + cls.__qualname__
    postfix = ""

    def get_name() -> str:
        # If arguments are specified (different from the defaults), we append a hash to the
        # class name, to make it unique
        # We don't check by stack, as cycles get explicitly renamed.
        # When called later, include is explicitly set, so fence passes.
        nonlocal postfix
        is_default = (
                exclude == ()
                and include == ()
                and computed == ()
                and sort_alphabetically is None
                and allow_cycles is None
        )
        hashval = (
            f"{fqname};{exclude};{include};{computed};{_stack}:{sort_alphabetically}:{allow_cycles}"
        )
        postfix = (
            "." + b32encode(sha3_224(hashval.encode("utf-8")).digest()).decode("utf-8").lower()[:6]
            if not is_default
            else ""
        )
        return fqname + postfix

    return pydantic_model_creator(cls, name=name or get_name(), exclude=exclude, include=include, computed=computed,
                                  allow_cycles=allow_cycles, sort_alphabetically=sort_alphabetically,
                                  exclude_readonly=exclude_readonly, meta_override=meta_override)


def pqc(
        cls: "Type[Model]",
        *,
        name=None,
        exclude: Tuple[str, ...] = (),
        include: Tuple[str, ...] = (),
        computed: Tuple[str, ...] = (),
        allow_cycles: Optional[bool] = None,
        sort_alphabetically: Optional[bool] = None,
) -> Type[PydanticListModel]:
    fqname = cls.__module__ + "." + cls.__qualname__
    postfix = ""

    def get_name() -> str:
        # If arguments are specified (different from the defaults), we append a hash to the
        # class name, to make it unique
        # We don't check by stack, as cycles get explicitly renamed.
        # When called later, include is explicitly set, so fence passes.
        nonlocal postfix
        is_default = (
                exclude == ()
                and include == ()
                and computed == ()
                and sort_alphabetically is None
                and allow_cycles is None
        )
        hashval = (
            f"{fqname};{exclude};{include};{computed};{sort_alphabetically}:{allow_cycles}"
        )
        postfix = (
            "." + b32encode(sha3_224(hashval.encode("utf-8")).digest()).decode("utf-8").lower()[:6]
            if not is_default
            else ""
        )
        return fqname + postfix + "_list"

    return pydantic_queryset_creator(cls, name=name or get_name(), exclude=exclude, include=include, computed=computed,
                                     allow_cycles=allow_cycles, sort_alphabetically=sort_alphabetically)
