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
        shipments_ids = [s.id for s in shipments if s.state == 'draft']
        super(ShipmentOut, cls).wait(shipments)

        if Transaction().context.get('assign_try', True) and shipments_ids:
            with Transaction().set_context(_check_access=False):
                shipments_to_assign = cls.browse(shipments_ids)
                for s in shipments_to_assign:
                    cls.assign_try([s])
                    Transaction().cursor.commit()

    @classmethod
    def assign_try_scheduler(cls, args=None):
        '''
        This method is intended to be called from ir.cron
        args: warehouse ids [ids]
        '''
        pool = Pool()
        Cron = pool.get('ir.cron')
        ModelData = pool.get('ir.model.data')
        ShipmentOut = pool.get('stock.shipment.out')

        cron = Cron(ModelData.get_id('stock_shipment_out_autoassign',
                'cron_shipment_out_assign_try_scheduler'))
        from_date = cron.next_call - Cron.get_delta(cron)

        domain = [
            ('state', '=', 'waiting'),
            ('write_date', '>=', from_date),
            ]
        if args:
            domain.append(
                ('id', 'in', args),
                )
        shipments = ShipmentOut.search(domain)

        logger.info(
            'Try Assign %s shipments' % (len(shipments)))
        for s in shipments:
            ShipmentOut.assign_try([s])
            Transaction().cursor.commit()


class ShipmentOutAssignWizardStart(ModelView):
    'Assign Out Shipment Wizard Start'
    __name__ = 'stock.shipment.out.assign.wizard.start'
    warehouse = fields.Many2One('stock.location', 'Warehouse',
        domain=[('type', '=', 'warehouse')], required=True)
    from_datetime = fields.DateTime('From Date & Time', required=True)

    @classmethod
    def default_warehouse(cls):
        Location = Pool().get('stock.location')
        locations = Location.search(cls.warehouse.domain)
        if len(locations) == 1:
            return locations[0].id

    @classmethod
    def default_from_datetime(cls):
        now = datetime.datetime.now()
        return now


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
