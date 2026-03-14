import xlsxwriter
import io
import re
import logging
from typing import List, Dict

# Configure logger
logger = logging.getLogger(__name__)

class ExcelExporter:
    """
    Service for exporting data to multi-tab Excel files using xlsxwriter.
    """

    @staticmethod
    def sanitize_sheet_name(name: str) -> str:
        """
        Sanitize sheet name for Excel compatibility:
        - Max 31 characters.
        - Remove forbidden characters: [ ] : * ? / \
        - Strip leading/trailing whitespace.
        - Collapse multiple spaces.
        """
        # Remove forbidden characters
        sanitized = re.sub(r'[\[\]:\*\?\/\\]', '', name)
        # Collapse multiple spaces
        sanitized = re.sub(r'\s+', ' ', sanitized)
        # Trim to 31 characters and strip
        return sanitized[:31].strip()

    def generate_excel(self, summary_data: List[Dict], transactions_data: List[Dict] = None) -> io.BytesIO:
        """
        Generate a multi-tab Excel file from summary and transactions data.
        Returns a BytesIO object containing the Excel file.
        """
        try:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            
            # Add formatting
            bold = workbook.add_format({'bold': True})
            currency = workbook.add_format({'num_format': '$#,##0.00'})
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',
                'border': 1
            })

            # Tab 1: Summary
            self._write_summary_sheet(workbook, summary_data, header_format, currency)

            # Tab 2: Transactions (Always create the sheet, even if empty)
            self._write_transactions_sheet(workbook, transactions_data or [], header_format, currency)

            workbook.close()
            output.seek(0)
            return output
        except Exception as e:
            logger.error(f"Error generating Excel: {str(e)}", exc_info=True)
            raise

    def _write_summary_sheet(self, workbook, data, header_format, currency_format):
        sheet_name = self.sanitize_sheet_name("Summary")
        worksheet = workbook.add_worksheet(sheet_name)
        
        headers = ["Package ID", "Filename", "Lender", "Date", "Total"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            
        if not data:
            worksheet.write(1, 0, "No data available for export.")
            return

        for row, item in enumerate(data, start=1):
            worksheet.write(row, 0, item.get("package_id") or "N/A")
            worksheet.write(row, 1, item.get("filename") or "Unknown")
            worksheet.write(row, 2, item.get("lender_name") or "N/A")
            worksheet.write(row, 3, item.get("document_date") or "N/A")
            
            total = item.get("total_amount")
            if total is not None:
                try:
                    worksheet.write(row, 4, float(total), currency_format)
                except (ValueError, TypeError):
                    worksheet.write(row, 4, 0.0, currency_format)
            else:
                worksheet.write(row, 4, 0.0, currency_format)
            
        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 30)
        worksheet.set_column(2, 2, 20)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 15)

    def _write_transactions_sheet(self, workbook, data, header_format, currency_format):
        sheet_name = self.sanitize_sheet_name("Transactions")
        worksheet = workbook.add_worksheet(sheet_name)
        
        headers = ["Package ID", "Component", "Amount"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            
        if not data:
            worksheet.write(1, 0, "No transactions found.")
            return

        for row, item in enumerate(data, start=1):
            worksheet.write(row, 0, item.get("package_id") or "N/A")
            worksheet.write(row, 1, item.get("component") or "N/A")
            
            amount = item.get("amount")
            if amount is not None:
                try:
                    worksheet.write(row, 2, float(amount), currency_format)
                except (ValueError, TypeError):
                    worksheet.write(row, 2, 0.0, currency_format)
            else:
                worksheet.write(row, 2, 0.0, currency_format)
            
        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 30)
        worksheet.set_column(2, 2, 15)
