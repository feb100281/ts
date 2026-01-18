# macro/management/commands/import_market_site.py
from django.core.management.base import BaseCommand, CommandError

from macro.models import MarketSource
from macro.parsers.site_html import SiteHTMLParser
from macro.services.market_ingest import ingest_market_item


class Command(BaseCommand):
    help = "Import market listings/observations by parsing an allowed website (HTML MVP)"

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="MarketSource.code")
        parser.add_argument("--base-url", required=True, help="https://example.com")
        parser.add_argument("--list-path", required=True, help="/rent/offices?..." )
        parser.add_argument("--pages", type=int, default=1, help="How many pages to scan")
        parser.add_argument("--delay", type=float, default=1.0, help="Delay between pages (sec)")

    def handle(self, *args, **opts):
        try:
            source = MarketSource.objects.get(code=opts["source"])
        except MarketSource.DoesNotExist:
            raise CommandError(f"MarketSource with code='{opts['source']}' not found. Create it in admin first.")

        parser = SiteHTMLParser(
            base_url=opts["base_url"],
            list_path=opts["list_path"],
            delay_sec=opts["delay"],
        )

        n = 0
        for item in parser.iter_items(max_pages=opts["pages"]):
            ingest_market_item(source, item)
            n += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {n} items from site (source={source.code})"))
