=======================
TicketBAI - OSS Support
=======================

.. |badge1| image:: https://img.shields.io/badge/maturity-Alpha-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Alpha
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1| |badge2|

Módulo para hacer compatible el envío de facturas Ticketbai con el OSS

Añade 2 campos nuevos en los impuestos (account.tax):

* Tipo de causa de no sujeción (se añade el tipo IE)
* Tipo de impuesto Ticketbai

A la hora de generar el fichero XML de envío a TicketBai, si estos campos están rellenados,
se tendrán en cuenta dichos campos, sino seguirá el flujo normal como hasta ahora.


Dependencies
============

#. l10n_es_ticketbai


Credits
=======

Authors
~~~~~~~

* Binovo IT Human Project S.L.

Contributors
~~~~~~~~~~~~

* Alicia Rodríguez <arodriguez@binovo.es>

Maintainers
~~~~~~~~~~~

.. image:: /l10n_es_ticketbai_oss/static/src/img/binovo_logo_peque.jpg
   :alt: Binovo IT Human Project SL
   :target: http://www.binovo.es

This module is maintained by Binovo IT Human Project SL.
