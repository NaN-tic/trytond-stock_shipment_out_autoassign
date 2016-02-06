# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, Button, StateAction
import datetime
import logging

__all__ = ['ShipmentOut', 'ShipmentOutAssignWizardStart',
    'ShipmentOutAssignWizard']
__metaclass__ = PoolMeta
logger = logging.getLogger(__name__)


class ShipmentOut:
    __name__ = 'stock.shipment.out'

    @classmethod
    def wait(cls, shipments):
        forward_shipments = [s for s in shipments if s.state == 'draft']
        super(ShipmentOut, cls).wait(shipments)
        cls.assign_try(forward_shipments)

    @classmethod
    def assign_try_scheduler(cls, args=None):
        '''
        This method is intended to be called from ir.cron
        '''
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        Cron = pool.get('ir.cron')
        Location = pool.get('stock.location')
        Move = pool.get('stock.move')

        cron = Cron(ModelData.get_id('stock_shipment_out_autoassign',
                'cron_shipment_out_assign_try_scheduler'))
        from_date = cron.next_call - Cron.get_delta(cron)
        locations = Location.search([
                ('code', '!=', 'OUT'),
                ('type', '=', 'storage'),
                ])
        customer_locations = Location.search([('type', '=', 'customer')])
        moves = Move.search([
                ('write_date', '>=', from_date),
                ('to_location', 'in', locations),
                ('state', '=', 'done'),
                ])
        products = {m.product for m in moves}
        moves = Move.search([
                ('product', 'in', products),
                ('to_location', 'in', customer_locations),
                ('state', '=', 'draft'),
                ])
        shipments = [m.shipment
            for m in moves
            if m.shipment
            and isinstance(m.shipment, cls)
            and m.shipment.state == 'waiting'
            ]
        warehouses = []
        if args:
            warehouses = Location.search([
                    ('name', 'in', args),
                    ])
        for s in shipments:
            if s.warehouse in warehouses:
                cls.assign_try([s])
                Transaction().cursor.commit()


class ShipmentOutAssignWizardStart(ModelView):
    'Assign Out Shipment Wizard Start'
    __name__ = 'stock.shipment.out.assign.wizard.start'
    warehouse = fields.Many2One('stock.location', 'Warehouse',
        domain=[('type', '=', 'warehouse')], required=True)
    from_datetime = fields.DateTime('From Date & Time', required=True)


class ShipmentOutAssignWizard(Wizard):
    'Assign Out Shipment Wizard'
    __name__ = 'stock.shipment.out.assign.wizard'
    start = StateView('stock.shipment.out.assign.wizard.start',
        'stock_shipment_out_autoassign.'
        'stock_shipment_out_assign_wizard_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Next', 'assign', 'tryton-go-next', default=True),
            ])
    assign = StateAction('stock.act_shipment_out_form')

    def do_assign(self, action):
        ShipmentOut = Pool().get('stock.shipment.out')

        shipments_assigned = []
        shipments = ShipmentOut.search([
                ('state', 'in', ['waiting']),
                ('warehouse', '=', self.start.warehouse),
                ('create_date', '>', self.start.from_datetime),
                ], order=[('create_date', 'ASC')])

        for s in shipments:
            if ShipmentOut.assign_try([s]):
                shipments_assigned.append(s)
            Transaction().cursor.commit()

        action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [s.id for s in shipments_assigned]),
                ])
        return action, {}

    def transition_assign(self):
        return 'end'
