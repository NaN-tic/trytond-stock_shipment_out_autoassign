# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Configuration']


class Configuration:
    __name__ = 'stock.configuration'
    __metaclass__ = PoolMeta
    try_wait2assign = fields.Boolean('Try Assign',
        help="Try assign shipments in wait state")
    blocks_try_assign = fields.Integer('Cron Blocks Try Assign',
        help=("Number of shipments to try assign toghether. If 0 or "
            "null it will be all shipments."))
    repeat_blocks_try_assign = fields.Integer('Cron Repeat Blocks Try Assign',
        help=("Number of blocks to try assign before do the commit. If 0 or "
            "null it will be all blocks in 1 iteration."))
    next_id_try_assign = fields.Integer('Cron Try Assign Next ID',
        help="Next ID to use in the try assign.")
    last_id_try_assign = fields.Integer('Cron Try Assign Last ID',
        readonly=True, help="Last ID in the try assign iteration.")

    @staticmethod
    def default_try_wait2assign():
        return True

    @staticmethod
    def default_blocks_cron_try_assign():
        return 500

    @staticmethod
    def default_repeat_blocks_try_assign():
        return 1

    @staticmethod
    def default_next_id_try_assign():
        return 0

    @staticmethod
    def default_last_id_try_assign():
        return 0
