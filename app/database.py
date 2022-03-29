from peewee import Model, SqliteDatabase, UUIDField

db = SqliteDatabase('./sqlite.db')
db.connect()


class BaseModel(Model):
    id = UUIDField(primary_key=True)  # , constraints=[SQL("DEFAULT uuid_generate_v4()")])

    class Meta:
        database = db
