from django.db import models


class ProductGroup(models.Model):
    name = models.CharField(max_length=250, unique=True, verbose_name="Группа")
    description = models.TextField(null=True, blank=True, help_text="Описание группы")

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы товаров"

    def __str__(self):
        return self.name


class Category(models.Model):
    group = models.ForeignKey(
        ProductGroup,
        on_delete=models.PROTECT,
        related_name="categories",
        verbose_name="Группа",
        blank=True,
        null = True
    )
    name = models.CharField(max_length=250, verbose_name="Категория")
    description = models.TextField(null=True, blank=True, help_text="Описание категории")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        constraints = [
            models.UniqueConstraint(
                fields=["group", "name"],
                name="uniq_category_in_group",
            )
        ]

    def __str__(self):
        return f"{self.group.name} → {self.name}" if self.group else self.name


class Brand(models.Model):
    name = models.CharField(max_length=250, unique=True, verbose_name="Бренд")
    description = models.TextField(null=True, blank=True, help_text="Описание бренда")

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self):
        return self.name


class Product(models.Model):
    wb_article = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="Артикул WB")

    categories = models.ManyToManyField(
        "Category",
        related_name="products",
        blank=True,        
        verbose_name="Категории",
    )

    brands = models.ManyToManyField(
        "Brand",
        related_name="products",
        blank=True,        
        verbose_name="Бренды",
    )

    class Meta:
        verbose_name = "Товар (WB)"
        verbose_name_plural = "Товары (WB)"

    def __str__(self):
        return self.wb_article
    
    @property
    def imt_name(self):
        try:
            return self.wb_data.data.get("imt_name")
        except Exception:
            return None


class SellerSKU(models.Model):
    # если seller_article строго один на товар — ставь OneToOne
    product = models.OneToOneField(
        Product,
        on_delete=models.PROTECT,
        related_name="seller_sku",
        verbose_name="Товар",
    )
    seller_article = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="Артикул продавца")

    class Meta:
        verbose_name = "Артикул продавца"
        verbose_name_plural = "Артикулы продавца"

    def __str__(self):
        return self.seller_article


class Barcode(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="barcodes",
        verbose_name="Товар",
    )
    barcode = models.CharField(max_length=32, unique=True, db_index=True, verbose_name="Баркод")

    class Meta:
        verbose_name = "Баркод"
        verbose_name_plural = "Баркоды"

    def __str__(self):
        return self.barcode

class ProductData(models.Model):
    wb_article = models.OneToOneField(   # <— тут логичнее OneToOne
        "Product",
        on_delete=models.CASCADE,
        related_name="wb_data",
        db_index=True,
    )
    data = models.JSONField(null=True, blank=True)
    basket = models.CharField(max_length=5, null=True, blank=True, db_index=True)  # "12"
    fetched_at = models.DateTimeField(null=True, blank=True)
    status = models.SmallIntegerField(default=0, db_index=True)  # 0=new,1=basket,2=json,-1=error
    error = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Данные продуктов"
        verbose_name_plural = "Данные продуктов"

    def __str__(self):
        return str(self.wb_article)

class MVSalesProductData(models.Model): 
    wb_article_id = models.BigIntegerField(primary_key=True) 
    status = models.SmallIntegerField(verbose_name='статус',null=True) 
    basket = models.TextField(null=True,verbose_name='Корзина WB') 
    fetched_at = models.DateTimeField(null=True,verbose_name='Дата загрузки')
    nm_id = models.TextField(null=True,verbose_name='nm_id') 
    imt_id = models.TextField(null=True,verbose_name='WB Артикль') 
    imt_name = models.TextField(null=True,verbose_name='Наименование') 
    slug = models.TextField(null=True,verbose_name='slug') 
    vendor_code = models.TextField(null=True,verbose_name='Код поставщика') 
    subj_name = models.TextField(null=True,verbose_name='Категория') 
    subj_root_name = models.TextField(null=True,verbose_name='Группа') 
    subject_id = models.TextField(null=True,verbose_name='subject_id') 
    subject_root_id = models.TextField(null=True,verbose_name='subject_root_id') 
    brand_name = models.TextField(null=True,verbose_name='Бренд') 
    supplier_id = models.TextField(null=True,verbose_name='supplier_id') 
    photo_count = models.SmallIntegerField(null=True,verbose_name='Количество фото') 
    nm_colors_names = models.TextField(null=True,verbose_name='Цвета') 
    create_date = models.DateTimeField(null=True,verbose_name='Дата создания') 
    update_date = models.DateTimeField(null=True,verbose_name='Дата обновления') 
    contents = models.TextField(null=True,verbose_name='Кр описание') 
    description = models.TextField(null=True,verbose_name='Описание') 
    composition = models.TextField(null=True,verbose_name='Состав') 
    country = models.TextField(null=True,verbose_name='Страна производитель') 
    sex = models.TextField(null=True,verbose_name='Пол') 
    kit = models.TextField(null=True,verbose_name='Комплект') 
    class Meta: 
        managed = False 
        db_table = "mv_sales_productdata"
        verbose_name = "Номенклатура WB"
        verbose_name_plural = "Номенклатуры WB"
        
        
    def __str__(self):
        return f"{self.imt_name} ({self.imt_id})"
 