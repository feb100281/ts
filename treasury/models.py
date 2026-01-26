# treasury/models.py
from django.db import models
from corporate.models import BankAccount,Owners, CfItems
from contracts.models import Contracts
from counterparties.models import Counterparty
from django.core.exceptions import ValidationError

from utils.bsparsers.bsparser import get_bs_details


class BankStatements(models.Model):
    
    file = models.FileField(upload_to='migrations/', verbose_name="Файл миграции")
    owner = models.ForeignKey(Owners,verbose_name='Компания',on_delete=models.CASCADE,null=True,blank=True)
    ba = models.ForeignKey(BankAccount,verbose_name='Счет',on_delete=models.CASCADE,null=True,blank=True)
    start = models.DateField(verbose_name="C",null=True,blank=True)
    finish = models.DateField(verbose_name="По",null=True,blank=True)
    bb = models.DecimalField("Начальный остаток",max_digits=12,decimal_places=2,null=True,blank=True)
    eb = models.DecimalField("Конечный остаток",max_digits=12,decimal_places=2,null=True,blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Выписка"
        verbose_name_plural = "Выписки"

    def __str__(self):
        return f"{self.start}-{self.finish} {self.owner} ({self.ba})"
    
    def save(self, *args, **kwargs):
        # Сначала сохраняем, чтобы файл точно оказался на диске и был путь
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Если файла нет — нечего парсить
        if not self.file:
            return

        # Триггер: заполняем только если поля ещё пустые (можешь поменять условие)
        need_parse = any(v is None for v in (self.start, self.finish, self.bb, self.eb))
        if not need_parse:
            return

        # Парсим файл
        bank, start_date,end_date,bb,eb = get_bs_details(self.file.path)
        

        self.start = start_date
        self.finish = end_date        
        self.bb = bb
        self.eb = eb

        account_number = bank  

        ba_id = None
        owner_id = None

        if account_number:
            ba = BankAccount.objects.select_related("corporate").filter(account=account_number).first()
            if ba:
                ba_id = ba.id
                owner_id = ba.corporate_id

        type(self).objects.filter(pk=self.pk).update(
            start=self.start,
            finish=self.finish,
            bb=self.bb,
            eb=self.eb,
            ba_id=ba_id,
            owner_id=owner_id,
        )

        self.ba_id = ba_id
        self.owner_id = owner_id
        
class CfData(models.Model):
    bs = models.ForeignKey(BankStatements,on_delete=models.CASCADE,verbose_name="Выписка",null=True,blank=True)
    doc_type = models.CharField("Документ",max_length=250,null=True,blank=True)
    doc_numner = models.CharField("Номер",max_length=250,null=True,blank=True)
    doc_date = models.CharField("Дата",max_length=250,null=True,blank=True)
    date = models.DateField("Дата платежа",blank=True,null=True)
    dt = models.DecimalField("Дт",max_digits=12,decimal_places=2,null=True,blank=True)
    cr = models.DecimalField("Кр",max_digits=12,decimal_places=2,null=True,blank=True)
    tax_id = models.CharField("ИНН",max_length=250,null=True,blank=True)
    temp = models.TextField("Назначение",null=True,blank=True)
    cp_bs_name = models.CharField("Имя в выписке",max_length=250,null=True,blank=True)
    intercompany = models.BooleanField("Внутрегрупповой")
    payer_account = models.CharField("Счет плательщика",max_length=250,null=True,blank=True)
    reciver_account = models.CharField("Счет получателя",max_length=250,null=True,blank=True)
    vat_rate = models.DecimalField("НДС",max_digits=6,decimal_places=2,null=True,blank=True)
    cp = models.ForeignKey(Counterparty,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Контрагент по ИНН в выписке",related_name="cp_init" )
    cp_final = models.ForeignKey(Counterparty,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Контрагент финальный",related_name="cp_final")
    owner = models.ForeignKey(Owners,on_delete=models.CASCADE,null=True,blank=True, verbose_name="Компания")
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Договор")
    cfitem = models.ForeignKey(CfItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Статья CF" )
    ba = models.ForeignKey(BankAccount,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Расчетный счет")
    
    
    class Meta:
        verbose_name = "CF документ"
        verbose_name_plural = "CF документы"        
        constraints = [
            models.UniqueConstraint(
                fields=["bs", "doc_numner", "date", "dt", "cr"],
                name="uniq_cfdata_bs_row",
            )
        ]

    def __str__(self):
        return f"{self.doc_type} № {self.doc_numner} от {self.doc_date} (на сумму {self.dt - self.cr})"
    
class CfSplits(models.Model):
    transaction = models.ForeignKey(CfData,on_delete=models.CASCADE,verbose_name='Транскация')
    dt = models.DecimalField("Дт",max_digits=12,decimal_places=2,null=True,blank=True)
    cr = models.DecimalField("Кр",max_digits=12,decimal_places=2,null=True,blank=True)
    temp = models.TextField("Назначение",null=True,blank=True)
    vat_rate = models.DecimalField("НДС",max_digits=6,decimal_places=2,null=True,blank=True)
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Договор")
    cfitem = models.ForeignKey(CfItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Статья CF" )
    class Meta:
        verbose_name = "Сплит"
        verbose_name_plural = "Сплиты оплат"   
    
    def __str__(self):
        return f"{self.transaction}"
    
class ContractsRexex(models.Model):
    cp = models.ForeignKey(Counterparty,on_delete=models.CASCADE,verbose_name='Контрагент')
    regex = models.CharField(max_length=500,verbose_name='RegEx',default=r"^.*$")
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,verbose_name='Договор')
    comments = models.TextField('Комментарии')
    
    class Meta:
        verbose_name = "Автоматизация"
        verbose_name_plural = "Автоматизация"   
    
    def __str__(self):
        return f"{self.cp} - {self.contract}"
    
    def clean(self):
        """
        Валидация: contract должен принадлежать cp.
        """
        if not self.cp_id or not self.contract_id:
            return

        # ВАРИАНТ A: если в Contracts поле называется `cp`
        contract_cp_id = getattr(self.contract, "cp_id", None)

        # ВАРИАНТ B: если в Contracts поле называется `contragent`
        # contract_cp_id = getattr(self.contract, "contragent_id", None)

        if contract_cp_id is None:
            raise ValidationError({
                "contract": "Не удалось проверить принадлежность: в Contracts нет поля cp_id/contragent_id."
            })

        if contract_cp_id != self.cp_id:
            raise ValidationError({
                "contract": "Нельзя сохранить: выбранный договор не принадлежит выбранному контрагенту."
            })

    def save(self, *args, **kwargs):
        # чтобы валидация срабатывала и в админке, и при save() из кода
        self.full_clean()
        return super().save(*args, **kwargs)