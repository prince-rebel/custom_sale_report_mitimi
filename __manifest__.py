# -*- coding: utf-8 -*-
{
    'name': 'Custom Sale Report - MITIMI Style',
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': 'Personnalisation du rapport de devis/commande style MITIMI CONSULTING',
    'description': """
        Module de personnalisation du rapport de vente Odoo
        ====================================================

        Ce module personnalise le rapport de devis/commande de vente pour
        reproduire le style du modèle MITIMI CONSULTING.

        Fonctionnalités:
        - Header personnalisé avec logo et slogan
        - Mise en page professionnelle
        - Informations client et conditions de vente
        - Section TVA et totaux conformes au modèle
    """,
    'author': 'Custom Development',
    'website': 'https://www.mitimi-consulting.com',
    'depends': ['sale', 'account'],
    'data': [
        # 'views/report_saleorder.xml',
        # 'report/sale_report_templates.xml',
        'data/sale_sequence.xml',
        'views/res_company_views.xml',
        'views/sale_order_views.xml',
        'report/mitimi_sale_report.xml',
        'report/mitimi_fiche_affaire.xml',
        'report/mitimi_invoice_report.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'custom_sale_report_mitimi/static/src/scss/report_style.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
