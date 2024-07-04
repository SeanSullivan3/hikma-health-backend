from abc import abstractmethod
from __future__ import annotations
from typing import override

from psycopg.connection import Connection
from psycopg.rows import dict_row

from hikmahealth.entity.base import BaseEntity
from typing import Optional

class ISyncDown(object):
    @classmethod
    @abstractmethod
    def get_delta_records(self, last_sync_time: int | str, *args, **kwargs) -> DeltaData:
        """Return the difference in data that was created, updated, or deleted since
         last sync time.
         
         Implement this to prevent the code base from exploding"""
        raise NotImplementedError()


class DeltaData(object):
    """Handles database delta data"""
    def __init__(self, 
                 created: list[dict] | None = None, 
                 updated: list[dict] | None = None, 
                 deleted: list[dict] | None = None):
        self.created = created if created is not None else []
        self.updated = updated if updated is not None else []
        self.deleted = deleted if deleted is not None else []

    def to_dict(self):
        return dict(
            created=self.created,
            updated=self.updated,
            deleted=self.deleted
        )
    




# should be move to a different structure. since it depends on psycopg to
# execute properly
class SyncDownEntity(ISyncDown, BaseEntity):
    """For entity that expects to apply changes from server to client"""
    @classmethod
    @override
    def get_delta_records(cls, last_sync_time: int | str, conn: Connection): 
        with conn.cursor(row_factory=dict_row) as cur:
            newrecords = cur.execute(
                f"SELECT * from {cls.TABLE_NAME} WHERE server_created_at > %s AND deleted_at IS NULL",
                (last_sync_time, )
            ).fetchall()

            updatedrecords = cur.execute(
            f"SELECT * FROM {cls.TABLE_NAME} WHERE last_modified > %s AND server_created_at < %s AND deleted_at IS NULL",
                (last_sync_time, last_sync_time),
            ).fetchall()

            deleterecords = cur.execute(
            f"SELECT id FROM {cls.TABLE_NAME} WHERE deleted_at > %s",
            (last_sync_time,)).fetchall()

            return DeltaData(
                created=newrecords,
                updated=updatedrecords,
                deleted=deleterecords
            )
        
class ISyncUp(object):
    """Abstract for entities that expect to apply changes from client to server"""
    @classmethod
    @abstractmethod
    def apply_delta_changes(cls, deltadata: DeltaData, last_pushed_at: int | str, conn: Connection):
        raise NotImplementedError(f"require that the {__class__} implement this to syncronize from client")
    
class SyncronizableEntity(SyncDownEntity, ISyncUp):
    pass