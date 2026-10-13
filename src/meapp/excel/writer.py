from pathlib import Path
import logging

import xlwings as xw

from meapp.exceptions import ExcelWriteError
from meapp.models import MaintenanceReport

XL_COLOR_INDEX_AUTOMATIC = -4105
logger = logging.getLogger(__name__)


class ExcelManager:
    TABLE_NAME = "Table2"

    FLAG_STYLES = {
        1: {"fill": (255, 199, 206), "font": (156, 0, 6)},    # not found
        2: {"fill": (255, 235, 156), "font": (156, 87, 0)},   # found, unit assumed
    }

    # (column letter, MaintenanceReport attribute). Single source of truth:
    # the blank-row check and the writer both use this, so they can't drift apart.
    # Remove the "H" entry if your table has no shift column.
    COLUMNS = [
        ("A", "report_date"),
        ("B", "switch_overs"),
        ("C", "generator"),
        ("D", "running_time_hr"),
        ("E", "running_time_mins"),
        ("F", "avg_load"),
        ("G", "volume_of_diesel"),
        ("H", "shift"),
    ]

    def __init__(self, wb_path: Path) -> None:
        self.wb_path = Path(wb_path).resolve()
        self.worksheet = None
        self._closed = False
        self.save_progress = False
        self.excel_app = None
        self.workbook_is_mine = True

        # Save and close matching workbooks already open in Excel.
        for app in list(xw.apps):
            for workbook in list(app.books):
                if Path(workbook.fullname).resolve() == self.wb_path:
                    self.excel_app = app
                    self.workbook_is_mine = False

                    workbook.save()
                    workbook.close()

        # Open the workbook in an Excel instance owned by this manager.
        try:
            self.excel_app = self.excel_app or xw.App(visible=True, add_book=False)
            self.excel_app.api.WindowState = xw.constants.WindowState.xlNormal
            self.workbook = self.excel_app.books.open(str(self.wb_path))
            logger.info("Maintenance workbook opened.")
        except Exception as exc:
            logger.error("Maintenance workbook could not be opened.")
            if self.excel_app is not None:
                try:
                    self.excel_app.quit()
                except Exception:
                    pass
            raise ExcelWriteError(
                "Could not open the maintenance workbook."
            ) from exc

    # ---- context manager -------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        # Save only after the workflow explicitly commits and exits successfully.
        try:
            self.close_workbook(save=self.save_progress and exc_type is None)
        except Exception as exc:
            raise ExcelWriteError(
                "Could not save or close the maintenance workbook."
            ) from exc
        return False                       # don't swallow the exception

    @property
    def save_progress(self) -> bool:
        return self._save


    @save_progress.setter
    def save_progress(self, value: bool) -> None:
        self._save = value


    # ---- worksheet helpers -----------------------------------------------
    def open_worksheet(self, worksheet):
        try:
            self.worksheet = self.workbook.sheets[worksheet]
            logger.info("Maintenance worksheet opened.")
        except Exception as exc:
            logger.error("Maintenance worksheet could not be opened.")
            raise ExcelWriteError(
                "The maintenance worksheet could not be opened."
            ) from exc

    def _add_table_row(self) -> int:
        """Append a row to the table and return its worksheet row number."""
        table = self.worksheet.tables[self.TABLE_NAME]
        new_list_row = table.api.ListRows.Add()
        return new_list_row.Range.Row      # read the row from the object Excel just created

    def _next_row(self) -> int:
        """Return the last table row if blank; otherwise, append a row."""
        table = self.worksheet.tables[self.TABLE_NAME]
        data_range = table.data_body_range

        if data_range is None:
            return self._add_table_row()

        first_col = self.COLUMNS[0][0]
        last_col = self.COLUMNS[-1][0]
        last_row = data_range.last_cell.row

        values = self.worksheet.range(
            f"{first_col}{last_row}:{last_col}{last_row}"
        ).options(ndim=1).value

        if all(value is None for value in values):
            return last_row

        return self._add_table_row()

    def _write_cell(self, col: str, row: int, field: tuple) -> None:
        """Write a value and apply formatting based on its flag."""
        value, flag = field
        cell = self.worksheet.range(f"{col}{row}")

        cell.value = value

        if flag > 0:
            style = self.FLAG_STYLES.get(flag, self.FLAG_STYLES[1])
            cell.color = style["fill"]
            cell.font.color = style["font"]
            cell.font.bold = True
        else:
            cell.color = None                                       # clear fill
            cell.api.Font.ColorIndex = XL_COLOR_INDEX_AUTOMATIC     # remove font color override
            cell.font.bold = False

    # ---- main write operation --------------------------------------------
    def write_record(self, maintenance_record: MaintenanceReport) -> None:
        try:
            row = self._next_row()

            for col, attr in self.COLUMNS:
                self._write_cell(col, row, getattr(maintenance_record, attr))
        except Exception as exc:
            logger.error("Maintenance report write failed.")
            raise ExcelWriteError(
                "A maintenance report could not be written to the workbook."
            ) from exc

        # # save workbook after each write operation
        # self.workbook.save()

    # ---- cleanup ---------------------------------------------------------
    def close_workbook(self, save: bool = True) -> None:
        """Optionally save, then close this manager's workbook and Excel instance."""
        if self._closed:
            return

        try:
            if save:
                self.workbook.save()
                logger.info("Maintenance workbook saved.")
        finally:
            # Closing without saving discards this instance's unsaved workbook edits.
            try:
                if self.workbook_is_mine:
                    self.workbook.close()
            finally:
                if self.workbook_is_mine:
                    self.excel_app.quit()
                self._closed = True
                logger.info("Maintenance workbook session closed.")
