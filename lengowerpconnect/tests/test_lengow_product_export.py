# -*- coding: utf-8 -*-
# Copyright 2016 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import csv
from cStringIO import StringIO
from base64 import b64decode

from openerp.addons.connector.session import ConnectorSession

from . import common
from ..models.product import ProductExporter
from ..models.connector import get_environment


class TestLengowProductBinding(common.SetUpLengowBase):

    def setUp(self):
        super(TestLengowProductBinding, self).setUp()
        self.product = self.env.ref('product.product_product_36')
        self.product.write({'ean13': '4004764782703',
                            'description_sale': 'A smart description',
                            'list_price': 40.59,
                            'product_url': 'url_product',
                            'image_url': 'url_image'})
        bind_wizard = self.bind_wizard_model.create(
            {'catalogue_id': self.catalogue.id,
             'product_ids': [(6, 0, [self.product.id])]})

        bind_wizard.bind_products()

    def test_export_products(self):
        """
            Export a product and check result file
        """
        env = get_environment(ConnectorSession.from_env(self.env),
                              'lengow.product.product', self.backend.id)
        products_exporter = env.get_connector_unit(ProductExporter)

        products_exporter.run(self.catalogue,
                              self.catalogue.binded_product_ids)

        csv_file = self.env['ir.attachment'].search(
            [('name', '=', self.catalogue.product_filename)])

        datas = b64decode(csv_file.datas)
        reader = csv.DictReader(StringIO(datas),
                                delimiter=';')

        linesByID = {}
        for line in reader:
            linesByID[line['ID_PRODUCT']] = line

        self.assertEqual(1, len(linesByID))

        lineDict = linesByID['DVD']
        expectedDict = {
            'BRAND': '',
            'CATEGORY': 'All / Saleable / Accessories',
            'DESCRIPTION': 'A smart description',
            'EAN': '4004764782703',
            'ID_PRODUCT': 'DVD',
            'NAME_PRODUCT': 'Blank DVD-RW',
            'PRICE_PRODUCT': '40.59',
            'QUANTITY': '-3.0',
            'SUPPLIER_CODE': '',
            'URL_IMAGE': 'url_image',
            'URL_PRODUCT': 'url_product'}
        self.assertDictEqual(lineDict, expectedDict)

    def test_export_products_lang(self):
        """
            Export a product and check result file
            - Set french as export language
        """
        wiz_lang = self.env['base.language.install'].create(
            {'lang': 'fr_FR'
             })
        wiz_lang.lang_install()

        self.product.with_context(lang="fr_FR").write(
            {'name': 'DVD-RW vierge',
             'description_sale': 'Description de vente'})

        fr = self.env['res.lang'].search([('code', '=', 'fr_FR')])
        self.catalogue.write({'default_lang_id': fr.id})

        env = get_environment(ConnectorSession.from_env(self.env),
                              'lengow.product.product', self.backend.id)
        products_exporter = env.get_connector_unit(ProductExporter)

        products_exporter.run(self.catalogue,
                              self.catalogue.binded_product_ids)

        csv_file = self.env['ir.attachment'].search(
            [('name', '=', self.catalogue.product_filename)])

        datas = b64decode(csv_file.datas)
        reader = csv.DictReader(StringIO(datas),
                                delimiter=';')

        linesByID = {}
        for line in reader:
            linesByID[line['ID_PRODUCT']] = line

        self.assertEqual(1, len(linesByID))

        lineDict = linesByID['DVD']
        expectedDict = {
            'BRAND': '',
            'CATEGORY': 'Tous / En vente / Accessoires',
            'DESCRIPTION': 'Description de vente',
            'EAN': '4004764782703',
            'ID_PRODUCT': 'DVD',
            'NAME_PRODUCT': 'DVD-RW vierge',
            'PRICE_PRODUCT': '40.59',
            'QUANTITY': '-3.0',
            'SUPPLIER_CODE': '',
            'URL_IMAGE': 'url_image',
            'URL_PRODUCT': 'url_product'}
        self.assertDictEqual(lineDict, expectedDict)

    def test_export_products_pricelist(self):
        """
            Export a product and check result file
            - set a pricelist of 10% discount on product
        """
        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
            'type': 'sale'
        })
        version = self.env['product.pricelist.version'].create({
            'name': 'Test Version',
            'pricelist_id': pricelist.id,
        })
        self.env['product.pricelist.item'].create({
            'name': 'Test Item',
            'price_version_id': version.id,
            'base': 1,
            'product_id': self.product.id,
            'price_discount': -0.1,
        })
        self.catalogue.write({'product_pricelist_id': pricelist.id})
        env = get_environment(ConnectorSession.from_env(self.env),
                              'lengow.product.product', self.backend.id)
        products_exporter = env.get_connector_unit(ProductExporter)

        products_exporter.run(self.catalogue,
                              self.catalogue.binded_product_ids)

        csv_file = self.env['ir.attachment'].search(
            [('name', '=', self.catalogue.product_filename)])

        datas = b64decode(csv_file.datas)
        reader = csv.DictReader(StringIO(datas),
                                delimiter=';')

        linesByID = {}
        for line in reader:
            linesByID[line['ID_PRODUCT']] = line

        self.assertEqual(1, len(linesByID))

        lineDict = linesByID['DVD']
        expectedDict = {
            'BRAND': '',
            'CATEGORY': 'All / Saleable / Accessories',
            'DESCRIPTION': 'A smart description',
            'EAN': '4004764782703',
            'ID_PRODUCT': 'DVD',
            'NAME_PRODUCT': 'Blank DVD-RW',
            'PRICE_PRODUCT': '36.53',
            'QUANTITY': '-3.0',
            'SUPPLIER_CODE': '',
            'URL_IMAGE': 'url_image',
            'URL_PRODUCT': 'url_product'}
        self.assertDictEqual(lineDict, expectedDict)
