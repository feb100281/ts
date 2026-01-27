# contracts/models.py

from django.db import models
from corporate.models import Owners, CfItems
from counterparties.models import Counterparty
from django.conf import settings
import os
from django.utils.text import slugify



# Модели договоров.

# ----------------------------
# Типы договоров
# ----------------------------

class ContractsTitle(models.Model):
    title = models.CharField(max_length=250,verbose_name='Тип договора',unique=True)
    
    class Meta:
        verbose_name = "Тип договора"
        verbose_name_plural = "Типы договоров"

    def __str__(self):
        return self.title
    
class Contracts(models.Model):
    title = models.ForeignKey(ContractsTitle,on_delete=models.DO_NOTHING, verbose_name='Тип документа')
    number = models.CharField(max_length=250,verbose_name='Номер',null=True,blank=True)
    date = models.DateField(verbose_name='Дата договора',null=True,blank=True) 
    owner = models.ForeignKey(Owners,on_delete=models.CASCADE, verbose_name='Компания')
    cp = models.ForeignKey(Counterparty,on_delete=models.CASCADE,verbose_name='Контрагент')   
    date_signed = models.DateField(verbose_name='Дата подписания',null=True,blank=True)
    
    pid = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="amendments"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Менеджер договора',
        related_name='managed_by'
        # limit_choices_to={'groups__name': 'Подразделение'}
    )
    is_signed = models.BooleanField(verbose_name='Подписан',null=True,blank=True)
    regex =  models.TextField(verbose_name='RegEx',null=True,blank=True)
    
    class Meta:
        verbose_name = "Договор"
        verbose_name_plural = "Договоры"        

    def __str__(self):
        
        number = 'без номера' if not self.number else self.number
        date = 'без даты' if not self.date else self.date
        
        return f"{self.cp} {self.title} № {number} от {date} (id {self.id})"
    
    @property
    def is_amendment(self):
        return self.pid is not None
    
class ContractItems(models.Model):
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,verbose_name='Контрагент')
    item = models.CharField(max_length=550,verbose_name='Предмет договора',null=True,blank=True)
    
    class Meta:
        verbose_name = "Предмет договора"
        verbose_name_plural = "Предметы договоров"

    def __str__(self):
        return self.item
    
class Conditions(models.Model):
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,verbose_name='Контрагент')
    condition = models.CharField(max_length=550,verbose_name='Условие',null=True,blank=True)
    date_start = models.DateField(verbose_name='Дата начлала',null=True,blank=True) 
    date_finish = models.DateField(verbose_name='Дата окончания',null=True,blank=True) 
    accural_finc =  models.CharField(max_length=100,verbose_name='Функция начислений',null=True,blank=True)
    params = models.JSONField('Параметры', null=True, blank=True)
    
    class Meta:
        verbose_name = "Условие договора"
        verbose_name_plural = "Условия договоров"

    def __str__(self):
        return self.condition
    

def document_upload_path(instance, filename):
    cp = slugify(instance.contracts.cp.name) if hasattr(instance.contracts.cp, "name") else instance.contracts.cp_id
    try:
        number = slugify(instance.contracts.number)
    except:
        number = 'б/н'
    try:
        date = instance.contracts.date.strftime("%Y-%m-%d")
    except:        
        date = 'б/д'
    return os.path.join("la", cp, f"{number}_{date}", filename)

class ContractFiles(models.Model):
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,related_name='files')
    description = models.TextField(verbose_name='описание',null=True,blank=True)
    file = models.FileField(upload_to=document_upload_path, verbose_name="Файл документа", null=True, blank=True) 

class CfItemAuto(models.Model):
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,verbose_name='Договор')
    regex =  models.CharField(max_length=500,verbose_name='RegEx',null=True,blank=True)
    defaultcfdt = models.ForeignKey(CfItems,on_delete=models.CASCADE, verbose_name='Статья CF по дефолту для Дт',null=True,blank=True,related_name="contracts_default_dt", )
    defaultcfcr = models.ForeignKey(CfItems,on_delete=models.CASCADE, verbose_name='Статья CF по дефолту для Кт',null=True,blank=True,related_name="contracts_default_cr", )
    
    class Meta:
        verbose_name = "⚙️ Автоматизация"
        verbose_name_plural = "⚙️ Автоматизация"

    def __str__(self):
        return str(self.contract)

    
    
    