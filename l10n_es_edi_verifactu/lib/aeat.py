# -*- coding: utf-8 -*-
# Copyright 2024 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

TEST_AEAT_VERIFACTU_SERVICE_URL = (
    "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP"
)

TEST_AEAT_VERIFACTU_QR_URL = "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"

NAMESPACE_TIK_INFO = {
    "tik": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd"
}

NAMESPACE_SUM_INFO = {
    "sum": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"
}

NAMESPACE_SUM1_INFO = {
    "sum1": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd"
}

NAMESPACE_TIK_RESPONSE = {
    "tikR": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd"
}


def aeat_service_url(invoice):
    if invoice.company_id.l10n_es_edi_test_env:
        return TEST_AEAT_VERIFACTU_SERVICE_URL
    else:
        # TODO post to verifactu production systems, not available yet
        raise NotImplementedError()


def aeat_qr_url(invoice):
    if invoice.company_id.l10n_es_edi_test_env:
        return TEST_AEAT_VERIFACTU_QR_URL
    else:
        # TODO post to verifactu production systems, not available yet
        raise NotImplementedError()
