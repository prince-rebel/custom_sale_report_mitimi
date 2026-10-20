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
        # Ligne 1 : société + adresse
        address = ', '.join(x for x in (
            partner.street, partner.street2,
            ' '.join(y for y in (partner.zip, partner.city) if y),
            partner.country_id.name,
        ) if x)
        lines = [' - '.join(x for x in (self.name, address) if x)]
        # Ligne 2 : registre de commerce et compte contribuable
        legal = []
        if self.company_registry:
            legal.append('Registre de commerce : %s' % self.company_registry)
        if self.vat:
            legal.append('CC %s' % self.vat)
        if legal:
            lines.append(' - '.join(legal))
        # Ligne 3 : comptes bancaires de la société (Contacts > société > Coordonnées bancaires)
        banks = []
        for b in partner.bank_ids:
            if not b.acc_number:
                continue
            name = b.bank_id.name
            banks.append('%s (%s)' % (name, b.acc_number) if name else b.acc_number)
        if banks:
            lines.append('N° Compte : ' + ' - '.join(banks))
        # Ligne 4 : e-mail et site
        contact = []
        if self.email:
            contact.append('Email : %s' % self.email)
        if self.website:
            contact.append('Site : %s' % self.website)
        if contact:
            lines.append(', '.join(contact))
        return lines
