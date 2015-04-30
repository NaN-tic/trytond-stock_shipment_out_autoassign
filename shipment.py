# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder
from trytond.wizard import Wizard, StateView, Button, StateAction


__all__ = ['ShipmentOut', 'ShipmentOutAssignWizardStart',
    'ShipmentOutAssignWizard']
__metaclass__ = PoolMeta


class ShipmentOut:
    __name__ = 'stock.shipment.out'

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
        shipments = {m.shipment
            for m in moves
            if m.shipment
            and isinstance(m.shipment, cls)
            and m.shipment.state == 'waiting'
            }
        if shipments and args:
            warehouses = Location.search([
                    ('name', 'in', args),
                    ])
            shipments = {s for s in shipments if s.warehouse in warehouses}
        cls.assign_try(shipments)


class ShipmentOutAssignWizardStart(ModelView):
    'Assign Out Shipment Wizard Start'
    __name__ = 'stock.shipment.out.assign.wizard.start'
    shipments = fields.Many2Many('stock.shipment.out', None, None, 'Shipments',
        domain=[
            ('state', 'in', ['waiting']),
            ],
        states={
            'required': True,
            },
        help='Select output shipments to try to assign them.')
    warehouse = fields.Many2One('stock.location', 'Warehouse')
    from_datetime = fields.DateTime('From Date & Time')

    @staticmethod
    def default_shipments():
        ShipmentOut = Pool().get('stock.shipment.out')
        shipments = ShipmentOut.search([
                ('state', 'in', ['waiting']),
                ])
        return [w.id for w in shipments]


class ShipmentOutAssignWizard(Wizard):
    'Assign Out Shipment Wizard'
    __name__ = 'stock.shipment.out.assign.wizard'
    start = StateView('stock.shipment.out.assign.wizard.start',
        'stock_shipment_out_autoassign.'
        'stock_shipment_out_assign_wizard_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Assign', 'assign', 'tryton-ok', default=True),
            ])
    assign = StateAction('stock.act_shipment_out_form')

    def do_assign(self, action):
        ShipmentOut = Pool().get('stock.shipment.out')
        domain = [('id', 'in', [s.id for s in self.start.shipments])]
        warehouse = self.start.warehouse
        if warehouse:
            domain.append(('warehouse', '=', warehouse.id))
        from_date = self.start.from_datetime
        if from_date:
            domain.append(('create_date', '>', from_date))
        shipments = ShipmentOut.search(domain)
        ShipmentOut.assign_try(shipments)

        action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [s.id for s in shipments]),
                ])
        return action, {}

    def transition_assign(self):
        return 'end'
