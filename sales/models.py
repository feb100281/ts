from django.db import models
from corporate.models import Countries

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

class SellerSKU(models.Model):
    
    seller_article = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="Артикул продавца")

    class Meta:
        verbose_name = "Артикул продавца"
        verbose_name_plural = "Артикулы продавца"

    def __str__(self):
        return self.seller_article

class Barcode(models.Model):
    
    barcode = models.CharField(max_length=32, unique=True, db_index=True, verbose_name="Баркод")

    class Meta:
        verbose_name = "Баркод"
        verbose_name_plural = "Баркоды"

    def __str__(self):
        return self.barcode

class Size(models.Model):
    
    size = models.CharField(max_length=32, unique=True, db_index=True, verbose_name="Размер")

    class Meta:
        verbose_name = "Размер"
        verbose_name_plural = "Размеры"

    def __str__(self):
        return self.size



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
    
    barcodes = models.ManyToManyField(
        "Barcode",
        related_name="products",
        blank=True,        
        verbose_name="Баркод",
    )
    
    sizes = models.ManyToManyField(
        "Size",
        related_name="products",
        blank=True,        
        verbose_name="Размер",
    )
    
    sellersku = models.ManyToManyField(
        "SellerSku",
        related_name="products",
        blank=True,        
        verbose_name="Размер",
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

class Warehouse(models.Model):
    name = models.CharField(max_length=250,verbose_name='Наименование')
    
    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склады"

    def __str__(self):
        return str(self.name)

class Order(models.Model):
    code = models.CharField(max_length=250,verbose_name='Код заказа')
    
    class Meta:
        verbose_name = "Код заказа"
        verbose_name_plural = "Коды заказа"

    def __str__(self):
        return str(self.code)

class SalesData(models.Model):
    created_date = models.DateTimeField(verbose_name='Дата создания')
    sale_date = models.DateTimeField(verbose_name='Дата продажи')
    product = models.ForeignKey(Product,on_delete=models.PROTECT,verbose_name='WB Артикль')
    barcode = models.ForeignKey(Barcode,on_delete=models.PROTECT,verbose_name='Баркод',null=True,blank=True)
    brand = models.ForeignKey(Brand,on_delete=models.PROTECT,verbose_name='Бренд',null=True,blank=True)
    size = models.ForeignKey(Size,on_delete=models.PROTECT,verbose_name='Размер',null=True,blank=True)
    country = models.ForeignKey(Countries,on_delete=models.PROTECT,verbose_name='Размер',null=True,blank=True)
    order = models.ForeignKey(Order,on_delete=models.PROTECT,verbose_name='Код заказа',null=True,blank=True)
    warehouse = models.ForeignKey(Warehouse,on_delete=models.PROTECT,verbose_name='Склад',null=True,blank=True)
    amount_dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='dt Выручка')
    amount_cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='cr Выручка')
    quant_dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='dt Количество')
    quant_cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='cr Количество')
    dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Дт')
    cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Кр')
    transaction_type = models.CharField(max_length=50,verbose_name='Тип транскации')
    
    class Meta:
        verbose_name = "Данные продаж"
        verbose_name_plural = "Данные продаж"

    def __str__(self):
        return f"{self.sale_date} - {self.product} {(self.dt - self.cr):,.2f}"


# -------------------------------
# MV модели
#--------------------------------

# Дневные продажи

class MVSalesDaily(models.Model): 
    date = models.DateField(primary_key=True, verbose_name='Дата')
    amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Оборот',null=True,blank=True)
    revenue = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Выручка',null=True,blank=True)
    comission = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Проц. комисии',null=True,blank=True)
    quant = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Количество',null=True,blank=True)
    sales = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Продажи',null=True,blank=True)
    rtr = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Возвраты',null=True,blank=True)
    rtr_ratio = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='К возвратов',null=True,blank=True)
    
    class Meta: 
        managed = False 
        db_table = "mv_sales_daily"
        verbose_name = "Дневные продажи"
        verbose_name_plural = "Дневные продажи"
        
       
    def __str__(self):
        return self.date.strftime("%d %b-%Y")

#    SELECT 
#   t.created_date,
#   t.sale_date,
#   p.id  AS product_id,
#   bc.id AS barcode_id,
#   b.id  AS brand_id,
#   s.id  AS size_id,
#   c.id  AS country_id,
#   o.id  AS order_id,
#   w.id  AS warehouse_id,
#   case when t.transaction_type != 'Возврат' then t.amount else 0 end as amount_dt,
#   case when t.transaction_type = 'Возврат' then t.amount else 0 end as amount_cr,
#   case when t.transaction_type != 'Возврат' then t.payout_amount else 0 end as dt,
#   case when t.transaction_type = 'Возврат' then t.payout_amount else 0 end as cr,
#   t.transaction_type
# FROM public.fixed_bars AS t
# LEFT JOIN sales_product        AS p  ON p.wb_article = t.wb_article
# LEFT JOIN sales_brand          AS b  ON b.name       = t.brand
# LEFT JOIN sales_barcode        AS bc ON bc.barcode   = t.barcode
# LEFT JOIN sales_size           AS s  ON s.size       = t.size
# LEFT JOIN corporate_countries  AS c  ON t.country ~* c.regex_patterns
# LEFT JOIN sales_order          AS o  ON o.code       = t.order_id
# LEFT JOIN sales_warehouse      AS w  ON w.name       = t.warehouse;


# -- Даты (фильтр/сортировка)
# CREATE INDEX IF NOT EXISTS salesdata_created_date_idx
#   ON sales_salesdata (created_date);

# CREATE INDEX IF NOT EXISTS salesdata_sale_date_idx
#   ON sales_salesdata (sale_date);

# -- FK (частые фильтры/группировки)
# CREATE INDEX IF NOT EXISTS salesdata_product_id_idx
#   ON sales_salesdata (product_id);

# CREATE INDEX IF NOT EXISTS salesdata_barcode_id_idx
#   ON sales_salesdata (barcode_id);

# CREATE INDEX IF NOT EXISTS salesdata_brand_id_idx
#   ON sales_salesdata (brand_id);

# CREATE INDEX IF NOT EXISTS salesdata_size_id_idx
#   ON sales_salesdata (size_id);

# CREATE INDEX IF NOT EXISTS salesdata_country_id_idx
#   ON sales_salesdata (country_id);

# CREATE INDEX IF NOT EXISTS salesdata_order_id_idx
#   ON sales_salesdata (order_id);

# CREATE INDEX IF NOT EXISTS salesdata_warehouse_id_idx
#   ON sales_salesdata (warehouse_id);

# -- Композитные под отчёты "по периоду + измерение"
# CREATE INDEX IF NOT EXISTS salesdata_sale_date_product_idx
#   ON sales_salesdata (sale_date, product_id);

# CREATE INDEX IF NOT EXISTS salesdata_sale_date_brand_idx
#   ON sales_salesdata (sale_date, brand_id);

# CREATE INDEX IF NOT EXISTS salesdata_sale_date_warehouse_idx
#   ON sales_salesdata (sale_date, warehouse_id);

# -- Если часто фильтруешь по типу транзакции
# CREATE INDEX IF NOT EXISTS salesdata_transaction_type_idx
#   ON sales_salesdata (transaction_type);