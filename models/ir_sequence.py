# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import api, models

_logger = logging.getLogger(__name__)

QUOTE_START_PARAM = 'custom_sale_report_mitimi.quote_start_21'
QUOTE_START = 21


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def _mitimi_set_quote_start(self):
        """Une seule fois : le prochain devis de l'année en cours porte le numéro 21 (MTM-COPF-26021).
        Ne réécrit jamais un compteur déjà plus avancé, ni une modification faite ensuite dans Odoo."""
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param(QUOTE_START_PARAM):
            return
        seq = self.sudo().search([('code', '=', 'sale.order')], limit=1)
        if not seq:
            return
        try:
            with self.env.cr.savepoint():
                today = date.today()
                rng = seq.date_range_ids.filtered(lambda r: r.date_from <= today <= r.date_to)[:1]
                if rng:
                    if rng.number_next < QUOTE_START:
                        rng.number_next = QUOTE_START
                else:
                    self.env['ir.sequence.date_range'].sudo().create({
                        'sequence_id': seq.id,
                        'date_from': date(today.year, 1, 1),
                        'date_to': date(today.year, 12, 31),
                        'number_next': QUOTE_START,
                    })
            icp.set_param(QUOTE_START_PARAM, '1')
        except Exception:  # ne jamais bloquer la mise à jour du module
            _logger.exception("custom_sale_report_mitimi : numéro de départ des devis non appliqué")
