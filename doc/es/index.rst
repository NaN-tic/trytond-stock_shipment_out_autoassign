===================================================
Stock. Reservar albaranes de salida automáticamente
===================================================

Permite reservar automáticamente albaranes de salida en estado "En espera",
bien ejecutando el asistente (Logística/Albaranes de cliente/Reservar albaranes),
o bien mediante la acción planificada.

Para la ejecución del asistente, el usario debe pertenecer en el grupo
"Stock. Forzar reserva en logística".

Mediante la acción planificada se pueden filtrar los albaranes que se quieren
reservar añadiendo a los argumentos de la misma una lista con una tupla en la
que se señalen los nombres de los almacenes sobre los que se quiere ejecutar la
acción. A modo de ejemplo, el argumento

[('Almacén', 'Almacén 2')]

reservaría los albaranes de los almacenes Almacén y Almacén 2, pero no los del
resto de almacenes.
