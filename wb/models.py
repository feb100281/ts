from django.db import models

class TechSize(models.Model):
    size = models.CharField(max_length=100, primary_key=True, verbose_name="Размер")

    class Meta:
        verbose_name = "Тех. размер"
        verbose_name_plural = "Тех. размеры"

    def __str__(self):
        return self.size

class Subject(models.Model):
    subject_id = models.BigIntegerField(primary_key=True,verbose_name="subject_id")
    name = models.CharField(max_length=250,verbose_name="Категория", blank=True, null=True)
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
    
    def __str__(self):
        return f"{self.name}"

# Create your models here.
class Product(models.Model):
    nm_id = models.BigIntegerField(primary_key=True,verbose_name="Артукул WB")
    sa_name = models.CharField(max_length=250,verbose_name="Артикул продавца", blank=True, null=True)
    title = models.CharField(max_length=250,verbose_name="Наименование", blank=True, null=True)
    imtID = models.BigIntegerField(verbose_name="imtID",blank=True,null=True)
    nmUUID = models.CharField(max_length=250,verbose_name="nmUUID", blank=True, null=True)
    subject = models.ForeignKey(Subject,on_delete=models.DO_NOTHING,verbose_name="Категория", blank=True, null=True)
    brand = models.CharField(max_length=250,verbose_name="Бренд", blank=True, null=True)
    createdAt = models.DateTimeField(verbose_name='Создано',null=True,blank=True)
    updatedAt = models.DateTimeField(verbose_name='Обновлено',null=True,blank=True)
    tnved = models.CharField(max_length=250,verbose_name="ТНВЭД", blank=True, null=True)
    gender = models.CharField(max_length=250,verbose_name="Пол", blank=True, null=True)
    country = models.CharField(max_length=250,verbose_name="Страна производитель", blank=True, null=True)  
    vat_rate = models.CharField(max_length=250,verbose_name="Указанная ставка НДС", blank=True, null=True)  
    
    tech_sizes = models.ManyToManyField(
        "TechSize",
        verbose_name="Тех. размеры",
        blank=True,
        related_name="products",
    )

    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Каталог WB"
    
    def __str__(self):
        return f"{self.title} ({self.nm_id})"


