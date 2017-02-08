# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Configuration']


class Configuration:
    __name__ = 'stock.configuration'
    __metaclass__ = PoolMeta
    try_wait2assign = fields.Boolean('Try assign',
        help="Try assign shipments in wait state")
    slice_try_assign = fields.Integer('Cron slice Try assign',
        help=("Number of blocs of shipments to try assign before do the "
            "commit. If 0 or null it will be all."))

    @staticmethod
    def default_try_wait2assign():
        return True

    @staticmethod
    def default_slice_try_assign():
        return 10
