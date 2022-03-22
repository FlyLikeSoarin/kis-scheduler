from peewee import IntegerField, FloatField


class WithResourceDataMixin:
    cpu_cores = IntegerField(null=True)
    ram = FloatField(null=True)
    disk = FloatField(null=True)
