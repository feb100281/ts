from django.db import models

# Create your models here.

SLIDE_STYLE = {
    "width": "1280px",
    "height": "720px",
    "margin": "0 auto 24px auto",
    "padding": "40px",
    "boxSizing": "border-box",
    "backgroundColor": "white",
    "overflow": "hidden",
    "position": "relative",
    "boxShadow": "0 0 8px rgba(0,0,0,0.15)",
}


def get_default_slide_style():
    return SLIDE_STYLE.copy()

class ReportType(models.TextChoices):
    AH = "AH", "Ad-hoc"
    COB = "COB", "Close of business"
    DE = "DE", "Daily"
    WE = "WE", "Weekly"
    ME = "ME", "Monthly"
    QE = "QE", "Quarterly"
    HY = "HY", "Half-year"
    YE = "YE", "Yearly"


class SlideRegistered(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Title"
    )

    python_path = models.CharField(
        max_length=500,
        unique=True,
        verbose_name="Python path",
        help_text="Example: reports.slides.revenue.render"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Is active"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Slide"
        verbose_name_plural = "Slides"
        ordering = ["title"]

    def __str__(self):
        return self.title



class Report(models.Model):

    title = models.CharField(
        max_length=255,
        verbose_name="Title"
    )

    subtitle = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Subtitle"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )

    author = models.CharField(
        max_length=255,
        default="Дарья Войтенко",
        verbose_name="Author"
    )

    company = models.CharField(
        max_length=255,
        default="Трендсеттер",
        verbose_name="Company"
    )

    css = models.CharField(
        max_length=255,
        default="print.css",
        verbose_name="CSS file"
    )

    slide_style = models.JSONField(
        default=get_default_slide_style,
        verbose_name="Slide style"
    )

    date_from = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date from"
    )

    date_to = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date to"
    )

    report_type = models.CharField(
        max_length=10,
        choices=ReportType.choices,
        default=ReportType.AH,
        verbose_name="Report type"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
   
class Section(models.Model):

    title = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Title"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ["title"]

    def __str__(self):
        return self.title


from django.db import models

class ReportConstructor(models.Model):

    report = models.ForeignKey(
        "Report",
        on_delete=models.CASCADE,
        related_name="slides"
    )

    section = models.ForeignKey(
        "Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_slides"
    )

    slide = models.ForeignKey(
        "SlideRegistered",
        on_delete=models.CASCADE,
        related_name="report_usage"
    )

    order = models.PositiveIntegerField(
        default=100
    )

    filters = models.JSONField(
    null=True,
    blank=True,
    default=None,
    verbose_name="Filters"
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Report constructor"
        verbose_name_plural = "Report constructor"
        ordering = ["order", "id"]

    def __str__(self):
        return (
            f"{self.report.title} | "
            f"{self.order} | "
            f"{self.slide.title}"
        )