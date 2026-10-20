# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Texte proposé une seule fois à l'installation (modifiable ensuite dans la fiche société).
# La ligne {comptes} est remplacée par les comptes bancaires saisis dans Odoo
# (Contacts > société > Coordonnées bancaires).
MITIMI_FOOTER_DEFAULT = (
    "MITIMI CONSULTING au capital de 1 000 000 FCFA - COCODY II PLATEAUX 7E TRANCHE "
    "PHARMACIE MAGNIFICAT, Lot 2977, Ilot 247\n"
    "Abidjan-Côte d'Ivoire 11 BP 1556 ABIDJAN 11 \u2013 Registre de commerce : "
    "CI-ABJ-03-2024-B12-07084 - CC 2403478 Z\n"
    "{comptes}\n"
    "Email : contact@mitimi-consulting.com, Site : www.mitimi-consulting.com"
)
PREFILL_PARAM = 'custom_sale_report_mitimi.footer_prefilled'


class ResCompany(models.Model):
    _inherit = 'res.company'

    mitimi_footer_text = fields.Text(
        string='Mentions légales (pied de page des devis)',
        help="Texte centré en bas du devis, une ligne par retour à la ligne. "
             "La ligne {comptes} est remplacée par les comptes bancaires de la société. "
             "Laissez vide pour une composition automatique à partir de la fiche société.",
    )

    @api.model
    def _mitimi_prefill_defaults(self):
        """Pré-remplit les mentions légales une seule fois (ne réécrit jamais une modification)."""
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param(PREFILL_PARAM):
            return
        for company in self.sudo().search([('name', 'ilike', 'MITIMI')]):
            if not company.mitimi_footer_text:
                company.mitimi_footer_text = MITIMI_FOOTER_DEFAULT
        icp.set_param(PREFILL_PARAM, '1')

    def _mitimi_bank_line(self):
        """'N° Compte : BANQUE (numéro) - BANQUE (numéro)' d'après les comptes de la société."""
        self.ensure_one()
        banks = []
        for b in self.partner_id.bank_ids:
            if not b.acc_number:
                continue
            name = b.bank_id.name
            banks.append('%s (%s)' % (name, b.acc_number) if name else b.acc_number)
        return ('N° Compte : ' + ' - '.join(banks)) if banks else ''

    def mitimi_footer_lines(self):
        """Lignes du pied de page des devis : texte saisi, sinon composition auto."""
        self.ensure_one()
        if self.mitimi_footer_text:
            lines = []
            for raw in self.mitimi_footer_text.splitlines():
                line = raw.strip()
                if '{comptes}' in line:
                    line = line.replace('{comptes}', self._mitimi_bank_line()).strip()
                if line:
                    lines.append(line)
            return lines
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
        # Ligne 3 : comptes bancaires
        bank_line = self._mitimi_bank_line()
        if bank_line:
            lines.append(bank_line)
        # Ligne 4 : e-mail et site
        contact = []
        if self.email:
            contact.append('Email : %s' % self.email)
        if self.website:
            contact.append('Site : %s' % self.website)
        if contact:
            lines.append(', '.join(contact))
        return lines
