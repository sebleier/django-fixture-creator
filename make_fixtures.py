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
from django.db.models.fields import NOT_PROVIDED
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import simplejson

FIELD_TYPE_DEFAULTS = {
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
    'PositiveIntegerField': 1000000, 
    'PositiveSmallIntegerField': 1, 
    'SlugField': "test-slug", 
    'SmallIntegerField': 16384,
    'TextField': "lorem ipsum", 
    'TimeField': datetime.time().strftime("%H:%M:%S"),
    'URLField': "http://www.example.com", 
    'XMLField': "<xml><head></head><body></body></xml>",
}

class FixtureMaker(object):
    """
        A simple utility to make fixtures using models with either all their
        fields or the required subset of those fields.  TODO: IDs can also be used 
        create fixtures from the database.
        
        Example Usage:
            ./make_fixture.py (-a)? (-f output.json)? <model_name> (<id>)?
    """

    def __init__(self, use_all=False, format="json"):
        self.use_all = use_all
        self._fixtures = []

    @property
    def fixtures(self):
        return simplejson.dumps(self._fixtures, indent=4, cls=DjangoJSONEncoder)

    def get_app_models(self, model_names):
        """
            Given a model name or a list of model names, return a tuple of
            the app label and a model instance.
        """
        app_models = []
        if isinstance(model_names, str):
            model_names = [model_names]
        for app_label in settings.INSTALLED_APPS:
            for model_name in model_names:
                model = get_model(app_label.split(".")[-1], model_name)
                if model is not None:
                    app_models.append((app_label.split(".")[-1], model))
        return app_models

    def get_default_value(self, field):
        """
            Given a field instance, return the default value based on 
            the field type.  If the field is a subclass of a built in
            django field type, it will return the defualt value for
            the django field type.
        """
        try:
            if field.default != NOT_PROVIDED:
                if callable(field.default):
                    value = field.default()
                else:
                    value = field.default
                return value
            value = FIELD_TYPE_DEFAULTS[field.get_internal_type()]
        except KeyError:
            if len(field.__class__.__bases__) > 0:
                value = self.get_default_value(field.__class__.__bases__[0])
            else:
                return None
        except AttributeError:
            return None
        return value
    
    def get_default_pk(self, model):
        """
            Go through the model instance and find the field that is
            the primary key.
        """
        for field in model._meta.fields:
            if field.primary_key:
                return self.get_default_value(field)
        return None

    def build_fixture(self, app_model):
        """
            Given an (app_label, model_instance) tuple, build fixtures
            with default values and traverse the related model
            relationships to build the required models
        """
        (app_label, model) = app_model
        instance = { 
            "pk": self.get_default_pk(model),
            "model": "%s.%s" % (app_label, model.__name__),
            "fields": {},
        }
        fields = {}
        for field in model._meta.fields + model._meta.many_to_many:
            if field.primary_key:
                continue
            if hasattr(field, "rel") and hasattr(field.rel, "to"):
                if field.rel.to in [m[1] for m in self.app_models]:
                    continue
                if self.use_all or not field.blank:
                    app_model = self.get_app_models(field.rel.to.__name__)
                    self.app_models.append(app_model[0])
                    field_name = field.get_attname()
                    if hasattr(field, "m2m_reverse_name"):
                        fields[field_name] = [1]
                    else:
                        fields[field_name[:-3]] = 1
            else:
                if self.use_all or not field.blank:
                    default = self.get_default_value(field)
                    if default is not None:
                        fields[field.get_attname()] = default
        instance['fields'] = fields
        self._fixtures.append(instance)

    def build_fixtures(self, model_names):
        """
            Go though all the model names and build the fixture or the model
            and related models.
        """
        self.app_models = self.get_app_models(args)
        for app_model in self.app_models:
            self.build_fixture(app_model)

if __name__=="__main__":
    parser = OptionParser()
    parser.add_option("-a", action="store_true", dest="all", default=False)
    parser.add_option("-f", "--file", dest="filename")
    (options, args) = parser.parse_args()
    maker = FixtureMaker(use_all=options.all)
    if args > 0:    
        maker.build_fixtures(args)
        if options.filename is None:
            print maker.fixtures
        else:
            f = open(options.filename, "w")
            f.write(maker.fixtures)
            f.close()

