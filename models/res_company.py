# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    mitimi_footer_text = fields.Text(
        string='Mentions légales (pied de page des devis)',
        help="Texte centré en bas du devis, une ligne par retour à la ligne "
             "(capital, adresse, RCCM, CC, comptes bancaires...). "
             "Laissez vide pour une composition automatique à partir de la fiche société.",
    )

    def mitimi_footer_lines(self):
        """Lignes du pied de page des devis : texte saisi, sinon composition auto."""
        self.ensure_one()
        if self.mitimi_footer_text:
            return [l.strip() for l in self.mitimi_footer_text.splitlines() if l.strip()]
        partner = self.partner_id
        lines = [self.name or '']
        address = ', '.join(p for p in (
            partner.street, partner.street2,
            ' '.join(x for x in (partner.zip, partner.city) if x),
            partner.country_id.name,
        ) if p)
        if address:
            lines.append(address)
        if self.email:
            lines.append('E-mail : %s' % self.email)
        legal = []
        if self.company_registry:
            legal.append(self.company_registry)
        if self.vat:
            legal.append('CC %s' % self.vat)
        if legal:
            lines.append(' '.join(legal))
        banks = [
            '%s : %s' % (b.bank_id.name or 'Banque', b.acc_number)
            for b in partner.bank_ids if b.acc_number
        ]
        if banks:
            lines.append('N° Comptes : ' + ' ; '.join(banks))
        return lines
