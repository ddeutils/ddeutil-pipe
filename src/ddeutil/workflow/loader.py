# ------------------------------------------------------------------------------
# Copyright (c) 2022 Korawich Anuttra. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for
# license information.
# ------------------------------------------------------------------------------
from __future__ import annotations

import copy
import logging
import urllib.parse
from functools import cached_property
from typing import Any

from ddeutil.core import (
    clear_cache,
    getdot,
    hasdot,
    import_string,
    setdot,
)
from ddeutil.io import (
    ConfigNotFound,
    Params,
    PathSearch,
    Register,
    YamlEnvFl,
    map_func,
)
from ddeutil.io.__conf import UPDATE_KEY, VERSION_KEY
from fmtutil import Datetime
from typing_extensions import Self

from .__types import DictData, TupleStr
from .exceptions import ConfigArgumentError

YamlEnvQuote = YamlEnvFl
YamlEnvQuote.prepare = staticmethod(lambda x: urllib.parse.quote_plus(str(x)))


class BaseLoad:
    """Base configuration data loading object for load config data from
    `cls.load_stage` stage. The base loading object contain necessary
    properties and method for type object.

    :param data: dict : A configuration data content with fix keys, `name`,
        `fullname`, and `data`.
    :param params: Optional[dict] : A parameters mapping for some
        subclass of loading use.
    """

    # NOTE: Set loading config for inherit
    load_prefixes: TupleStr = ("conn",)
    load_datetime_name: str = "audit_date"
    load_datetime_fmt: str = "%Y-%m-%d %H:%M:%S"

    # NOTE: Set preparing config for inherit
    data_excluded: TupleStr = (UPDATE_KEY, VERSION_KEY)
    option_key: TupleStr = ("parameters",)
    datetime_key: TupleStr = ("endpoint",)

    @classmethod
    def from_register(
        cls,
        name: str,
        params: Params,
        externals: DictData | None = None,
    ) -> Self:
        """Loading config data from register object.

        :param name: A name of config data catalog that can register.
        :type name: str
        :param params: A params object.
        :type params: Params
        :param externals: A external parameters
        :type externals: DictData | None(=None)
        """
        try:
            rs: Register = Register(
                name=name,
                stage=params.stage_final,
                params=params,
                loader=YamlEnvQuote,
            )
        except ConfigNotFound:
            rs: Register = Register(
                name=name,
                params=params,
                loader=YamlEnvQuote,
            ).deploy(stop=params.stage_final)
        return cls(
            name=rs.name,
            data=rs.data().copy(),
            params=params,
            externals=externals,
        )

    def __init__(
        self,
        name: str,
        data: DictData,
        params: Params,
        externals: DictData | None = None,
    ) -> None:
        """Main initialize base config object which get a name of configuration
        and load data by the register object.
        """
        self.name: str = name
        self.__data: DictData = data
        self.params: Params = params
        self.externals: DictData = externals or {}

        # NOTE: Validate step of base loading object.
        if not any(
            self.name.startswith(prefix) for prefix in self.load_prefixes
        ):
            raise ConfigArgumentError(
                "prefix",
                (
                    f"{self.name!r} does not starts with the "
                    f"{self.__class__.__name__} prefixes: "
                    f"{self.load_prefixes!r}."
                ),
            )

    @property
    def updt(self):
        return self.data.get(UPDATE_KEY)

    @cached_property
    def _map_data(self) -> DictData:
        """Return configuration data without key in the excluded key set."""
        data: DictData = self.__data.copy()
        rs: DictData = {k: data[k] for k in data if k not in self.data_excluded}

        # Mapping datetime format to string value.
        for _ in self.datetime_key:
            if hasdot(_, rs):
                # Fill format datetime object to any type value.
                rs: DictData = setdot(
                    _,
                    rs,
                    map_func(
                        getdot(_, rs),
                        Datetime.parse(
                            value=self.externals[self.load_datetime_name],
                            fmt=self.load_datetime_fmt,
                        ).format,
                    ),
                )
        return rs

    @property
    def data(self) -> DictData:
        """Return deep copy of the input data.

        :rtype: DictData
        """
        return copy.deepcopy(self._map_data)

    @clear_cache(attrs=("type", "_map_data"))
    def refresh(self) -> Self:
        """Refresh configuration data. This process will use `deploy` method
        of the register object.
        """
        return self.from_register(
            name=self.name,
            params=self.params,
            externals=self.externals,
        )

    @cached_property
    def type(self):
        """Return object type which implement in `config_object` key."""
        if not (_typ := self.data.get("type")):
            raise ValueError(
                f"the 'type' value: {_typ} does not exists in config data."
            )
        return import_string(f"ddeutil.pipe.{_typ}")


class SimLoad:

    def __init__(self, name: str, params: Params, externals: DictData):
        self.data = {}
        for file in PathSearch(params.engine.paths.conf).files:
            if any(file.suffix.endswith(s) for s in ("yml", "yaml")) and (
                data := YamlEnvQuote(file).read().get(name, {})
            ):
                self.data = data
        if not self.data:
            raise ConfigNotFound(f"Config {name!r} does not found on conf path")
        self.__conf_params = params
        self.externals = externals

    @cached_property
    def type(self):
        """Return object type which implement in `config_object` key."""
        if not (_typ := self.data.get("type")):
            raise ValueError(
                f"the 'type' value: {_typ} does not exists in config data."
            )
        try:
            # NOTE: Auto adding module prefix if it does not set
            return import_string(f"ddeutil.workflow.{_typ}")
        except ModuleNotFoundError:
            return import_string(f"{_typ}")

    def params(self, param: dict[str, Any]) -> dict[str, Any]:
        if not (p := self.data.get("params", {})):
            return p
        try:
            return {
                i: import_string(f"ddeutil.workflow.{p[i]}")(param[i])
                for i in p
            }
        except ModuleNotFoundError as err:
            logging.error(err)
            raise err
        except KeyError as err:
            logging.error(f"Parameter: {err} does not exists from passing")
            raise err
        except ValueError as err:
            logging.error("Value that passing to params does not valid")
            raise err


class Conn(BaseLoad):

    @cached_property
    def type(self) -> Any:
        return super().type

    def link(self):
        """Return the connection instance."""
        return self.type.from_dict(self.data)
