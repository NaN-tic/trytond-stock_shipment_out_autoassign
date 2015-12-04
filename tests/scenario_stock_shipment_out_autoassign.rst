=======================================
Stock Shipment Out Auto Assign Scenario
=======================================

Imports::

    >>> from datetime import date, timedelta
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> today = date.today()
    >>> tomorrow = today + timedelta(days=1)

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install stock_shipment_out_autoassign Module::

    >>> Module = Model.get('ir.module.module')
    >>> module, = Module.find([('name', '=', 'stock_shipment_out_autoassign')])
    >>> Module.install([module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='US Dollar', symbol=u'$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[]',
    ...         mon_decimal_point='.')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create customer and supplier::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create 2 product::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> product1 = Product()
    >>> template1 = ProductTemplate()
    >>> template1.name = 'Product 1'
    >>> template1.category = category
    >>> template1.default_uom = unit
    >>> template1.type = 'goods'
    >>> template1.list_price = Decimal('20')
    >>> template1.cost_price = Decimal('8')
    >>> template1.save()
    >>> product1.template = template1
    >>> product1.save()
    >>> product2 = Product()
    >>> template2 = ProductTemplate()
    >>> template2.name = 'Product 2'
    >>> template2.category = category
    >>> template2.default_uom = unit
    >>> template2.type = 'goods'
    >>> template2.list_price = Decimal('20')
    >>> template2.cost_price = Decimal('8')
    >>> template2.save()
    >>> product2.template = template2
    >>> product2.save()

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> warehouse_loc, = Location.find([('code', '=', 'WH')])
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> customer_loc, = Location.find([('code', '=', 'CUS')])
    >>> input_loc, = Location.find([('code', '=', 'IN')])
    >>> output_loc, = Location.find([('code', '=', 'OUT')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])

Create 2 Shipment Out::

    >>> ShipmentOut = Model.get('stock.shipment.out')
    >>> shipment_out1 = ShipmentOut()
    >>> shipment_out1.planned_date = today
    >>> shipment_out1.customer = customer
    >>> shipment_out1.warehouse = warehouse_loc
    >>> shipment_out1.company = company
    >>> shipment_out2 = ShipmentOut()
    >>> shipment_out2.planned_date = tomorrow
    >>> shipment_out2.customer = customer
    >>> shipment_out2.warehouse = warehouse_loc
    >>> shipment_out2.company = company

Add two shipment lines to each Shipment Out::

    >>> StockMove = Model.get('stock.move')
    >>> quantity = 10
    >>> for product in (product1, product2):
    ...     move = StockMove()
    ...     shipment_out1.outgoing_moves.append(move)
    ...     move.product = product
    ...     move.uom =unit
    ...     move.quantity = quantity
    ...     move.from_location = output_loc
    ...     move.to_location = customer_loc
    ...     move.company = company
    ...     move.unit_price = Decimal('1')
    ...     move.currency = company.currency
    ...     move.planned_date = today
    ...     shipment_out1.save()
    ...     move = StockMove()
    ...     shipment_out2.outgoing_moves.append(move)
    ...     move.product = product
    ...     move.uom =unit
    ...     move.quantity = quantity
    ...     move.from_location = output_loc
    ...     move.to_location = customer_loc
    ...     move.company = company
    ...     move.unit_price = Decimal('1')
    ...     move.currency = company.currency
    ...     move.planned_date = tomorrow
    ...     shipment_out2.save()
    ...     quantity -= 5

Set each shipment out state to waiting::

    >>> shipment_out1.click('wait')
    >>> shipment_out2.click('wait')

Create 1 Shipment In::

    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment_in1 = ShipmentIn()
    >>> shipment_in1.planned_date = today
    >>> shipment_in1.supplier = supplier
    >>> shipment_in1.warehouse = warehouse_loc
    >>> shipment_in1.company = company

Add one shipment line to the first Shipment In::

    >>> incoming_move = StockMove()
    >>> shipment_in1.incoming_moves.append(incoming_move)
    >>> incoming_move.product = product1
    >>> incoming_move.uom = unit
    >>> incoming_move.quantity = 10
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = input_loc
    >>> incoming_move.planned_date = today
    >>> incoming_move.effective_date = today
    >>> incoming_move.company = company
    >>> incoming_move.unit_price = Decimal('1')
    >>> incoming_move.currency = company.currency
    >>> shipment_in1.save()

Set first input shipment state to done::

    >>> shipment_in1.click('receive')
    >>> shipment_in1.click('done')

Check the output shipments states::

    >>> shipment_out1.reload()
    >>> shipment_out1.state
    u'waiting'
    >>> shipment_out2.reload()
    >>> shipment_out2.state
    u'waiting'

Create another Shipment In::

    >>> shipment_in2 = ShipmentIn()
    >>> shipment_in2.planned_date = tomorrow
    >>> shipment_in2.supplier = supplier
    >>> shipment_in2.warehouse = warehouse_loc
    >>> shipment_in2.company = company

Add one shipment line to the first Shipment In::

    >>> incoming_move = StockMove()
    >>> shipment_in2.incoming_moves.append(incoming_move)
    >>> incoming_move.product = product2
    >>> incoming_move.uom = unit
    >>> incoming_move.quantity = 10
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = input_loc
    >>> incoming_move.planned_date = today
    >>> incoming_move.effective_date = today
    >>> incoming_move.company = company
    >>> incoming_move.unit_price = Decimal('1')
    >>> incoming_move.currency = company.currency
    >>> shipment_in2.save()

Set second input shipment state to done::

    >>> shipment_in2.click('receive')
    >>> shipment_in2.click('done')

Check the output shipments states::

    >>> shipment_out1.reload()
    >>> shipment_out1.state
    u'assigned'
    >>> shipment_out2.reload()
    >>> shipment_out2.state
    u'waiting'
