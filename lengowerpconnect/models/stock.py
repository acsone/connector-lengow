# -*- coding: utf-8 -*-
# Copyright 2016 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests

from openerp import models, fields

from openerp.addons.connector.event import on_record_create
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.synchronizer import Exporter
from openerp.addons.connector_ecommerce.event import on_picking_out_done

from .adapter import GenericAdapter20
from .backend import lengow20
from .configurator import MarketPlaceConfigurator
from .connector import get_environment
from openerp.exceptions import ValidationError


class LengowStockPicking(models.Model):
    _name = 'lengow.stock.picking'
    _inherit = 'lengow.binding'
    _inherits = {'stock.picking': 'openerp_id'}
    _description = 'Lengow Delivery Order'

    openerp_id = fields.Many2one(comodel_name='stock.picking',
                                 string='Stock Picking',
                                 required=True,
                                 ondelete='cascade')
    lengow_order_id = fields.Many2one(comodel_name='lengow.sale.order',
                                      string='Lengow Sale Order',
                                      ondelete='set null')
    picking_method = fields.Selection(selection=[('complete', 'Complete'),
                                                 ('partial', 'Partial')],
                                      string='Picking Method',
                                      required=True)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    lengow_bind_ids = fields.One2many(
        comodel_name='lengow.stock.picking',
        inverse_name='openerp_id',
        string="Lengow Bindings",
    )


@lengow20
class StockPickingAdapter(GenericAdapter20):
    _model_name = 'lengow.stock.picking'


@lengow20
class LengowPickingExporter(Exporter):
    _model_name = ['lengow.stock.picking']

    def run(self, picking_id):
        picking = self.env['lengow.stock.picking'].browse(picking_id)
        sale = picking.sale_id
        marketplace = sale.lengow_bind_ids.marketplace_id.lengow_id
        config = MarketPlaceConfigurator().get_configurator(
            self.env, marketplace)
        assert config is not None, (
            'No MarketplaceConfigurator found for %s' % marketplace)
        adapter = self.unit_for(StockPickingAdapter)
        api_url = '%s/%s' % (
            self.backend_record.wsdl_location,
            config().get_export_picking_api(sale.lengow_bind_ids[0].id_flux,
                                            sale.lengow_bind_ids[0].lengow_id))
        tracking_params = config().configure_tracking_params(
            picking.carrier_tracking_ref,
            picking.carrier_id.lengow_value or False)

        adapter.process_request(requests.post, api_url,
                                params=tracking_params,
                                ignore_result=True)


@on_picking_out_done
def picking_out_done(session, model_name, record_id, picking_method):
    """
    Create a ``lengow.stock.picking`` record. This record will then
    be exported to Lengow.

    :param picking_method: picking_method, can be 'complete' or 'partial'
    :type picking_method: str
    """
    picking = session.env[model_name].browse(record_id)
    sale = picking.sale_id
    if not sale:
        return
    for lengow_sale in sale.lengow_bind_ids:
        session.env['lengow.stock.picking'].create({
            'backend_id': lengow_sale.backend_id.id,
            'openerp_id': picking.id,
            'lengow_order_id': lengow_sale.id,
            'picking_method': picking_method})


@on_record_create(model_names='lengow.stock.picking')
def delay_export_picking_out(session, model_name, record_id, vals):
    picking = session.env[model_name].browse(record_id)
    job_name = "Export Lengow Picking %s (Order: %s)" % (picking.name,
                                                         picking.sale_id.name)
    export_picking_done.delay(session,
                              model_name,
                              record_id,
                              description=job_name)


@job(default_channel='root.lengow')
def export_picking_done(session, model_name, record_id):
    picking = session.env[model_name].browse(record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(LengowPickingExporter)
    res = picking_exporter.run(record_id)
    return res
