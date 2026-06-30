from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import models
from django.db import transaction
from django.db import connection


from conns import get_duckdb_conn_with_opt

import pandas as pd


class Command(BaseCommand):
    help = "Эта комманда запускает pipeline для GL"    
       
    def handle(self, *args, **options):
                
        self.stdout.write(self.style.WARNING("Обновляем данные gear/management/commands/gl_refference.py"))
        call_command("gl_refference")
        
        self.stdout.write(self.style.WARNING("Делаем проводки по банковским операциям gear/management/commands/gl_assets_ba.py"))
        call_command("gl_assets_ba")
        
        
                