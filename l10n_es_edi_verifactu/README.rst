.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :alt: License: AGPL-3

Spain - Verifactu
=================

When posting a customer invoice, this module builds a Verifactu XML with the
bundled ``verifactu-xmlgen`` command, chains it with the previous invoice and
sends it to the AEAT. Both the test environment and the production environment
are supported. The company setting *Test Environment*
(``l10n_es_edi_test_env``, from ``l10n_es_edi_sii``) selects the endpoint:

* Test: ``https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP``
  and QR ``https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR``
* Production: ``https://www1.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP``
  and QR ``https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR``

Supported and tested validation schemas: 1.0 28/10/2024 (official version
published with Ministerial Order HAC/1177/2024).

Highlighted features:

* Send the invoice XML to the AEAT test or production web service
* Verification QR on the invoice report, with the test or production URL
* Fiscal chain (hash and chain index) with a lock when the invoice is posted
* Cancellation of an already sent invoice
* Refunds of invoices issued outside Odoo (external number and date)
* OSS taxes (VAT regime key **17**)
* Company VAT regimes **01** (general), **18** (equivalence surcharge) and
  **20** (simplified VAT)
* Repercuted equivalence surcharge only when the company is in the general
  regime
* Software identification and responsible declaration file in settings

Supported and tested invoices:

* Standard sale invoice to a Spanish customer (F1)
* Taxes: Exento, Sujeto, No Sujeto, No Sujeto por reglas de localización
* Refund invoices (R1), including refunds that only record the original
  invoice number and date
* Sale invoices to EU customers: merchandises
* Exportation: sale invoices to non EU customers, merchandises
* Invoices in a foreign currency
* OSS taxes (VAT regime key **17**)
* Company VAT regimes **01**, **18** and **20**. A company in regime **18** or
  **20** sells with VAT only
* Repercuted equivalence surcharge (``recargo`` tax) on full invoices when the
  company is in general regime (**01**) and the customer is in the equivalence
  surcharge regime
* Cancellation of invoices sent to the AEAT
* Partner identification other than a Spanish NIF (passport and other ID
  types)
* Fiscal chain (hash and chain index) and QR code on the invoice report

Not supported invoices. In these cases invoice confirmation raises a
validation error and the invoice is not validated:

* Simplified invoices
* Taxes: Sujeto ISP, Retención
* Repercuted equivalence surcharge when the company is in equivalence
  surcharge regime (**18**) or simplified VAT regime (**20**)

Dependencies
============

Module: l10n_es_edi_sii

System: Node.js is required to execute ``verifactu-xmlgen``. Debian Bookworm
(Node 18.19.0) and Debian Trixie are supported.

Configuration
=============

``l10n_es_edi_verifactu.verifactu_xml_cmd`` indicates which command generates
the Verifactu XML files. The default value is
``%(addon_dir)s/lib/verifactu-xmlgen``. The command is distributed with the
addon itself.

Bundled ``verifactu-xmlgen``:

* Published version: 1.0.17 (git tag). ``verifactu-xmlgen --version`` prints
  ``1.0.0``.
* Source: https://github.com/binovo/verifactu-xmlgen/tree/1.0.17
* Embedded artifact: ``lib/verifactu-xmlgen``, build
  ``2026-09-07 08:29:20``
* SHA-256:
  ``93051977172c1194698f7e74d8ef2ae7b9118211bfd04340ef26cd7aed6b6e70``

Credits
=======

Contributors
------------

* Ugaitz Olaizola <uolaizola@binovo.es>

Maintainer
----------

.. image:: /l10n_es_edi_verifactu/static/description/icon.png
   :alt: Binovo IT Human Project SL
   :target: http://www.binovo.es

This module is maintained by Binovo IT Human Project SL.
