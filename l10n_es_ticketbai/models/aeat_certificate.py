# Copyright 2021 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
import base64
from odoo import models, fields, api
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
except(ImportError, IOError) as err:
    _logger.error(err)


class L10nEsAeatCertificate(models.Model):
    _inherit = 'l10n.es.aeat.certificate'

    tbai_p12 = fields.Binary(compute='_compute_tbai_p12')
    tbai_p12_friendlyname = fields.Char('Alias')
    tbai_p12_expiration_date = fields.Date(
        "Expiration Date", compute="_compute_tbai_cert_expiration_date"
    )
    tbai_certificate_is_expired = fields.Boolean(
        compute="_compute_tbai_certificate_is_expired"
    )

    def _get_expiration_datetime(self):
        self.ensure_one()
        expiration_datetime = (
            self.get_p12().get_certificate().get_notAfter().decode("utf-8")
        )
        return datetime.strptime(expiration_datetime, "%Y%m%d%H%M%S%fZ")

    @api.multi
    def _compute_tbai_cert_expiration_date(self):
        for certificate in self:
            try:
                certificate.tbai_p12_expiration_date = (
                    certificate._get_expiration_datetime().date()
                )
            except crypto.Error:
                certificate.tbai_p12_expiration_date = None

    @api.depends("file")
    def _compute_tbai_certificate_is_expired(self):
        for certificate in self:
            certificate.tbai_certificate_is_expired = (
                certificate.get_p12().get_certificate().has_expired()
            )

    def get_p12(self):
        """
        Because for signing the XML file is needed a PKCS #12 and
        the passphrase is not available in the AEAT certificate,
        create a new one and set the certificate and its private key
        from the stored files.
        :return: A PKCS #12 archive
        """
        self.ensure_one()
        with open(self.public_key, 'rb') as f_crt:
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, f_crt.read())
        p12 = crypto.PKCS12()
        p12.set_certificate(cert)
        with open(self.private_key, 'rb') as f_pem:
            private_key = f_pem.read()
        p12.set_privatekey(crypto.load_privatekey(crypto.FILETYPE_PEM, private_key))
        return p12

    @api.multi
    @api.depends('public_key', 'private_key', 'tbai_p12_friendlyname')
    def _compute_tbai_p12(self):
        for record in self:
            p12 = record.get_p12()
            if record.tbai_p12_friendlyname:  # Set on Certificate Password Wizard
                p12.set_friendlyname(record.tbai_p12_friendlyname.encode('utf-8'))
            record.tbai_p12 = base64.b64encode(p12.export())
