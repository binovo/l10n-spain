/* Copyright 2016 David Gómez Quilón <david.gomez@aselcis.com>
   Copyright 2018-19 Tecnativa - David Vidal
   License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
*/

odoo.define('l10n_es_pos.models', function (require) {
    "use strict";

    var logger = require('point_of_sale.logger');
    var models = require('point_of_sale.models');

    var pos_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (attributes, options) {
            pos_super.initialize.apply(this, arguments);
            this.pushed_simple_invoices = [];
            return this;
        },
        get_simple_inv_next_number: function () {
            return this.config.l10n_es_simplified_invoice_prefix+this.get_padding_simple_inv(this.config.l10n_es_simplified_invoice_number);
        },
        get_padding_simple_inv: function (number) {
            var diff = this.config.l10n_es_simplified_invoice_padding - number.toString().length;
            var result = '';
            if (diff <= 0) {
                result = number;
            } else {
                for (var i = 0; i < diff; i++) {
                    result += '0';
                }
                result += number;
            }
            return result;
        },
        push_simple_invoice: function (order) {
            logger.warn('l10n_es_pos/push_simple_invoice > in');
            if (order) {
                logger.warn('l10n_es_pos/push_simple_invoice > ' + order.data.uid + ' > ' + order.data.simplified_invoice);
            }
            if (this.pushed_simple_invoices.indexOf(order.data.simplified_invoice) === -1) {
                logger.warn('l10n_es_pos/push_simple_invoice > push');
                this.pushed_simple_invoices.push(order.data.simplified_invoice);
                logger.warn('l10n_es_pos/push_simple_invoice > current number: ' + this.config.l10n_es_simplified_invoice_number);
                ++this.config.l10n_es_simplified_invoice_number;
                logger.warn('l10n_es_pos/push_simple_invoice > increment number: ' + this.config.l10n_es_simplified_invoice_number);
            }
        },
        push_order: function(order, opts) {
            logger.warn('l10n_es_pos/push_order > in');
            if (order) {
                logger.warn('l10n_es_pos/push_order > ' + order.uid + ' > ' + order.simplified_invoice);
            }
            if (order && order.simplified_invoice && this.pushed_simple_invoices.indexOf(order.simplified_invoice) === -1) {
                logger.warn('l10n_es_pos/push_order > push');
                this.pushed_simple_invoices.push(order.simplified_invoice);
                logger.warn('l10n_es_pos/push_order > current number: ' + this.config.l10n_es_simplified_invoice_number);
                ++this.config.l10n_es_simplified_invoice_number;
                logger.warn('l10n_es_pos/push_order > increment number: ' + this.config.l10n_es_simplified_invoice_number);
            }
            try {
                return pos_super.push_order.apply(this, arguments);
            } catch (err) {
                logger.error(err.message);
                logger.error(err.stack);
                alert('Ha ocurrido un error al registrar el ticket.');
            }
        },
        _flush_orders: function (orders, options) {
            var self = this;
            // Save pushed orders numbers
            _.each(orders, function (order) {
                if (!order.data.to_invoice) {
                    self.push_simple_invoice(order);
                }
            });
            return pos_super._flush_orders.apply(this, arguments);
        },
    });

    var order_super = models.Order.prototype;
    models.Order = models.Order.extend({
        get_total_with_tax: function () {
            var total = order_super.get_total_with_tax.apply(this, arguments);
            var below_limit = total <=
                this.pos.config.l10n_es_simplified_invoice_limit;
            this.is_simplified_invoice =
                below_limit && this.pos.config.iface_l10n_es_simplified_invoice;
            return total;
        },
        set_simple_inv_number: function () {
            logger.warn('l10n_es_pos/set_simple_inv_number > in');
            logger.warn('l10n_es_pos/set_simple_inv_number > simplified_invoice: ' + this.simplified_invoice);
            this.simplified_invoice = this.pos.get_simple_inv_next_number();
            logger.warn('l10n_es_pos/set_simple_inv_number > GET simplified_invoice: ' + this.simplified_invoice);
            this.name = this.simplified_invoice;
            this.is_simplified_invoice = true;
        },
        get_base_by_tax: function () {
            var base_by_tax = {};
            this.get_orderlines().forEach(function (line) {
                var tax_detail = line.get_tax_details();
                var base_price = line.get_price_without_tax();
                if (tax_detail) {
                    Object.keys(tax_detail).forEach(function (tax) {
                        if (Object.keys(base_by_tax).includes(tax)) {
                            base_by_tax[tax] += base_price;
                        } else {
                            base_by_tax[tax] = base_price;
                        }
                    });
                }
            });
            return base_by_tax;
        },
        init_from_JSON: function (json) {
            order_super.init_from_JSON.apply(this, arguments);
            this.to_invoice = json.to_invoice;
            this.simplified_invoice = json.simplified_invoice;
        },
        export_as_JSON: function () {
            var res = order_super.export_as_JSON.apply(this, arguments);
            res.to_invoice = this.is_to_invoice();
            if (!res.to_invoice) {
                res.simplified_invoice = this.simplified_invoice;
            }
            return res;
        },
    });

    models.load_fields('res.company', ['street', 'city', 'state_id', 'zip']);

});
