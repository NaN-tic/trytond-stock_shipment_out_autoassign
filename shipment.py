# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from sql import Table
from time import sleep
from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Id, PYSONEncoder
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, Button, StateAction
from trytond.tools import reduce_ids, grouped_slice
import datetime
import logging

__all__ = ['ShipmentOut', 'ShipmentOutAssignWizardStart',
    'ShipmentOutAssignWizard']
logger = logging.getLogger(__name__)


class ShipmentOut:
    __metaclass__ = PoolMeta
    __name__ = 'stock.shipment.out'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()

        cls._buttons.update({
                'try_assign': {
                    'invisible': Eval('state') != 'waiting',
                    'readonly': ~Eval('groups', []).contains(
                        Id('stock', 'group_stock')),
                    },
                })

    @classmethod
    def stock_move_locked(cls):
        transaction = Transaction()
        cursor = transaction.connection.cursor()

        pg_activity = Table('pg_stat_activity')
        pg_locks = Table('pg_locks')
        pg_class = Table('pg_class')

        cursor.execute(*pg_activity
            .join(pg_locks, 'LEFT',
                condition=(pg_activity.pid == pg_locks.pid))
            .join(pg_class, 'LEFT',
                condition=(pg_locks.relation == pg_class.oid))
            .select(
                pg_activity.pid,
                where=(
                    (pg_locks.mode == 'ExclusiveLock')
                    &
                    (pg_class.relname == 'stock_move')
                    ),
                )
            )
        return cursor.fetchall()

    @classmethod
    def get_assignable(cls, shipments):
        pool = Pool()
        Product = pool.get('product.product')
        Date = pool.get('ir.date')
        Location = pool.get('stock.location')

        today = Date.today()
        product_ids = set()
        locations = set()
        for shipment in shipments:
            for move in shipment.inventory_moves:
                product_ids.add(move.product.id)
                locations.add(move.from_location)

        location_ids = [l.id for l in Location.search([
                    ('parent', 'child_of', list(locations))
                    ])]

        with Transaction().set_context(forecast=False, stock_date_end=today):
            pbl = Product.products_by_location(
                    list(location_ids), list(product_ids), with_childs=False)
        assignable_shipments = []

        for shipment in shipments:
            for move in shipment.inventory_moves:
                if ((move.from_location.id, move.product.id) not in pbl
                        or move.quantity >= pbl[
                            (move.from_location.id, move.product.id)]):
                    break
            else:
                for m in shipment.inventory_moves:
                    pbl[(m.from_location.id, m.product.id)] -= m.quantity
                assignable_shipments.append(shipment)
        return assignable_shipments

    @classmethod
    @ModelView.button
    def try_assign(cls, shipments):
        for s in shipments:
            if s.state != 'waiting':
                continue
            cls.assign_try([s])

    @classmethod
    def wait(cls, shipments):
        Configuration = Pool().get('stock.configuration')

        config = Configuration(1)

        shipments_ids = [s.id for s in shipments if s.state == 'draft']
        super(ShipmentOut, cls).wait(shipments)

        if config.try_wait2assign and shipments_ids \
                and Transaction().context.get('assign_try', True):
            with Transaction().set_context(_check_access=False):
                shipments_to_assign = cls.browse(shipments_ids)
                for s in shipments_to_assign:
                    cls.assign_try([s])
                    Transaction().commit()

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
        Configuration = Pool().get('stock.configuration')

        config = Configuration(1)
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

        with Transaction().set_context(dblock=False):
            shipments = ShipmentOut.search(domain)

            logger.info(
                'Scheduler Try Assign. Total: %s' % (len(shipments)))

            while cls.stock_move_locked():
                sleep(0.1)
            slice_try_assign = config.slice_try_assign or len(shipments)
            blocs = 1
            len_ship = len(shipments)
            for sub_shipments in grouped_slice(shipments, slice_try_assign):
                logger.info('Start bloc %s of %s.' % (blocs, len_ship/slice_try_assign))
                ship = ShipmentOut.browse(sub_shipments)
                ShipmentOut.assign_try(ship)
                Transaction().commit()
                logger.info('End bloc %s.' % blocs)
                blocs += 1
            logger.info('End Scheduler Try Assign.')


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
    assign = StateAction('stock_shipment_out_autoassign'
        '.act_shipment_out_autoassign')

    def do_assign(self, action):
        ShipmentOut = Pool().get('stock.shipment.out')

        shipments = ShipmentOut.search([
            ('state', 'in', ['waiting']),
            ('warehouse', '=', self.start.warehouse),
            ('write_date', '>=', self.start.from_datetime),
            ], order=[('create_date', 'ASC')])

        shipments = ShipmentOut.get_assignable(shipments)

        action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [s.id for s in shipments]),
                ])
        return action, {}

    def transition_assign(self):
        return 'end'
