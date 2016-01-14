# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from .move import *
from .shipment import *


def register():
    Pool.register(
        Move,
        ShipmentOut,
        ShipmentOutAssignWizardStart,
        module='stock_shipment_out_autoassign', type_='model')
    Pool.register(
        ShipmentOutAssignWizard,
        module='stock_shipment_out_autoassign', type_='wizard')
