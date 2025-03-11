import functools
from pathlib import Path
import pandas as pd
import os
import time
from inversebias.data.utils import create_dtype
from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from inversebias.config import settings


class InverseBiasEngine:
    _instance = None
    _engine = None
    _last_modified = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InverseBiasEngine, cls).__new__(cls)
            cls._create_engine()
        return cls._instance

    @classmethod
    def _create_engine(cls):

        # Create the engine with PostgreSQL connection
        cls._engine = create_engine(
            settings.database.uri,
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
            pool_pre_ping=True,  # Verify connections before using them
        )

    @property
    def engine(self) -> Engine:
        # No need to check for file modification with PostgreSQL
        return self._engine


def get_table(table_name, return_if_not_exists=False):
    engine = InverseBiasEngine().engine

    if not table_exists(table_name):
        if return_if_not_exists:
            return pd.DataFrame()
        raise ValueError(f"Invalid table name: '{table_name}'")

    query = text(f"SELECT * FROM {table_name}")
    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    return df


def upload_to_table(primary_key="url", table_name=None, verbose=False, upload=True):
    """
    Decorator that uploads the function's return value to a database table.

    Args:
        primary_key (str): The primary key for the table.
        table_name (str, optional): The name of the table. If None, it will be inferred.
        verbose (bool, optional): Whether to print verbose output.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if kwargs.get("upload", False):
                actual_table_name = table_name
                table_upload(
                    df=result,
                    primary_key=primary_key,
                    table_name=actual_table_name,
                    verbose=kwargs.get("verbose", verbose),
                )
            return result

        return wrapper

    return decorator


def table_exists(table_name: str) -> bool:
    engine = InverseBiasEngine().engine
    return table_name in inspect(engine).get_table_names()


def sql_append_df(df: pd.DataFrame, table_name: str, dtype: dict | None = None):
    engine = InverseBiasEngine().engine

    with engine.connect() as conn:
        df.to_sql(
            table_name,
            conn,
            if_exists="append",
            index=False,
            dtype=dtype,
        )


def sql_replace_df(df: pd.DataFrame, table_name: str, primary_key: str):
    dtype = create_dtype(df)
    engine = InverseBiasEngine().engine

    with engine.connect() as conn:
        # For PostgreSQL, we need to handle the primary key differently
        # Drop the table if it exists and create a new one
        conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        conn.commit()

        # Now create the table with proper primary key
        df.to_sql(
            table_name,
            conn,
            if_exists="replace",
            index=False,
            dtype=dtype,
        )

        # Add primary key constraint
        conn.execute(text(f"ALTER TABLE {table_name} ADD PRIMARY KEY ({primary_key})"))
        conn.commit()


def table_upload(df: pd.DataFrame, table_name: str, primary_key: str, verbose=False):
    dtype = None
    if table_exists(table_name=table_name):
        table = get_table(table_name)
        df = df.loc[~df[primary_key].isin(table[primary_key])]
        if df.empty:
            return
    else:
        dtype = create_dtype(df)

    sql_append_df(
        df=df.drop_duplicates(subset=primary_key), table_name=table_name, dtype=dtype
    )

    if verbose:
        print(f"Uploaded {len(df)} rows to the {table_name} table in the database.")
