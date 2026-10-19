from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, *args, **kwargs):
        result = super()._build_wkhtmltopdf_args(*args, **kwargs)
        # Force UTF-8 pour corriger l'encodage sur Windows
        if '--encoding' not in result:
            result = ['--encoding', 'utf-8'] + result
        return result