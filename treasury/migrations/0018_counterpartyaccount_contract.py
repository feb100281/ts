"""Счёт контрагента → договор: операции по счёту сразу на договор (эквайринг, инкассация)."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0022_conditions_vat_mode_by_payment"),
        ("treasury", "0017_cfdata_contract_date_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="counterpartyaccount",
            name="contract",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="bound_accounts", to="contracts.contracts",
                verbose_name="Договор для операций по счёту",
                help_text="Операции по этому счёту — сразу на этот договор (например, эквайринг банка). "
                          "Такой договор по RegEx не подбирается."),
        ),
    ]
