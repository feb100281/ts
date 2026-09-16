# contracts/loans_report/builder.py

from io import BytesIO
from openpyxl import Workbook
from typing import List, Dict
from .queries import LoansQueries
from .sheets import TOCSheet, LoanSheet


class LoansReportGenerator:    
    def __init__(self):
        self.queries = LoansQueries()
        self.wb = Workbook()
    
    def generate(self, report_date: str) -> BytesIO:
        try:
            # ОДИН запрос ко всем данным
            report_data = self.queries.get_full_report_data(report_date)
            loans_list = report_data['loans']
            transactions_by_contract = report_data['transactions']
            
            if not loans_list:
                raise ValueError(f"Нет договоров займа или кредита на дату {report_date}")
            
            # Создаем оглавление
            toc = TOCSheet(self.wb)
            toc.build(loans_list, report_date)
            
            # Создаем лист для каждого договора (уже с транзакциями)
            for idx, loan in enumerate(loans_list, start=1):
                contract_id = loan.get('contract_id')
                transactions = transactions_by_contract.get(contract_id, [])
                
                # Создаем детальный лист
                sheet_name = str(idx)
                loan_sheet = LoanSheet(self.wb, sheet_name)
                loan_sheet.build(loan, report_date, transactions, {})
                
                print(f"Создан лист {sheet_name} для {loan.get('counterparty_name', '')[:30]}")
            
            # Удаляем дефолтный лист
            if 'Sheet' in self.wb.sheetnames:
                self.wb.remove(self.wb['Sheet'])
            
            # Сохраняем в BytesIO
            output = BytesIO()
            self.wb.save(output)
            output.seek(0)
            return output
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise



