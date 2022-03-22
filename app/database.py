from peewee import *

db = SqliteDatabase('./sqlite.db')


class BaseModel(Model):
    id = UUIDField(constraints=[SQL("DEFAULT uuid_generate_v4()")], primary_key=True)

    class Meta:
        database = db
