from peewee import FloatField, IntegerField, Model


class WithResourceDataMixin(Model):
    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)
