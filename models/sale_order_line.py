# -*- coding: utf-8 -*-
from odoo import api, fields, models

CATEGORY_SELECTION = [
    ('LICENCES', 'Licences'),
    ('MATERIELS', 'Matériels'),
    ('LOGICIELS', 'Logiciels'),
    ('SUPPORT', 'Support'),
    ('SERVICES', 'Services'),
    ('DEVISES', 'Devises'),
]

CURRENCY_SELECTION = [
    ('FCFA', 'F CFA'),
    ('USD', 'US Dollar'),
    ('EURO', 'Euro'),
]


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ── Données saisies (Fiche Affaire) ───────────────────────────────────────
    mitimi_category = fields.Selection(
        CATEGORY_SELECTION, string='Catégorie', default='SERVICES',
    )
    mitimi_supplier = fields.Char(string='Fournisseur')

    mitimi_currency_type = fields.Selection(
        CURRENCY_SELECTION, string='Devise achat', default='FCFA',
    )
    # P.U. Achat Fournisseur  (colonne K)
    mitimi_purchase_price = fields.Float(
        string='P.U. Achat Frs', digits=(16, 2),
        help='Prix unitaire chez le fournisseur, dans la devise choisie',
    )
    # Remise Frs  (colonne L)
    mitimi_supplier_discount = fields.Float(
        string='Remise Frs (%)', digits=(5, 4),
        help='Ex : 0.49 pour 49 %',
    )
    # FAP  (colonne N)
    mitimi_fap_rate = fields.Float(
        string="Frais d'Approche (%)", digits=(5, 4),
        help='Ex : 0.25 pour 25 %',
    )
    # Marge Brute Souhaitée  (colonne R)
    mitimi_margin_target = fields.Float(
        string='Marge Souhaitée (%)', digits=(5, 4),
        help='Ex : 0.35 pour 35 %',
    )

    # ── Champs calculés stockés (Fiche Affaire) ───────────────────────────────
    # P.U. Achat Frs avec Remise  (colonne M)
    mitimi_purchase_price_net = fields.Float(
        string='P.U. Achat Net (FCFA)',
        compute='_compute_mitimi_costs', store=True, digits=(16, 2),
    )
    # Montant FAP  (colonne O)
    mitimi_fap_amount = fields.Float(
        string='Montant FAP (FCFA)',
        compute='_compute_mitimi_costs', store=True, digits=(16, 2),
    )
    # P.U. Revient  (colonne P)
    mitimi_cost_price = fields.Float(
        string='P.U. Revient (FCFA)',
        compute='_compute_mitimi_costs', store=True, digits=(16, 2),
    )
    # P.T. Revient  (colonne Q)
    mitimi_cost_total = fields.Float(
        string='P.T. Revient (FCFA)',
        compute='_compute_mitimi_costs', store=True, digits=(16, 2),
    )
    # Montant Marge Brute  (colonne S)
    mitimi_margin_amount = fields.Float(
        string='Marge Brute (FCFA)',
        compute='_compute_mitimi_margins', store=True, digits=(16, 2),
    )
    # Marge Brute Réelle  (colonne T)
    mitimi_real_margin_rate = fields.Float(
        string='Marge Réelle (%)',
        compute='_compute_mitimi_margins', store=True, digits=(5, 4),
    )

    # ── _compute_mitimi_costs : M, O, P, Q  (recalcul après sauvegarde) ───────
    @api.depends(
        'mitimi_purchase_price', 'mitimi_supplier_discount',
        'mitimi_currency_type', 'mitimi_fap_rate',
        'order_id.mitimi_rate_usd', 'order_id.mitimi_rate_euro',
        'product_uom_qty',
    )
    def _compute_mitimi_costs(self):
        for line in self:
            order = line.order_id
            if line.mitimi_currency_type == 'USD':
                rate = order.mitimi_rate_usd or 600.0
            elif line.mitimi_currency_type == 'EURO':
                rate = order.mitimi_rate_euro or 656.0
            else:
                rate = 1.0

            # M = K*(1-L)*taux
            net  = line.mitimi_purchase_price * (1.0 - line.mitimi_supplier_discount) * rate
            # O = M*N
            fap  = net * line.mitimi_fap_rate
            # P = M+O
            cost = net + fap

            line.mitimi_purchase_price_net = net
            line.mitimi_fap_amount         = fap
            line.mitimi_cost_price         = cost
            # Q = P*D
            line.mitimi_cost_total         = cost * line.product_uom_qty

    # ── _compute_mitimi_margins : S, T  (recalcul après sauvegarde) ──────────
    @api.depends('price_subtotal', 'mitimi_cost_total')
    def _compute_mitimi_margins(self):
        for line in self:
            # S = F-Q
            margin = line.price_subtotal - line.mitimi_cost_total
            line.mitimi_margin_amount    = margin
            # T = S/F
            line.mitimi_real_margin_rate = margin / line.price_subtotal if line.price_subtotal else 0.0

    # ── onchange : tout se met à jour en temps réel dans le popup ─────────────
    @api.onchange(
        'mitimi_purchase_price', 'mitimi_supplier_discount',
        'mitimi_currency_type', 'mitimi_fap_rate', 'mitimi_margin_target',
        'product_uom_qty',
    )
    def _onchange_mitimi_pricing(self):
        """
        Met à jour price_unit ET tous les champs intermédiaires en temps réel.
        Formules Excel :
          M = K*(1-L)*taux
          O = M*N
          P = M+O
          Q = P*D
          E = P/(1-R)
          S = F-Q
          T = S/F
        """
        order = self.order_id
        if self.mitimi_currency_type == 'USD':
            rate = order.mitimi_rate_usd or 600.0
        elif self.mitimi_currency_type == 'EURO':
            rate = order.mitimi_rate_euro or 656.0
        else:
            rate = 1.0

        # M = K*(1-L)*taux
        net  = self.mitimi_purchase_price * (1.0 - self.mitimi_supplier_discount) * rate
        # O = M*N
        fap  = net * self.mitimi_fap_rate
        # P = M+O
        cost = net + fap

        # Mise à jour en temps réel des champs intermédiaires
        self.mitimi_purchase_price_net = net
        self.mitimi_fap_amount         = fap
        self.mitimi_cost_price         = cost
        # Q = P*D
        self.mitimi_cost_total         = cost * self.product_uom_qty

        # E = P/(1-R)
        if self.mitimi_purchase_price and self.mitimi_margin_target and 0.0 < self.mitimi_margin_target < 1.0:
            self.price_unit = cost / (1.0 - self.mitimi_margin_target)

        # S = F-Q  et  T = S/F  en temps réel
        subtotal = self.price_unit * self.product_uom_qty
        self.mitimi_margin_amount    = subtotal - self.mitimi_cost_total
        self.mitimi_real_margin_rate = self.mitimi_margin_amount / subtotal if subtotal else 0.0

    # ── Action popup Fiche Affaire ────────────────────────────────────────────
    def action_mitimi_cost_detail(self):
        """Ouvre le formulaire de saisie des coûts MITIMI en popup."""
        return {
            'name': 'Détails du coût — Fiche Affaire',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(self.env.ref('custom_sale_report_mitimi.view_mitimi_sale_order_line_cost_form').id, 'form')],
            'target': 'new',
        }