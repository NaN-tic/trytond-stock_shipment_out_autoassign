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
    slice_try_assign = fields.Integer('Cron Slice Try Assign',
        help=("Number of blocs of shipments to try assign before do the "
            "commit. If 0 or null it will be all."))
    delta_cron_try_assign = fields.Integer('Delta Cron Try Assign',
        help=("Number of minutes to substract for the selection of shipment "
            "outs, to do the try assign."))

    @staticmethod
    def default_try_wait2assign():
        return True

    @staticmethod
    def default_slice_try_assign():
        return 10

    @staticmethod
    def default_delta_cron_try_assign():
        return 30
