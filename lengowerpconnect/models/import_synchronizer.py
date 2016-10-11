# -*- coding: utf-8 -*-
# Copyright 2016 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from openerp.addons.connector.unit.synchronizer import Importer
from openerp.addons.connector.queue.job import job

from .connector import get_environment

_logger = logging.getLogger(__name__)


class LengowImporter(Importer):
    """ Base importer for Magento """

    def __init__(self, connector_env):
        """
        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(LengowImporter, self).__init__(connector_env)
        self.lengow_id = None
        self.lengow_record = None

    def _import_dependency(self, lengow_id, lengow_data, binding_model,
                           importer_class=None):
        """ Import a dependency. """

        if not lengow_id:
            return
        if importer_class is None:
            importer_class = LengowImporter
        binder = self.binder_for(binding_model)
        if binder.to_openerp(lengow_id) is None:
            importer = self.unit_for(importer_class, model=binding_model)
            importer.run(lengow_id, lengow_data)

    def _import_dependencies(self):
        """ Import the dependencies for the record

        Import of dependencies can be done manually or by calling
        :meth:`_import_dependency` for each dependency.
        """
        return

    def _get_binding(self):
        return self.binder.to_openerp(self.lengow_id, browse=True)

    def _map_data(self):
        return self.mapper.map_record(self.lengow_record)

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data):
        """ Create the Odoo record """
        model = self.model.with_context(connector_no_export=True)
        binding = model.create(data)
        _logger.debug('%d created from Lengow %s', binding, self.lengow_id)
        return binding

    def _update_data(self, map_record, **kwargs):
        return map_record.values(**kwargs)

    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from Lengow %s', binding, self.lengow_id)
        return

    def run(self, lengow_id, lengow_data):
        """ Run the synchronization

        :param lengow_id: identifier of the record on Lengow
        :param lengow_id: identifier of the record on Lengow
        """
        self.lengow_id = lengow_id
        self.lengow_record = lengow_data

        binding = self._get_binding()

        self._import_dependencies()

        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record)
            self._update(binding, record)
        else:
            record = self._create_data(map_record)
            binding = self._create(record)

        self.binder.bind(self.lengow_id, binding)


class BatchImporter(Importer):
    """ The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    def run(self, filters=None):
        """ Run the synchronization """
        dict_records = self.backend_adapter.search(filters)
        for record_id, record_data in dict_records.iteritems():
            self._import_record(record_id, record_data)

    def _import_record(self, record_id, record_data):
        """ Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
        raise NotImplementedError


class DirectBatchImporter(BatchImporter):
    """ Import the records directly, without delaying the jobs. """
    _model_name = None

    def _import_record(self, record_id, record_data):
        """ Import the record directly """
        import_record(self.session,
                      self.model._name,
                      self.backend_record.id,
                      record_id,
                      record_data)


class DelayedBatchImporter(BatchImporter):
    """ Delay import of the records """
    _model_name = None

    def _import_record(self, record_id, record_data, **kwargs):
        """ Delay the import of the records"""
        description = 'Import %s %s from Lengow Backend %s' %\
            (self.model._name,
             record_id,
             self.backend_record.name)
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            record_id,
                            record_data,
                            description=description,
                            **kwargs)


@job(default_channel='root.lengow')
def import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of records from Lengow """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(BatchImporter)
    importer.run(filters=filters)


@job(default_channel='root.lengow')
def import_record(session, model_name, backend_id, record_id,
                  record_data):
    """ Import a record from Lengow """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(LengowImporter)
    importer.run(record_id, record_data)
