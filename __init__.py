# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configuration
from . import move
from . import shipment


def register():
    Pool.register(
        configuration.Configuration,
        move.Move,
        shipment.ShipmentOut,
        shipment.ShipmentOutAssignWizardStart,
        module='stock_shipment_out_autoassign', type_='model')
    Pool.register(
        shipment.ShipmentOutAssignWizard,
        module='stock_shipment_out_autoassign', type_='wizard')
