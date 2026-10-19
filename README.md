# custom_sale_report_mitimi

Module Odoo 19 : devis, bon de commande, facture et Fiche Affaire au style MITIMI CONSULTING.

## Fonctionnalités

- Devis / bon de commande PDF (en-tête, parties, projet concerné, tableau des lignes, totaux, termes et conditions, mentions légales).
- Numérotation des devis `MTM-COPF-AANNN` (année sur 2 chiffres + compteur annuel sur 3 chiffres, ex. `MTM-COPF-26001`).
- TVA calculée depuis les taxes des lignes de commande ; remise globale en pourcentage.
- Fiche Affaire : coûts d'achat, frais d'approche, marges par ligne et marge globale (données internes).
- Mentions légales du pied de page paramétrables par société.

## Installation

1. Copier le dossier `custom_sale_report_mitimi` dans un dossier d'addons déclaré dans `addons_path` (`odoo.conf`).
2. Mode développeur > Applications > Mettre à jour la liste des applications.
3. Installer « Custom Sale Report - MITIMI Style » (ou mettre à jour le module s'il est déjà installé).

## Configuration après installation

- Fiche de la société : renseigner « Mentions légales (pied de page des devis) » (une ligne par retour à la ligne) ; à défaut, le pied de page est composé automatiquement.
- Logo et coordonnées de la société : Paramètres > Sociétés.

## Structure

```
custom_sale_report_mitimi/
├── __manifest__.py
├── data/sale_sequence.xml          # numérotation des devis
├── models/                         # sale.order, sale.order.line, res.company
├── report/                         # devis, facture, Fiche Affaire (QWeb)
├── views/                          # formulaires sale.order et société
└── static/src/scss/report_style.scss
```

## Dépendances

`sale`, `account` — Odoo 19.0

## Licence

LGPL-3
