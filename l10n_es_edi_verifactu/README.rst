.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :alt: License: AGPL-3

Spain - Verifactu
=================

When posting an invoice, a Verifactu XML is created, sending of the XML to the Verifactu systems is only implemented to the developing environment, there is no production environment yet.

Supported and tested validation schemas: 1.0 28/10/2024 (Versión oficial a raíz de la publicación de la Orden Ministerial HAC-1177-2024)

Supported and tested invoices:

* Standard sale invoice to a Spanish customer
* Taxes: Exento, Sujeto, No Sujeto, No Sujeto por reglas de Localization
* Refund invoices
* Sale invoices to EU customers: merchandises
* Exportation: sale invoices to non EU customers, merchandises

Not supported invoices, in these cases, when invoice confirmation a validation error is raised and the invoice
is not validated:

* Simplified invoices
* Taxes: Sujeto ISP, Retencion
* Repercuted equivalence surcharge (``recargo`` tax on sales lines) is only
  supported when the company is in general regime (**01**); a company in
  equivalence surcharge regime (**18**) or simplified VAT regime (**20**) must
  sell with VAT only. See POS module for simplified tickets. Repercuting
  recargo to an RE customer (supplier in general regime **01** with
  ``fp_recargo``) is supported on full invoices (``rate2``/``amount2``).
* Cancellation of invoices

Dependencies
============

Module: l10n_es_edi_sii

System: to execute verifactu-xmlgen node is required, version Debian Bookworm v18.19.0.

Configuration
=============

l10n_es_edi_verifactu.verifactu_xml_cmd config_parameter indicates which version of command to use to generates Verifactu xml files, default value is addon_dir/lib/verifactu-xmlgen, the command is distributed with the addon it self.

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
