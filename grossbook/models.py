# grossbook/models.py
from django.db import models
from utils.choises import CURRENCY_CHOISE
from corporate.models import Owners,COA,CfItems
from contracts.models import Contracts
from counterparties.models import Counterparty

# Create your models here.

#Модель для ручных проводок

class Manual(models.Model):
    id = models.BigAutoField(primary_key=True)

    pid = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="pid_manual"
    )
    date = models.DateField(verbose_name='Дата')
    owner = models.ForeignKey(Owners, on_delete=models.CASCADE,verbose_name='Компания')
    acc = models.ForeignKey(COA, on_delete=models.CASCADE,verbose_name='Счет')
    contract = models.ForeignKey(Contracts, on_delete=models.CASCADE,verbose_name='Договор')
    dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Дт',default=0.0)
    cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Кт',default=0.0)
    currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOISE, verbose_name="Валюта", default="RUB"
    )
    cfitem = models.ForeignKey(CfItems, on_delete=models.CASCADE,verbose_name='Статья CF',null=True,blank=True)
    temp = models.TextField(verbose_name='Описание операции')
    
    class Meta:        
        verbose_name = "Проводка"
        verbose_name_plural = "Ручные проводки"

    def __str__(self):
        return f"{self.date} на сумму: ({self.currency}{(self.dt - self.cr):,.0f})"
    
    
            
    
# class Settlements(models.Model):
#     id = models.UUIDField(primary_key=True)
#     date_from = models.DateField(verbose_name='Дата')
#     pid = models.ForeignKey(Contracts,on_delete=models.DO_NOTHING,verbose_name='Основной договор',related_name='pid_contract', null=True,blank=True)
#     contract = models.ForeignKey(Contracts,on_delete=models.DO_NOTHING,verbose_name='Договор',related_name='contract', null=True,blank=True)
#     cp = models.ForeignKey(Counterparty,on_delete=models.DO_NOTHING,verbose_name='Контрагент',related_name='cp_name', null=True,blank=True)
#     st = models.ForeignKey(COA,on_delete=models.DO_NOTHING,verbose_name='Счет',related_name='account', null=True,blank=True)
#     description = models.TextField(verbose_name='Описание',null=True,blank=True)
#     dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Дт')
#     cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Кр')
    
#     class Meta:
#         managed = False
#         db_table = '"gl"."mv_accurals"'
#         verbose_name = "Взаиморасчеты"
#         verbose_name_plural = "Взаиморасчеты"

#     def __str__(self):
#         return f"{self.date_from:} на сумму: ({(self.dt - self.cr):,.0f})"
    

