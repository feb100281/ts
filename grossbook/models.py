# grossbook/models.py
from django.db import models
from utils.choises import CURRENCY_CHOISE
from corporate.models import Owners,COA,CfItems
from contracts.models import Contracts

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
    
    
            
    
    
    
    
    