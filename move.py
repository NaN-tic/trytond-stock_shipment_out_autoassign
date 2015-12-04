# This file is part stock_lot_out_autoassign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from collections import OrderedDict
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

from sql import Cast, Literal
from sql.aggregate import Sum
from sql.functions import Substring, Position
from sql.operators import Like


__all__ = ['Move']
__metaclass__ = PoolMeta


class Move:
    __name__ = 'stock.move'

    @classmethod
    def do(cls, moves):
        ShipmentIn = Pool().get('stock.shipment.in')
        super(Move, cls).do(moves)
        in_moves = [m.id for m in moves if isinstance(m.shipment, ShipmentIn)]
        if in_moves:
            cls.autoassign_out_moves(in_moves)

    @classmethod
    def autoassign_out_moves(cls, move_ids):
        '''
        This method tries to auto assign output moves when input shipments pass
        to done state.
        :param move_ids: List of ids moves of stock.shipment.in
        '''
        pool = Pool()
        Location = pool.get('stock.location')
        ShipmentIn = pool.get('stock.shipment.in')
        ShipmentOut = Pool().get('stock.shipment.out')
        Date_ = Pool().get('ir.date')
        Product = Pool().get('product.product')
        cursor = Transaction().cursor

        move = cls.__table__()
        shipment_in = ShipmentIn.__table__()
        shipment_out = ShipmentOut.__table__()
        move_location = Location.__table__()
        warehouse_location = Location.__table__()
        storage_location = Location.__table__()
        today = Date_.today()

        # Get quantities of new products
        query = (move
            .join(shipment_in, 'LEFT',
                condition=(
                    (Cast(Substring(move.shipment, Position(',', move.shipment)
                        + Literal(1)), 'INTEGER') == shipment_in.id)
                    &
                    (Like(move.shipment, 'stock.shipment.in,%'))
                ))
            .join(warehouse_location, 'LEFT',
                condition=(shipment_in.warehouse == warehouse_location.id))
            .join(storage_location, 'LEFT', condition=(
                    warehouse_location.storage_location == storage_location.id
                    ))
            .join(move_location, 'LEFT',
                condition=(move.to_location == move_location.id))
            .select(
                # Gets root storage location no matter where product is stored
                storage_location.id,
                move.product,
                Sum(move.quantity),
                # to location of move could be child of storage location of
                # shipment warehouse
                where=(
                    (move.id.in_(move_ids))
                    &
                    (move_location.right <= storage_location.right)
                    &
                    (move_location.left >= storage_location.left)
                    ),
                group_by=(storage_location.id, move.product),
                ))
        cursor.execute(*query)
        warehouse_inputs = {(wi[0], wi[1]): wi[2] for wi in cursor.fetchall()}
        if not warehouse_inputs:
            return
        storage_location_ids = [wi[0] for wi in warehouse_inputs]
        product_ids = [wi[1] for wi in warehouse_inputs]

        with Transaction().set_context(forecast=False,
                stock_date_start=today,
                stock_date_end=today):
            # Gets product by location quantities included output shipments in
            # assigned state
            pbl = Product.products_by_location(storage_location_ids,
                product_ids=product_ids, with_childs=True)

        # Get quantities of assigned output moves in order to substract them of
        # product by location quantities
        query = (move
            .join(shipment_out, 'LEFT',
                condition=(
                    (Cast(Substring(move.shipment,
                                Position(',', move.shipment) + Literal(1)),
                            'INTEGER') == shipment_out.id)
                    &
                    (Like(move.shipment, 'stock.shipment.out,%'))
                ))
            .join(warehouse_location, 'LEFT',
                condition=shipment_out.warehouse == warehouse_location.id
                )
            .join(storage_location, 'LEFT', condition=(
                    warehouse_location.storage_location == storage_location.id
                    ))
            .join(move_location, 'LEFT',
                condition=(move.from_location == move_location.id))
            .select(
                storage_location.id,
                move.product,
                Sum(move.quantity),
                # from location of move could be child of storage location of
                # shipment warehouse
                where=(
                    (shipment_out.state == 'assigned')
                    &
                    (move_location.right <= storage_location.right)
                    &
                    (move_location.left >= storage_location.left)
                    &
                    (move.product.in_(product_ids))
                    &
                    (storage_location.id.in_(storage_location_ids))
                    ),
                group_by=(storage_location.id, move.product),
                ))
        cursor.execute(*query)
        assigned_out_moves = {(om[0], om[1]): om[2]
            for om in cursor.fetchall()}

        # Compute quantities of new products plus quantities stored
        for warehouse_input in warehouse_inputs:
            if (warehouse_input in pbl and
                    pbl[warehouse_input] > warehouse_inputs[warehouse_input]):
                warehouse_inputs[warehouse_input] = pbl[warehouse_input]
                if warehouse_input in assigned_out_moves:
                    warehouse_inputs[warehouse_input] -= (
                        assigned_out_moves[warehouse_input])

        # Get output moves in draft states ordered by shipment planned date
        query = (move
            .join(shipment_out, 'LEFT',
                condition=(
                    (Cast(Substring(move.shipment,
                                Position(',', move.shipment) + Literal(1)),
                            'INTEGER') == shipment_out.id)
                    &
                    (Like(move.shipment, 'stock.shipment.out,%'))
                ))
            .join(warehouse_location, 'LEFT',
                condition=shipment_out.warehouse == warehouse_location.id
                )
            .join(storage_location, 'LEFT', condition=(
                    warehouse_location.storage_location == storage_location.id
                    ))
            .join(move_location, 'LEFT', condition=(
                    (move.from_location == move_location.id)
                    ))
            .select(
                move.id,
                storage_location.id,
                move.product,
                move.quantity,
                # from location of move could be child of storage location of
                # shipment warehouse
                where=(
                    (move.state == 'draft')
                    &
                    (move_location.right <= storage_location.right)
                    &
                    (move_location.left >= storage_location.left)
                    &
                    (move.product.in_(product_ids))
                    &
                    (storage_location.id.in_(storage_location_ids))
                    ),
                order_by=shipment_out.planned_date.asc,
                ))
        cursor.execute(*query)
        moves = OrderedDict()
        for move in cursor.fetchall():
            if move[0] in moves:
                moves[move[0]].update({(move[1], move[2]): move[3]})
            else:
                moves[move[0]] = {(move[1], move[2]): move[3]}

        # Checks if there is enough quantity to serve the move
        to_assign = []
        for move in moves:
            for out_product in moves[move]:
                if (out_product in warehouse_inputs and
                        moves[move][out_product] <=
                        warehouse_inputs[out_product]):
                    to_assign.append(move)
                    warehouse_inputs[out_product] -= moves[move][out_product]

        if to_assign:
            # As there could be shipments with more than one move, it must try
            # assign shipments one by one because of, if one fails, continue
            # trying to assign the others
            for move in cls.browse(to_assign):
                ShipmentOut.assign_try([move.shipment])
