# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from sql import Table
from time import sleep
from dateutil.relativedelta import relativedelta
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
    def get_assignable(cls, shipments, date_start=None):
        pool = Pool()
        Date = pool.get('ir.date')
        Product = pool.get('product.product')
        Location = pool.get('stock.location')
        ShipmentOut = pool.get('stock.shipment.out')

        today = Date.today()
        product_ids = set()
        location_ids = set()
        for shipment in shipments:
            for move in shipment.inventory_moves:
                product_ids.add(move.product.id)
                location_ids.add(move.from_location.id)

        pbl = None
        if location_ids:
            context = {
                'locations': list(location_ids),
                'stock_assign': True,
                'forecast': False,
                'stock_date_end': today,
                'check_access': False,
                }
            if date_start:
                context['stock_date_start'] = date_start
            with Transaction().set_context(**context):
                pbl = Product.products_by_location(
                    list(location_ids),
                    list(product_ids),
                    with_childs=True)

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
                    Transaction().cursor.commit()

    @classmethod
    def get_shipment_block(cls, domain, config):
        limit = config.blocks_try_assign
        shipments = cls.search(domain + [
            ('id', '<=', config.last_id_try_assign),
            ('id', '>', config.next_id_try_assign),
            ], order=[('id','asc')], limit=limit)
        limit = limit - len(shipments)
        if shipments and shipments[-1].id < config.last_id_try_assign:
            config.next_id_try_assign = shipments[-1].id
        else:
            config.next_id_try_assign = 0
            all_shipments = cls.search(domain, order=[('id','asc')])
            if all_shipments:
                config.last_id_try_assign = all_shipments[-1].id
        if limit > 0:
            shipments += cls.get_shipment_block(domain, config)
        return shipments

    @classmethod
    def assign_try_scheduler(cls, args=None):
        '''
        This method is intended to be called from ir.cron
        args: warehouse ids [ids]
        '''
        pool = Pool()
        Cron = pool.get('ir.cron')
        ModelData = pool.get('ir.model.data')
        Configuration = Pool().get('stock.configuration')

        config = Configuration(1)
        cron = Cron(ModelData.get_id('stock_shipment_out_autoassign',
                'cron_shipment_out_assign_try_scheduler'))

        domain = [
            ('state', '=', 'waiting'),
            ]
        if args:
            domain.append(
                ('id', 'in', args),
                )

        with Transaction().set_context(dblock=False):
            if (not config.last_id_try_assign or
                    config.last_id_try_assign <= config.next_id_try_assign):
                all_shipments = cls.search(domain, order=[('id','asc')])
                config.last_id_try_assign = (all_shipments[-1].id
                    if all_shipments else 0)
            for repeat_blocks in range(config.repeat_blocks_try_assign):
                shipments = cls.get_shipment_block(domain, config)
                if not shipments:
                    continue
                config.save()
                logger.info('Start block %s of %s.' % (str(repeat_blocks + 1),
                        config.repeat_blocks_try_assign))
                ships = cls.browse(shipments)
                cls.assign_try(ships)
                Transaction().cursor.commit()
                logger.info('End block %s.' % str(repeat_blocks + 1))
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
