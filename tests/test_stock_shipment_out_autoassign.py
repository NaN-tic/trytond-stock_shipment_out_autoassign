# This file is part of the stock_shipment_out_autoassign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class StockShipmentOutAutoassignTestCase(ModuleTestCase):
    'Test Stock Shipment Out Autoassign module'
    module = 'stock_shipment_out_autoassign'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        StockShipmentOutAutoassignTestCase))
    return suite