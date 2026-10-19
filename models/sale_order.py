# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ── Taux de change (nommés USD, EURO, FCFA dans l'Excel) ──────────────────
    mitimi_rate_usd  = fields.Float('Taux USD → FCFA',  default=600.0)
    mitimi_rate_euro = fields.Float('Taux EURO → FCFA', default=656.0)

    # ── Informations du devis ─────────────────────────────────────────────────
    mitimi_objet          = fields.Char("Objet du devis")
    mitimi_validity_label = fields.Char('Délai de validité', default='1 semaine')

    # ── Fiscalité : la TVA provient des taxes des lignes de commande ──────────
    mitimi_remise   = fields.Float('Remise globale (%)', digits=(5, 4), default=0.0,
                                   help='Ex : 0.05 pour 5 % — correspond à E35 dans l\'Excel')

    # ── Termes et conditions ──────────────────────────────────────────────────
    mitimi_delivery_licence   = fields.Char('Délai livraison licences / matériels', default='N/A')
    mitimi_delivery_project   = fields.Char('Délai livraison du projet',            default='5 jours')
    mitimi_payment_conditions = fields.Char('Conditions de vente',                  default='100 % à la commande')
    mitimi_payment_method     = fields.Char('Mode de paiement',                     default='Chèque ou virement bancaire')
    mitimi_warranty           = fields.Char('Garantie et Support',                  default='Un (01) an')

    # ── Fiche Affaire — J40 et L40 ────────────────────────────────────────────
    mitimi_commission = fields.Float('Commissions (FCFA)', default=0.0, digits=(16, 2))
    mitimi_provision  = fields.Float('Provisions (FCFA)',  default=0.0, digits=(16, 2))

    # ── Totaux calculés ───────────────────────────────────────────────────────
    mitimi_total_ht        = fields.Float('Total HT FCFA',        compute='_compute_mitimi_totals', store=True, digits=(16, 2))
    mitimi_remise_amount   = fields.Float('Montant Remise',       compute='_compute_mitimi_totals', store=True, digits=(16, 2))
    mitimi_total_ht_remise = fields.Float('Total HT avec Remise', compute='_compute_mitimi_totals', store=True, digits=(16, 2))
    mitimi_tva_amount      = fields.Float('Montant TVA',          compute='_compute_mitimi_totals', store=True, digits=(16, 2))
    mitimi_total_ttc       = fields.Float('Total TTC FCFA',       compute='_compute_mitimi_totals', store=True, digits=(16, 2))

    # ── Résultats Fiche Affaire ───────────────────────────────────────────────
    mitimi_total_cost  = fields.Float('Total Prix de Revient', compute='_compute_mitimi_totals', store=True, digits=(16, 2))
    mitimi_marge_brute = fields.Float('Marge Brute (FCFA)',    compute='_compute_mitimi_totals', store=True, digits=(16, 2))
    mitimi_taux_marge  = fields.Float('Taux de Marge (%)',     compute='_compute_mitimi_totals', store=True, digits=(5, 4))

    @api.depends(
        'order_line.price_subtotal', 'order_line.mitimi_cost_total',
        'amount_tax', 'mitimi_remise',
        'mitimi_commission', 'mitimi_provision',
    )
    def _compute_mitimi_totals(self):
        for order in self:
            # F34 = somme des F (price_subtotal) de chaque ligne
            total_ht   = sum(l.price_subtotal for l in order.order_line)
            # F35 = F34 * E35
            remise_amt = total_ht * order.mitimi_remise
            # F36 = F34 - F35
            ht_remise  = total_ht - remise_amt
            # F37 : TVA réelle des lignes (taxes Odoo), ramenée au HT après remise
            tva_amt    = order.amount_tax * (1.0 - order.mitimi_remise)

            order.mitimi_total_ht        = total_ht
            order.mitimi_remise_amount   = remise_amt
            order.mitimi_total_ht_remise = ht_remise
            order.mitimi_tva_amount      = tva_amt
            # F38 = F36 + F37
            order.mitimi_total_ttc       = ht_remise + tva_amt

            # O40 = SUM(Q26:Q32) + J40 + L40
            total_cost = (
                sum(l.mitimi_cost_total for l in order.order_line)
                + order.mitimi_commission
                + order.mitimi_provision
            )
            order.mitimi_total_cost  = total_cost
            # Q40 = F36 - O40
            marge = ht_remise - total_cost
            order.mitimi_marge_brute = marge
            # S40 = (F36 - O40) / F36
            order.mitimi_taux_marge  = marge / ht_remise if ht_remise else 0.0

    def mitimi_tva_label(self):
        """Libellé du taux de TVA tiré des taxes des lignes (ex. '18 %').
        Retourne '' si aucune taxe, ou si les taux sont multiples."""
        self.ensure_one()
        rates = {
            tax.amount
            for tax in self.order_line.mapped('tax_ids')
            if tax.amount_type == 'percent'
        }
        if len(rates) == 1:
            rate = rates.pop()
            return ('%g' % rate) + '\u00a0%'
        return ''

    def mitimi_lines_by_category(self):
        """Retourne les lignes groupées par catégorie pour les rapports PDF."""
        labels = {
            'LICENCES': 'Licences', 'MATERIELS': 'Matériels',
            'LOGICIELS': 'Logiciels', 'SUPPORT': 'Support',
            'SERVICES': 'Services',   'DEVISES': 'Devises', '': 'Autres',
        }
        result = {}
        for line in self.order_line:
            cat = line.mitimi_category or ''
            if cat not in result:
                result[cat] = {'label': labels.get(cat, cat), 'lines': [], 'subtotal': 0.0}
            result[cat]['lines'].append(line)
            result[cat]['subtotal'] += line.price_subtotal
        return result
