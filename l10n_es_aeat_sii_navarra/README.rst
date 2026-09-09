.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :alt: License: AGPL-3

SII - Hacienda Foral de Navarra
===============================

Envía las facturas al SII de la Hacienda Foral de Navarra.

Configuración
=============

La realiza un usuario con el permiso **Responsable AEAT**.

#. **Facturación → Configuración → AEAT → Agencia Tributaria**: abrir
   *Hacienda Foral de Navarra* y, en la pestaña **SII**, indicar las URLs
   de facturas emitidas y recibidas. Hay que rellenarlas a mano.
#. **Ajustes → Usuarios y compañías → Compañías**: en la pestaña **AEAT**,
   seleccionar *Hacienda Foral de Navarra*; en la pestaña **SII**, activar
   el SII.

El certificado se configura en **Facturación → Configuración → AEAT**,
igual que en el SII estándar.

Uso
===

Un usuario de facturación valida las facturas. Si la compañía tiene el
SII activo y la agencia de Navarra, el envío va a Navarra. El estado
se consulta en la propia factura.

Detalles técnicos
=================

Sobrescribe ``_connect_params_sii`` solo para *Hacienda Foral de Navarra*:
usa el WSDL de la AEAT (Navarra no publica uno) y como dirección SOAP las
URLs de la agencia de Navarra. En modo test, si no hay URL de pruebas, el
puerto SOAP añade el sufijo ``Pruebas``.

Solo cubre facturas emitidas y recibidas.

Credits
=======

Contributors
------------

* Jesús Sánchez <jsanchez@binovo.es>

Maintainer
----------

.. image:: /l10n_es_aeat_sii_navarra/static/src/img/binovo_logo_peque.jpg
   :alt: Binovo IT Human Project SL
   :target: http://www.binovo.es

This module is maintained by Binovo IT Human Project SL.
