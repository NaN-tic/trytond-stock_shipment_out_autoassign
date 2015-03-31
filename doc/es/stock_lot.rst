#:after:stock_lot/stock_lot:section:anadir_lote_a_movimiento#

.. inheritref:: stock_lot/stock_lot:section:autoasignacion_lotes

Autoasignación de lotes en albaranes
------------------------------------

En los productos que en el caso que el lote sea requerido, se asignará un lote por
defecto en el momento que el albarán se reserve (del estado "en espera" a "reserva").

Para la asignación automática de lotes:

* El producto debe disponer la opción de lote requerido (en que ubicaciones el
  lote es requerido).
* Debe haber cantidades disponibles de lote en el producto.

En el caso de solicitar más cantidades del producto que cantidades diponibles
en el lote, en el momento de asignar un número de lote, se dividirá las líneas
del albarán con cantidades según números de lotes disponibles.

El orden de los lotes a asignar vendrá definido en la configuración de la logística
que orden desea los primeros lotes para asignar en los movimientos (FIFO). Por defecto
el orden de los lotes es por el campo "Fecha del lote".

Si en el momento que el operario haga el embalage en la ubicación interna hacia la 
ubicación de salida, puede darse que el número de lote asignado ya no se disponga
(debido que otro albarán ya se ha llevado estos números de lote con anterioridad).
En este caso, el operario podrá cambiar el número de lote en los movimientos internos
manualmente con los número de lote que finalmente añade en el paquete para la ubicación
de salida.
