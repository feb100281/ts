from django.db import models

# Create your models here.
class RegularReport(models.Model):
    name = models.CharField(max_length=100,verbose_name='Название отчета')
    # presentation = 
    description = models.TextField(verbose_name='Описание')
    
    class Meta:       
        verbose_name = "Регулярные отчет"
        verbose_name_plural = "Регулярные отчеты"

    def __str__(self):
        return f"{self.name}"
    
    

