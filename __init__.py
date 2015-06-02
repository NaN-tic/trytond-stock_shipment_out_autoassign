# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from .shipment import *


def register():
    Pool.register(
        ShipmentOut,
        ShipmentOutAssignWizardStart,
        ShipmentOutAssignWizardShipments,
        module='stock_shipment_out_autoassign', type_='model')
    Pool.register(
        ShipmentOutAssignWizard,
        module='stock_shipment_out_autoassign', type_='wizard')
