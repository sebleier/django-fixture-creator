#!/usr/bin/env python
"""
    A simple utility script to make a default set of fixtures given some
    model names.  It can build fixtures with the minimal set of required
    fields and related models or can include every field and related
    model.  It will use default field values when they exist and will
    fallback to the specified defaults for the django field types.

    This is by no means a perfect solution, but will yield a decent
    set of fixtures to start working with for creating tests.
"""
import datetime, time
from decimal import Decimal
from optparse import OptionParser
from django.db import models
from django.conf import settings
from django.db.models.loading import get_model
from django.db.models import ForeignKey, ManyToManyField
from django.db.models.fields import NOT_PROVIDED, Field
from django.db.models.fields.related import ManyToManyRel, ManyToOneRel
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import simplejson



class FixtureMaker(object):
    """
        A simple utility to make fixtures using models with either all their
        fields or the required subset of those fields.  TODO: IDs can also be used
        create fixtures from the database.

        Example Usage:
            ./make_fixture.py (-a)? (-f output.json)? <model_name> (<id>)?
    """
    field_type_defaults = {
        'AutoField': 1,
        'BooleanField': True,
        'CharField': "Default CharField",
        'CommaSeparatedIntegerField': "1,2,3,4,5",
        'DateField': datetime.date.today().strftime("%Y-%m-%d"),
        'DateTimeField': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'DecimalField': Decimal('1.0'),
        'EmailField': "person@example.com",
        'FileField': None,
        'FilePathField': "/path/to/file",
        'FloatField': 1.0,
        'IntegerField': 1,
        'IPAddressField': "127.0.0.1",
        'NullBooleanField': None,
        'PositiveIntegerField': 1,
        'PositiveSmallIntegerField': 1,
        'SlugField': "test-slug",
        'SmallIntegerField': 1,
        'TextField': "lorem ipsum",
        'TimeField': datetime.time().strftime("%H:%M:%S"),
        'URLField': "http://www.example.com",
        'XMLField': "<xml><head></head><body></body></xml>",
    }

    def __init__(self, use_all_fields=False, format="json"):
        self.use_all_fields = use_all_fields
        self._fixtures = []

    @property
    def fixtures(self):
        return simplejson.dumps(self._fixtures, indent=4, cls=DjangoJSONEncoder)

    def get_default_pk(self, model):
        """
            Go through the model instance and find the field that is
            the primary key.
        """
        for field in model._meta.fields:
            if field.primary_key:
                return self.get_default_value(field)
        return None

    def get_models(self, model_names):
        """
            Given a model name or a list of model names, return a tuple of
            the app label and a model instance.
        """
        models = []
        if isinstance(model_names, str):
            model_names = [model_names]
        for app_label in settings.INSTALLED_APPS:
            for model_name in model_names:
                model = get_model(app_label.split(".")[-1], model_name)
                if model is not None:
                    models.append(model)
        return models

    def get_default_value(self, field):
        """
            Given a field instance, return the default value based on
            the field type.  If the field is a subclass of a built in
            django field type, it will return the defualt value for
            the django field type.

            If the model was declared with a default value, return that
            value rather than a sensible value specified in
            self.field_type_defaults
        """
        if field.has_default():
            return field.get_default()
        try:
            default = self.field_type_defaults[field.get_internal_type()]
            if hasattr(field, "max_length") and isinstance(default, str):
                return default[:field.max_length]
            else:
                return default
        except KeyError:
            if field.null:
                return None
            else:
                return ''

    def build_fixture(self, model):
        """
            Given an model instance, build fixtures
            with default values and traverse the related model
            relationships to build the required models
        """
        app_label = model._meta.app_label
        instance = {
            "pk": self.get_default_pk(model),
            "model": "%s.%s" % (app_label, model.__name__),
            "fields": {},
        }
        fields = {}
        for field in model._meta.fields + model._meta.many_to_many:
            if field.primary_key or not field.serialize:
                continue
            if field.rel is not None:
                if not self.use_all_fields and field.null and field.blank:
                    continue
                if field.rel.to in self.models:
                    if isinstance(field.rel, ManyToManyRel):
                        fields[field.name] = [1]
                    else:
                        fields[field.name] = 1
                    continue
                self.models.append(field.rel.to)
            elif self.use_all_fields or not field.blank or not field.null:
                default = self.get_default_value(field)
                if default is not None:
                    fields[field.name] = default
        instance['fields'] = fields
        self._fixtures.append(instance)

    def build_fixtures(self, model_names):
        """
            Go though all the model names and build the fixture or the model
            and related models.
        """
        self.models = self.get_models(args)
        for model in self.models:
            self.build_fixture(model)

if __name__=="__main__":
    parser = OptionParser()
    parser.add_option("-a", action="store_true", dest="all", default=False)
    parser.add_option("-f", "--file", dest="filename")
    (options, args) = parser.parse_args()
    maker = FixtureMaker(use_all_fields=options.all)
    if args > 0:
        maker.build_fixtures(args)
        if options.filename is None:
            print maker.fixtures
        else:
            f = open(options.filename, "w")
            f.write(maker.fixtures)
            f.close()

