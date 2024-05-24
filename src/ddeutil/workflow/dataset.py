# ------------------------------------------------------------------------------
# Copyright (c) 2022 Korawich Anuttra. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for
# license information.
# ------------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Optional

from fmtutil import Datetime, FormatterGroupType, make_group
from fmtutil.utils import escape_fmt_group
from pydantic import BaseModel, Field
from typing_extensions import Self

try:
    import polars as pl
except ImportError:
    raise ImportError(
        "Please install polars package\n\t\t$ pip install polars"
    ) from None

from .__types import DictData, TupleStr
from .conn import SubclassConn
from .loader import Loader

EXCLUDED_EXTRAS: TupleStr = ("type",)
OBJ_FMTS: FormatterGroupType = make_group(
    {
        "datetime": Datetime,
    }
)


class BaseDataset(BaseModel):
    """Base Dataset Model. This model implement only loading constructor."""

    conn: Annotated[SubclassConn, Field(description="Connection Model")]
    endpoint: Annotated[
        Optional[str],
        Field(description="Endpoint of connection"),
    ] = None
    object: str
    features: list = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_loader(
        cls,
        name: str,
        externals: DictData,
    ) -> Self:
        """Construct Connection with Loader object with specific config name.

        :param name: A name of dataset that want to load from config file.
        :param externals: An external parameters.
        """
        loader: Loader = Loader(name, externals=externals)

        # NOTE: Validate the config type match with current dataset model
        if loader.type != cls:
            raise ValueError(f"Type {loader.type} does not match with {cls}")

        filter_data: DictData = {
            k: loader.data.pop(k)
            for k in loader.data.copy()
            if k not in cls.model_fields and k not in EXCLUDED_EXTRAS
        }

        if "conn" not in loader.data:
            raise ValueError("Dataset config does not set ``conn`` value")

        # NOTE: Start loading connection config
        conn_name: str = loader.data.pop("conn")
        conn_loader: Loader = Loader(conn_name, externals=externals)
        conn_model: SubclassConn = conn_loader.type.from_loader(
            name=conn_name, externals=externals
        )

        # NOTE: Override ``endpoint`` value to getter connection data.
        if "endpoint" in loader.data:
            # NOTE: Update endpoint path without Pydantic validator.
            conn_model.__dict__["endpoint"] = loader.data["endpoint"]
        else:
            loader.data.update({"endpoint": conn_model.endpoint})
        return cls.model_validate(
            obj={
                "extras": (
                    loader.data.pop("extras", {}) | filter_data | externals
                ),
                "conn": conn_model,
                **loader.data,
            }
        )


class Dataset(BaseDataset):

    def exists(self) -> bool:
        raise NotImplementedError("Object exists does not implement")

    def format_object(
        self,
        _object: str | None = None,
        dt: str | datetime | None = None,
    ) -> str:
        """Format the object value that implement datetime"""
        if dt is None:
            dt = datetime.now()
        dt: datetime = (
            dt if isinstance(dt, datetime) else datetime.fromisoformat(dt)
        )
        return (
            OBJ_FMTS({"datetime": dt})
            .format(escape_fmt_group(_object or self.object))
            .replace("\\", "")
        )


class FlDataset(Dataset):

    def exists(self) -> bool:
        return self.conn.find_object(self.object)


class TblDataset(Dataset):

    def exists(self) -> bool:
        return self.conn.find_object(self.object)


class FlDataFrame(Dataset):

    def exists(self) -> bool:
        return self.conn.find_object(self.object)


class TblDataFrame(Dataset): ...


class PandasCSV: ...


class PandasJson: ...


class PandasParq: ...


class PandasDb: ...


class PandasExcel: ...


class PolarsCsvArgs(BaseModel):
    """CSV file should use format rfc4180 as CSV standard format.

    docs: [RFC4180](https://datatracker.ietf.org/doc/html/rfc4180)
    """

    header: bool = True
    separator: str = ","
    skip_rows: int = 0
    encoding: str = "utf-8"


class PolarsCsv(FlDataFrame):
    extras: PolarsCsvArgs

    def load_options(self) -> dict[str, Any]:
        return {
            "has_header": self.extras.header,
            "separator": self.extras.separator,
            "skip_rows": self.extras.skip_rows,
            "encoding": self.extras.encoding,
        }

    def load(
        self,
        _object: str | None = None,
        options: dict[str, Any] | None = None,
        *,
        override: bool = False,
    ) -> pl.DataFrame:
        """Load CSV file to Polars DataFrame with ``read_csv`` method."""
        return pl.read_csv(
            f"{self.conn.get_spec()}/{_object or self.object}",
            **(
                (options or {})
                if override
                else (self.load_options() | (options or {}))
            ),
        )

    def scan(
        self,
        _object: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> pl.LazyFrame:
        """Load CSV file to Polars LazyFrame with ``scan_csv`` method."""
        # FIXME: Save Csv does not support for the fsspec file url.
        return pl.scan_csv(
            f"{self.conn.endpoint}/{_object or self.object}",
            **(self.load_options() | (options or {})),
        )

    def save_options(self) -> dict[str, Any]:
        return {
            "include_header": self.extras.header,
            "separator": self.extras.separator,
        }

    def save(
        self,
        df: pl.DataFrame,
        _object: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Save Polars Dataframe to CSV file with ``write_csv`` method."""
        # FIXME: Save Csv does not support for the fsspec file url.
        return df.write_csv(
            f"{self.conn.endpoint}/{_object or self.object}",
            **(self.save_options() | (options or {})),
        )

    def sink(
        self,
        df: pl.LazyFrame,
        _object: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Save Polars Dataframe to CSV file with ``sink_csv`` method."""
        # FIXME: Save Csv does not support for the fsspec file url.
        return df.sink_csv(
            f"{self.conn.endpoint}/{_object or self.object}",
            **(self.save_options() | (options or {})),
        )


class PolarsJson(FlDataFrame):

    def load(
        self,
        _object: str | None = None,
        options: dict[str, Any] | None = None,
        *,
        dt: str | datetime | None = None,
    ):
        """Load Json file to Polars Dataframe with ``read_json`` method."""
        # FIXME: Load Json does not support for the fsspec file url.
        return pl.read_json(
            f"{self.conn.endpoint}/"
            f"{self.format_object(_object or self.object, dt=dt)}",
            **(options or {}),
        )

    def save(
        self,
        df: pl.DataFrame,
        _object: str | None = None,
        options: dict[str, Any] | None = None,
    ): ...


class PolarsNdJson(FlDataFrame): ...


class PolarsParq(FlDataFrame):

    def save(
        self,
        df: pl.DataFrame,
        _object: str | None = None,
        options: dict[str, Any] | None = None,
    ):
        return df.write_parquet(
            f"{self.conn.endpoint}/{_object or self.object}"
        )


class PostgresTbl(TblDataset): ...


class SqliteTbl(TblDataset): ...


class PolarsPostgres(TblDataFrame): ...
