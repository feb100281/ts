"""Перевод назначений операций вне РФ по словарю шаблонов (translations_hy_ru.json + справочник)."""

from django.core.management.base import BaseCommand

from treasury.models import TextTranslation
from utils.bsparsers.am.loader import retranslate


class Command(BaseCommand):
    help = "Перевести назначения по словарю; показать шаблоны без перевода"

    def add_arguments(self, parser):
        parser.add_argument("--top", type=int, default=30, help="сколько шаблонов без перевода показать")

    def handle(self, *args, top, **options):
        retranslate(log=self.stdout.write)
        left = TextTranslation.objects.filter(translation__isnull=True).order_by("-hits")
        self.stdout.write(f"Шаблонов без перевода: {left.count()}, операций: {sum(x.hits for x in left)}")
        for x in left[:top]:
            self.stdout.write(f"  {x.hits:>6}  {x.source}")
